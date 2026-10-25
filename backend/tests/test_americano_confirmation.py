"""Atomic close/replay and private bracket reads, plus an opt-in PostgreSQL race."""

import threading
import time
from types import SimpleNamespace
from uuid import UUID

import pytest
import httpx
from sqlalchemy import event as sql_event, text as sql_text
from sqlmodel import Session, select

from app.americanos import service
from app.americanos.models import (
    AmericanoEvent, AmericanoEventState, AmericanoGroupMatch, AmericanoKnockoutMatch,
    AmericanoQualifierSnapshot, AmericanoRound, AmericanoTieResolution,
)
from app.americanos.schemas import ConfirmationResponse, PlayoffsResponse
from app.database.session import engine as application_engine

from .americano_fixtures import BASE, americano_api, create_event  # noqa: F401
from .test_americano_qualification_api import _finish, _generated, _preview, _put, _selections


KEY = "6c764a9e-ad96-4c73-a468-f89261f3fa08"
OTHER_KEY = "c23f6ee6-be9d-4b09-b5e8-7e86d6ae2fe5"


def _ready(api, sizes=(3,), stage="final", tiers=None):
    event = _finish(api, _generated(api, sizes, stage), tiers)
    preview = _preview(api, event)
    if preview["missing_slots"]:
        response = _put(api, preview, _selections(preview, reverse=True))
        assert response.status_code == 200, response.text
        preview = response.json()
    return event, preview


def _confirm(api, preview, **changes):
    return api.client.post(f"{BASE}/{preview['event_id']}/confirm-qualifiers", json={
        "expected_revision": preview["revision"],
        "source_groups_revision": preview["source_groups_revision"], "confirmation_key": KEY,
        **changes,
    })


def _playoffs(api, event_id):
    response = api.client.get(f"{BASE}/{event_id}/playoffs")
    assert response.status_code == 200, response.text
    PlayoffsResponse.model_validate(response.json())
    return response.json()


def _counts(api, event_id):
    with Session(api.engine) as session:
        return tuple(len(session.exec(select(model).where(model.event_id == event_id)).all())
                     for model in (AmericanoQualifierSnapshot, AmericanoKnockoutMatch))


@pytest.mark.parametrize("first_writer", ["score", "confirm"])
def test_real_postgres_score_and_close_race_serializes_stale_operation(
    admin, guest, monkeypatch, first_writer,
):
    """Prove the event row lock orders two independent HTTP/DB sessions.

    The ordinary Americano fixture deliberately uses SQLite memory. This test
    is skipped there and only runs when pytest was explicitly pointed at the
    disposable PostgreSQL validation database.
    """
    if application_engine.dialect.name != "postgresql":
        pytest.skip("requires a disposable PostgreSQL database and real row locks")

    token = admin.cookies.get("access_token")
    assert token
    guest.cookies.set("access_token", token)
    api = SimpleNamespace(client=admin, engine=application_engine)
    event = _generated(api, sizes=(2,))
    event = _finish(api, event, tiers=[1, 0])
    preview = _preview(api, event)
    assert preview["can_confirm"] is True
    group_round = admin.get(f"{BASE}/{event['id']}/rounds/1").json()
    assert len(group_round["matches"]) == 1
    group_match = group_round["matches"][0]
    original_revision = preview["revision"]
    original_groups_revision = preview["source_groups_revision"]

    score_request = {
        "expected_revision": original_revision,
        "results": [{"match_id": group_match["id"], "games_a": 0, "games_b": 1}],
    }
    confirm_request = {
        "expected_revision": original_revision,
        "source_groups_revision": original_groups_revision,
        "confirmation_key": "a8337f0e-bff8-4b13-bdb7-50307ed7ef0b",
    }
    original_event_lookup = service._event
    original_save_round = service.save_round
    original_confirm_qualifiers = service.confirm_qualifiers
    first_operation_context = threading.local()
    first_lock_acquired = threading.Event()
    release_first_writer = threading.Event()
    second_request_started = threading.Event()
    responses = {}
    failures = []

    def hold_first_event_lock(session, event_id, *, write=False):
        row = original_event_lookup(session, event_id, write=write)
        if write and event_id == event["id"] and getattr(first_operation_context, "active", False):
            first_lock_acquired.set()
            if not release_first_writer.wait(timeout=10):
                raise AssertionError("test did not release the first PostgreSQL row lock")
        return row

    def mark_first_operation(original):
        def invoke(*args, **kwargs):
            first_operation_context.active = True
            try:
                return original(*args, **kwargs)
            finally:
                first_operation_context.active = False

        return invoke

    monkeypatch.setattr(service, "_event", hold_first_event_lock)
    monkeypatch.setattr(
        service,
        "save_round",
        mark_first_operation(original_save_round) if first_writer == "score" else original_save_round,
    )
    monkeypatch.setattr(
        service,
        "confirm_qualifiers",
        mark_first_operation(original_confirm_qualifiers) if first_writer == "confirm" else original_confirm_qualifiers,
    )

    def send(kind, client, payload):
        try:
            if kind == "score":
                response = client.put(
                    f"{BASE}/{event['id']}/rounds/1/results", json=payload,
                )
            else:
                response = client.post(
                    f"{BASE}/{event['id']}/confirm-qualifiers", json=payload,
                )
            responses[kind] = response
        except Exception as exc:  # propagate worker failures to pytest
            failures.append(exc)

    operations = {
        "score": (admin, score_request),
        "confirm": (guest, confirm_request),
    }
    second_writer = "confirm" if first_writer == "score" else "score"
    first_client, first_payload = operations[first_writer]
    second_client, second_payload = operations[second_writer]

    def send_second():
        second_request_started.set()
        send(second_writer, second_client, second_payload)

    first = threading.Thread(
        name="first-writer", target=send, args=(first_writer, first_client, first_payload),
    )
    second = threading.Thread(name="second-writer", target=send_second)
    try:
        first.start()
        assert first_lock_acquired.wait(timeout=5), (
            "first request never acquired the event row lock; "
            f"failures={failures!r}, responses={responses!r}"
        )
        second.start()
        assert second_request_started.wait(timeout=5)

        # Observe a *real blocked SQL statement* in pg_stat_activity before
        # releasing the winner; simultaneous scheduling alone is insufficient.
        wait_started = time.monotonic()
        observed_wait = False
        while time.monotonic() - wait_started < 5:
            with application_engine.connect() as connection:
                blocked = connection.execute(sql_text("""
                    SELECT count(*) FROM pg_stat_activity
                    WHERE datname = current_database()
                      AND pid <> pg_backend_pid()
                      AND wait_event_type = 'Lock'
                      AND query ILIKE '%americano_events%'
                """)).scalar_one()
            if blocked:
                observed_wait = True
                break
            time.sleep(0.025)
        assert observed_wait, "second transaction was never observed waiting on the event lock"
    finally:
        release_first_writer.set()
        if first.ident is not None:
            first.join(timeout=15)
        if second.ident is not None:
            second.join(timeout=15)

    assert not first.is_alive() and not second.is_alive(), "race request thread did not finish"
    assert failures == [], failures
    assert responses["score"].status_code in {200, 409}, responses["score"].text
    assert responses["confirm"].status_code in {200, 409}, responses["confirm"].text
    assert sorted((responses["score"].status_code, responses["confirm"].status_code)) == [200, 409]

    canonical_event = admin.get(f"{BASE}/{event['id']}").json()
    canonical_round = admin.get(f"{BASE}/{event['id']}/rounds/1").json()
    if first_writer == "score":
        assert responses["score"].status_code == 200
        assert responses["confirm"].status_code == 409
        assert canonical_event["state"] == "review"
        assert canonical_event["revision"] == original_revision + 1
        assert canonical_event["groups_revision"] == original_groups_revision + 1
        assert (canonical_round["matches"][0]["games_a"], canonical_round["matches"][0]["games_b"]) == (0, 1)
        assert _counts(api, event["id"]) == (0, 0), "stale close must not create seeds or bracket nodes"
    else:
        assert responses["confirm"].status_code == 200
        assert responses["score"].status_code == 409
        assert canonical_event["state"] == "playoffs"
        assert canonical_event["revision"] == original_revision + 1
        assert canonical_event["groups_revision"] == original_groups_revision
        assert (canonical_round["matches"][0]["games_a"], canonical_round["matches"][0]["games_b"]) == (1, 0)
        assert _counts(api, event["id"]) == (2, 1)
        bracket = _playoffs(api, event["id"])
        assert all(seed["source_groups_revision"] == original_groups_revision for seed in bracket["snapshots"])


@pytest.mark.parametrize("stage,sizes,node_count", [
    ("final", (2,), 1), ("final", (1, 1), 1),
    ("semifinal", (4,), 3), ("semifinal", (2, 2), 3),
    ("quarterfinal", (8,), 7), ("quarterfinal", (4, 4), 7),
])
def test_confirm_creates_complete_approved_bracket_and_snapshot_once(americano_api, stage, sizes, node_count):
    api = americano_api
    event, preview = _ready(api, sizes, stage)
    assert _counts(api, event["id"]) == (0, 0)
    response = _confirm(api, preview)
    assert response.status_code == 200, response.text
    result = response.json()
    ConfirmationResponse.model_validate(result)
    assert result["confirmation_key"] == KEY
    assert result["confirmed_source_revision"] == preview["source_groups_revision"]
    assert result["event"]["confirmed_at"] == result["confirmed_at"]
    assert result["event"]["state"] == result["playoffs"]["state"] == "playoffs"
    assert result["event"]["revision"] == result["playoffs"]["revision"] == preview["revision"] + 1
    assert result["playoffs"]["groups_revision"] == preview["source_groups_revision"]
    assert result["playoffs"]["champion"] is None
    nodes = result["playoffs"]["nodes"]
    assert len(nodes) == node_count and len({node["id"] for node in nodes}) == node_count
    assert _counts(api, event["id"]) == (sum(quota["required"] for quota in preview["quotas"]), node_count)
    seed_map = {(seed["zone_id"], seed["position"]): seed["registration_id"] for seed in preview["resolved_seeds"]}
    assert [node["stage"] for node in nodes] == sorted([node["stage"] for node in nodes], key=["quarterfinal", "semifinal", "final"].index)
    by_ref = {(node["stage"], node["slot"]): node for node in nodes}
    for node, planned in zip(nodes, preview["bracket"], strict=True):
        assert (node["stage"], node["slot"]) == (planned["stage"], planned["slot"])
        for side in ("a", "b"):
            participant = node[f"registration_{side}"]
            assert (participant["id"] if participant else None) == planned[f"registration_{side}_id"]
        assert node["games_a"] is None and node["games_b"] is None and node["set_complete"] is False
        assert node["winner_registration_id"] is None
        if planned["next"]:
            destination = planned["next"]
            assert node["next_match_id"] == by_ref[destination["stage"], destination["slot"]]["id"]
            assert node["next_side"] == destination["side"]
        else:
            assert node["next_match_id"] is None and node["next_side"] is None
        assert node["can_edit"] is (node["stage"] == stage)
        assert node["edit_block_reason"] == (None if node["can_edit"] else "participants_pending")
    snapshots = result["playoffs"]["snapshots"]
    assert {(row["zone_id"], row["position"]): row["registration_id"] for row in snapshots} == seed_map
    standing_rows = {row["registration"]["id"]: row for zone in preview["standings"] for block in zone["blocks"] for row in block["rows"]}
    for snapshot in snapshots:
        row = standing_rows[snapshot["registration_id"]]
        assert snapshot["player1_name"] == row["registration"]["player1_name"]
        assert snapshot["player2_name"] == row["registration"]["player2_name"]
        assert snapshot["points_half_units"] == row["points_half_units"]
        assert snapshot["games_diff"] == row["games_diff"]
        assert snapshot["source_groups_revision"] == preview["source_groups_revision"]
    assert _playoffs(api, event["id"]) == result["playoffs"]
    frozen = _preview(api, event)
    assert frozen["frozen"] is True and frozen["can_confirm"] is False
    assert frozen["resolved_seeds"] == preview["resolved_seeds"]
    assert api.client.get(f"{BASE}/{event['id']}/standings").json()["frozen"] is True


@pytest.mark.parametrize("representation", [KEY, KEY.upper(), KEY.replace("-", ""), "{" + KEY.upper() + "}"])
def test_same_normalized_uuid_replays_with_obsolete_revisions_without_duplicate_rows(americano_api, representation):
    api = americano_api
    event, preview = _ready(api)
    result = _confirm(api, preview, confirmation_key=representation)
    assert result.status_code == 200, result.text
    canonical = result.json()
    before = _counts(api, event["id"])
    replay = _confirm(api, preview, expected_revision=1, source_groups_revision=0)
    assert replay.status_code == 200 and replay.json() == canonical
    assert replay.json()["confirmation_key"] == str(UUID(KEY))
    assert _counts(api, event["id"]) == before


def test_lost_confirmation_response_retries_same_key_without_duplicate_rows(americano_api, monkeypatch):
    api = americano_api
    event, preview = _ready(api)
    original_post = api.client.post
    calls = 0

    def commit_then_lose_first_response(url, **kwargs):
        nonlocal calls
        calls += 1
        response = original_post(url, **kwargs)
        if calls == 1:
            assert response.status_code == 200, response.text
            raise httpx.ReadTimeout("confirmation committed but response was lost")
        return response

    monkeypatch.setattr(api.client, "post", commit_then_lose_first_response)
    with pytest.raises(httpx.ReadTimeout, match="response was lost"):
        _confirm(api, preview)

    committed = api.client.get(f"{BASE}/{event['id']}/playoffs")
    assert committed.status_code == 200, committed.text
    canonical_before_retry = committed.json()
    counts_before_retry = _counts(api, event["id"])
    revision_before_retry = api.client.get(f"{BASE}/{event['id']}").json()["revision"]

    retry = _confirm(api, preview)
    assert retry.status_code == 200, retry.text
    assert retry.json()["playoffs"] == canonical_before_retry
    assert retry.json()["confirmation_key"] == KEY
    assert _counts(api, event["id"]) == counts_before_retry == (2, 1)
    assert api.client.get(f"{BASE}/{event['id']}").json()["revision"] == revision_before_retry
    assert calls == 2


@pytest.mark.parametrize("state", ["playoffs", "completed"])
def test_replay_returns_current_bracket_revision_and_champion_after_later_results(americano_api, state):
    api = americano_api
    event, preview = _ready(api, (4,), "semifinal")
    result = _confirm(api, preview).json()
    with Session(api.engine) as session:
        stored = session.get(AmericanoEvent, event["id"])
        nodes = session.exec(select(AmericanoKnockoutMatch).where(AmericanoKnockoutMatch.event_id == event["id"])).all()
        final = next(node for node in nodes if node.stage.value == "final")
        for semifinal in (node for node in nodes if node.stage.value == "semifinal"):
            semifinal.games_a, semifinal.games_b = 6, 0
            semifinal.set_complete = True
            semifinal.winner_registration_id = semifinal.registration_a_id
            setattr(final, f"registration_{semifinal.next_side.value}_id", semifinal.winner_registration_id)
            session.add(semifinal)
        if state == "completed":
            final.games_a, final.games_b = 0, 6
            final.set_complete = True
            final.winner_registration_id = final.registration_b_id
            stored.champion_registration_id = final.winner_registration_id
        stored.state = AmericanoEventState(state)
        stored.revision += 3
        session.add_all([stored, final])
        session.commit()
    current = _playoffs(api, event["id"])
    replay = _confirm(api, preview)
    assert replay.status_code == 200, replay.text
    assert replay.json()["playoffs"] == current
    assert replay.json()["event"]["revision"] == result["event"]["revision"] + 3
    assert replay.json()["confirmed_at"] == result["confirmed_at"]
    assert replay.json()["confirmed_source_revision"] == result["confirmed_source_revision"]
    final = next(node for node in current["nodes"] if node["stage"] == "final")
    assert final["can_edit"] is True and final["edit_block_reason"] is None
    for semifinal in (node for node in current["nodes"] if node["stage"] == "semifinal"):
        assert semifinal["can_edit"] is (state != "completed")
        assert semifinal["edit_block_reason"] == ("descendant_played" if state == "completed" else None)
    assert (current["champion"]["id"] if current["champion"] else None) == final["winner_registration_id"]


def test_another_key_conflicts_before_stale_revision_and_keeps_canonical_close(americano_api):
    api = americano_api
    event, preview = _ready(api)
    result = _confirm(api, preview).json()
    response = _confirm(api, preview, confirmation_key=OTHER_KEY, expected_revision=1, source_groups_revision=0)
    assert response.status_code == 409 and response.json()["code"] == "already_confirmed"
    assert response.json()["current_revision"] == result["event"]["revision"]
    assert response.json()["detail"] == response.json()["message"]
    assert _playoffs(api, event["id"]) == result["playoffs"] and _counts(api, event["id"]) == (2, 1)


@pytest.mark.parametrize("field,code", [("expected_revision", "revision_conflict"), ("source_groups_revision", "groups_revision_conflict")])
def test_stale_close_never_creates_snapshot_or_nodes(americano_api, field, code):
    api = americano_api
    event, preview = _ready(api)
    response = _confirm(api, preview, **{field: preview["revision" if field == "expected_revision" else field] - 1})
    assert response.status_code == 409 and response.json()["code"] == code
    assert response.json()["fields"][0]["path"] == [field]
    assert _counts(api, event["id"]) == (0, 0) and _preview(api, event) == preview


@pytest.mark.parametrize("state", ["draft", "groups"])
def test_confirm_and_playoffs_read_before_review_are_rejected(americano_api, state):
    api = americano_api
    event = create_event(api) if state == "draft" else _generated(api)
    preview = _preview(api, event)
    for response in [_confirm(api, preview), api.client.get(f"{BASE}/{event['id']}/playoffs")]:
        assert response.status_code == 409 and response.json()["code"] == "state_conflict"
        assert response.json()["current_revision"] == event["revision"]
    assert _counts(api, event["id"]) == (0, 0)


def test_unresolved_ties_prevent_close_without_guessing_from_visual_order(americano_api):
    api = americano_api
    event = _finish(api, _generated(api))
    preview = _preview(api, event)
    response = _confirm(api, preview)
    assert response.status_code == 422 and response.json()["code"] == "invalid_tie_resolution"
    assert _counts(api, event["id"]) == (0, 0) and _preview(api, event) == preview


@pytest.mark.parametrize("damage", ["unsaved_round", "missing_match", "missing_round", "null_score", "insufficient_quota"])
def test_close_rechecks_persisted_results_fixture_and_configuration(americano_api, damage):
    api = americano_api
    event, preview = _ready(api)
    with Session(api.engine) as session:
        round_ = session.exec(select(AmericanoRound).where(AmericanoRound.event_id == event["id"])).first()
        match = session.exec(select(AmericanoGroupMatch).where(AmericanoGroupMatch.round_id == round_.id)).first()
        if damage == "unsaved_round":
            round_.saved_at = None
            session.add(round_)
        elif damage == "missing_match":
            session.delete(match)
        elif damage == "missing_round":
            session.delete(match)
            session.flush()
            session.delete(round_)
        elif damage == "null_score":
            match.games_a = match.games_b = None
            session.add(match)
        else:
            stored = session.get(AmericanoEvent, event["id"])
            stored.start_stage = "quarterfinal"
            session.add(stored)
        session.commit()
    response = _confirm(api, preview)
    assert response.status_code == (422 if damage == "insufficient_quota" else 409), response.text
    assert response.json()["code"] == ("invalid_configuration" if damage == "insufficient_quota" else "state_conflict")
    assert _counts(api, event["id"]) == (0, 0)
    assert api.client.get(f"{BASE}/{event['id']}").json()["state"] == "review"


@pytest.mark.parametrize("failure", ["snapshot_insert", "node_insert", "node_later_insert", "constructor", "output", "commit"])
def test_every_failure_rolls_back_all_rows_metadata_and_revision(americano_api, monkeypatch, failure):
    api = americano_api
    event, preview = _ready(api, (4,), "semifinal")
    original_event = api.client.get(f"{BASE}/{event['id']}").json()
    node_inserts = 0

    def fail_sql(_connection, _cursor, statement, _parameters, _context, _many):
        nonlocal node_inserts
        upper = statement.lstrip().upper()
        if upper.startswith("INSERT INTO AMERICANO_KNOCKOUT_MATCHES"):
            node_inserts += 1
            if failure == "node_insert" or failure == "node_later_insert" and node_inserts == 2:
                raise RuntimeError("injected close failure")
        if failure == "snapshot_insert" and upper.startswith("INSERT INTO AMERICANO_QUALIFIER_SNAPSHOTS"):
            raise RuntimeError("injected close failure")

    def fail(*_args, **_kwargs):
        raise RuntimeError("injected close failure")

    original_commit = Session.commit

    def fail_commit(session):
        if session.bind is api.engine:
            fail()
        return original_commit(session)

    sql_event.listen(api.engine, "before_cursor_execute", fail_sql)
    try:
        with monkeypatch.context() as patch:
            if failure == "constructor":
                patch.setattr(service, "build_bracket", fail)
            elif failure == "output":
                patch.setattr(service, "_confirmation_detail", fail)
            elif failure == "commit":
                patch.setattr(Session, "commit", fail_commit)
            with pytest.raises(RuntimeError, match="injected close failure"):
                _confirm(api, preview)
    finally:
        sql_event.remove(api.engine, "before_cursor_execute", fail_sql)
    assert _counts(api, event["id"]) == (0, 0)
    assert api.client.get(f"{BASE}/{event['id']}").json() == original_event
    assert _preview(api, event) == preview
    assert _confirm(api, preview).status_code == 200


def test_confirmed_groups_and_composition_are_frozen_by_every_existing_writer(americano_api):
    api = americano_api
    event, preview = _ready(api)
    result = _confirm(api, preview).json()
    revision = result["event"]["revision"]
    registration_id = event["registrations"][0]["id"]
    url = f"{BASE}/{event['id']}"
    operations = [
        ("patch", url, {"expected_revision": revision, "name": "Changed"}),
        ("post", url + "/registrations", {"expected_revision": revision, "player1_name": "X", "player2_name": "Y"}),
        ("patch", url + f"/registrations/{registration_id}", {"expected_revision": revision, "player1_name": "X"}),
        ("put", url + "/zones", {"expected_revision": revision, "zone_count": 1, "zone_a_registration_ids": []}),
        ("post", url + "/zones/randomize", {"expected_revision": revision}),
        ("post", url + "/fixture", {"expected_revision": revision}),
        ("put", url + "/rounds/1/results", {"expected_revision": revision, "results": []}),
        ("put", url + "/tie-resolutions", {"expected_revision": revision, "source_groups_revision": preview["source_groups_revision"], "resolutions": []}),
    ]
    for method, path, payload in operations:
        response = getattr(api.client, method)(path, json=payload)
        assert response.status_code == 409 and response.json()["code"] == "state_conflict", response.text
    response = api.client.delete(url + f"/registrations/{registration_id}?expected_revision={revision}")
    assert response.status_code == 409 and response.json()["code"] == "state_conflict"
    assert _playoffs(api, event["id"]) == result["playoffs"]


@pytest.mark.parametrize("mode", ["anonymous", "expired", "inactive"])
@pytest.mark.parametrize("operation", ["confirm", "read"])
def test_new_endpoints_keep_real_admin_guard(americano_api, mode, operation):
    api = americano_api
    api.authenticate(mode)
    response = _confirm(api, {"event_id": 9999, "revision": 1, "source_groups_revision": 0}) if operation == "confirm" else api.client.get(f"{BASE}/9999/playoffs")
    assert response.status_code == 401 and response.json() == {"detail": "Not authenticated"}


@pytest.mark.parametrize("event_id", [9999, 2_147_483_648, 9_007_199_254_740_991])
@pytest.mark.parametrize("operation", ["confirm", "read"])
def test_missing_and_huge_event_ids_are_flat_404(americano_api, event_id, operation):
    api = americano_api
    response = _confirm(api, {"event_id": event_id, "revision": 1, "source_groups_revision": 0}) if operation == "confirm" else api.client.get(f"{BASE}/{event_id}/playoffs")
    assert response.status_code == 404 and response.json()["code"] == "not_found"
    assert response.json()["detail"] == response.json()["message"]


@pytest.mark.parametrize("changes", [
    {"confirmation_key": "invalid"}, {"confirmation_key": None}, {"confirmation_key": 1},
    {"expected_revision": True}, {"source_groups_revision": 1.0}, {"unexpected": []},
    {"resolved_seeds": []}, {"confirmation_key": ""},
])
def test_confirmation_transport_is_closed_and_strict(americano_api, changes):
    api = americano_api
    event, preview = _ready(api)
    response = _confirm(api, preview, **changes)
    assert response.status_code == 422 and response.json()["code"] == "validation_error"
    assert _counts(api, event["id"]) == (0, 0) and _preview(api, event) == preview


def test_confirming_one_event_does_not_write_another_or_league_tables(americano_api):
    api = americano_api
    first, first_preview = _ready(api)
    second, second_preview = _ready(api)
    writes = []

    def executed(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(statement)

    sql_event.listen(api.engine, "before_cursor_execute", executed)
    try:
        response = _confirm(api, first_preview)
        assert response.status_code == 200, response.text
    finally:
        sql_event.remove(api.engine, "before_cursor_execute", executed)
    assert writes and all("americano_" in statement for statement in writes)
    assert _preview(api, second) == second_preview and _counts(api, second["id"]) == (0, 0)
    assert _counts(api, first["id"]) == (2, 1)


def test_snapshot_metrics_are_recomputed_from_nonzero_canonical_standings(americano_api):
    api = americano_api
    event, preview = _ready(api, (4,), "semifinal", tiers=[3, 2, 1, 0])
    assert preview["missing_slots"] == []
    response = _confirm(api, preview)
    assert response.status_code == 200, response.text
    snapshots = response.json()["playoffs"]["snapshots"]
    assert [row["points_half_units"] for row in snapshots] == [6, 4, 2, 0]
    assert [row["games_diff"] for row in snapshots] == [3, 1, -1, -3]
    assert _playoffs(api, event["id"])["snapshots"] == snapshots


def test_sequential_score_then_close_rejects_old_preview_without_claiming_a_lock_race(americano_api):
    api = americano_api
    event, preview = _ready(api)
    round_ = api.client.get(f"{BASE}/{event['id']}/rounds/1").json()
    response = api.client.put(f"{BASE}/{event['id']}/rounds/1/results", json={
        "expected_revision": round_["revision"],
        "results": [{"match_id": match["id"], "games_a": 1, "games_b": 0} for match in round_["matches"]],
    })
    assert response.status_code == 200, response.text
    rejected = _confirm(api, preview)
    assert rejected.status_code == 409 and rejected.json()["code"] == "revision_conflict"
    current = _preview(api, event)
    rejected = _confirm(api, current, source_groups_revision=preview["source_groups_revision"])
    assert rejected.status_code == 409 and rejected.json()["code"] == "groups_revision_conflict"
    assert _counts(api, event["id"]) == (0, 0)
    if current["missing_slots"]:
        current = _put(api, current).json()
    accepted = _confirm(api, current)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["confirmed_source_revision"] == current["source_groups_revision"]


def test_new_manual_resolution_invalidates_old_global_revision_even_when_scores_are_unchanged(americano_api):
    api = americano_api
    event, preview = _ready(api)
    current = _put(api, preview).json()
    assert current["source_groups_revision"] == preview["source_groups_revision"]
    rejected = _confirm(api, preview)
    assert rejected.status_code == 409 and rejected.json()["code"] == "revision_conflict"
    response = _confirm(api, current)
    assert response.status_code == 200 and response.json()["confirmed_source_revision"] == preview["source_groups_revision"]
    assert _counts(api, event["id"]) == (2, 1)


def test_close_uses_event_first_lock_statement_and_one_connection_commit_sqlite_probe(americano_api):
    """Statement/transaction ordering only; SQLite cannot prove row contention."""
    api = americano_api
    _event, preview = _ready(api)
    statements, connections, commits = [], set(), []

    def executed(connection, clause, _multiparams, _params, _options):
        connections.add(id(connection))
        if "americano_" in str(clause):
            statements.append(clause)

    def committed(connection):
        commits.append(id(connection))

    sql_event.listen(api.engine, "before_execute", executed)
    sql_event.listen(api.engine, "commit", committed)
    try:
        response = _confirm(api, preview)
        assert response.status_code == 200, response.text
    finally:
        sql_event.remove(api.engine, "before_execute", executed)
        sql_event.remove(api.engine, "commit", committed)
    assert "FROM americano_events" in str(statements[0])
    assert statements[0]._for_update_arg is not None and statements[0]._for_update_arg.read is False
    assert len(connections) == len(commits) == 1 and commits[0] in connections


def test_canonical_get_and_same_key_replay_never_emit_dml_or_duplicate_rows(americano_api):
    api = americano_api
    event, preview = _ready(api)
    committed = _confirm(api, preview).json()
    writes = []

    def executed(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(statement)

    sql_event.listen(api.engine, "before_cursor_execute", executed)
    try:
        assert _playoffs(api, event["id"]) == committed["playoffs"]
        assert _confirm(api, preview).json() == committed
    finally:
        sql_event.remove(api.engine, "before_cursor_execute", executed)
    assert writes == [] and _counts(api, event["id"]) == (2, 1)
