"""Private round reads and atomic results against an isolated in-memory DB."""

import datetime

import pytest
from sqlalchemy import event as sql_event
from sqlmodel import Session, select

from app.americanos.models import (
    AmericanoEvent, AmericanoEventState, AmericanoGroupMatch, AmericanoRound, AmericanoZone,
    AmericanoTieResolution, AmericanoZoneLabel,
)
from app.americanos.schemas import RoundResponse, SaveRoundResponse, StandingsResponse

from .americano_fixtures import BASE, add_registration, americano_api, create_event  # noqa: F401


def _generated(api, sizes=(2,)):
    detail = create_event(api, zone_count=len(sizes))
    for index in range(sum(sizes)):
        detail = add_registration(api, detail, first=f"Jugador {index}", second=f"Pareja {index}")
    response = api.client.put(f"{BASE}/{detail['id']}/zones", json={
        "expected_revision": detail["revision"], "zone_count": len(sizes),
        "zone_a_registration_ids": [r["id"] for r in detail["registrations"][:sizes[0]]],
    })
    assert response.status_code == 200, response.text
    response = api.client.post(f"{BASE}/{detail['id']}/fixture", json={
        "expected_revision": response.json()["revision"],
    })
    assert response.status_code == 200, response.text
    return response.json()


def _round(api, event, number=1):
    return api.client.get(f"{BASE}/{event['id']}/rounds/{number}")


def _standings(api, event):
    return api.client.get(f"{BASE}/{event['id']}/standings")


def test_round_read_returns_the_persisted_first_round_without_mutating_event(americano_api):
    api = americano_api
    generated = _generated(api)
    response = _round(api, generated["event"])
    assert response.status_code == 200, response.text
    RoundResponse.model_validate(response.json())
    assert response.json() == generated["first_round"]
    assert api.client.get(f"{BASE}/{generated['event']['id']}").json() == generated["event"]


def _seed_round(api, event, number, scores=None, *, saved=True, state=None):
    """Seed persisted results for read tests; no 4.2 write endpoint is exercised."""
    with Session(api.engine) as session:
        round_ = session.exec(select(AmericanoRound).where(
            AmericanoRound.event_id == event["id"], AmericanoRound.number == number,
        )).one()
        matches = session.exec(select(AmericanoGroupMatch).where(
            AmericanoGroupMatch.event_id == event["id"], AmericanoGroupMatch.round_id == round_.id,
        ).order_by(AmericanoGroupMatch.display_order)).all()
        for match, score in zip(matches, scores or [(0, 0)] * len(matches), strict=True):
            match.games_a, match.games_b = score
            session.add(match)
        round_.saved_at = datetime.datetime.now(datetime.UTC) if saved else None
        session.add(round_)
        stored = session.get(AmericanoEvent, event["id"])
        stored.revision += 1
        stored.groups_revision += int(saved)
        if state:
            stored.state = AmericanoEventState(state)
        session.add(stored)
        session.commit()
    return api.client.get(f"{BASE}/{event['id']}").json()


@pytest.mark.parametrize("number", [2, 3])
def test_round_read_rejects_locked_round_without_leaking_its_scores(americano_api, number):
    api = americano_api
    event = _generated(api, (4,))["event"]
    event = _seed_round(api, event, number, [(9, 1), (8, 2)])
    response = _round(api, event, number)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "round_locked" and body["current_revision"] == event["revision"]
    assert body["detail"] == body["message"] and "matches" not in body and "games_a" not in response.text
    assert _round(api, event, 1).status_code == 200
    assert api.client.get(f"{BASE}/{event['id']}").json() == event


@pytest.mark.parametrize("score", [(0, 0), (5, 3)])
def test_round_read_preserves_saved_scores_including_zero_and_unlocks_next(americano_api, score):
    api = americano_api
    event = _generated(api, (4,))["event"]
    event = _seed_round(api, event, 1, [score, (None, None)])
    response = _round(api, event)
    assert response.status_code == 200
    actual = response.json()
    assert actual["saved"] is True and actual["max_unlocked_round"] == 2
    assert (actual["matches"][0]["games_a"], actual["matches"][0]["games_b"]) == score
    assert actual["matches"][1]["games_a"] is None and actual["matches"][1]["games_b"] is None
    assert actual["revision"] == event["revision"] and actual["groups_revision"] == event["groups_revision"]
    assert actual["read_only"] is False and actual["locked"] is False
    assert _round(api, event, 2).status_code == 200
    assert _round(api, event, 3).status_code == 409


@pytest.mark.parametrize("state", ["review", "playoffs", "completed"])
def test_round_read_remains_available_after_groups_and_only_closed_states_are_read_only(americano_api, state):
    api = americano_api
    event = _generated(api)["event"]
    event = _seed_round(api, event, 1, state=state)
    response = _round(api, event)
    assert response.status_code == 200
    actual = response.json()
    assert actual["read_only"] is (state in {"playoffs", "completed"})
    assert actual["saved"] is True and actual["locked"] is False
    assert actual["state"] == state and actual["number"] == 1


def _zero_row(registration):
    return {"registration": registration, "played": 0, "won": 0, "drawn": 0, "lost": 0,
            "games_for": 0, "games_against": 0, "games_diff": 0, "points_half_units": 0}


def test_standings_read_includes_assigned_pairs_at_zero_before_any_round_is_saved(americano_api):
    api = americano_api
    event = _generated(api)["event"]
    response = _standings(api, event)
    assert response.status_code == 200, response.text
    StandingsResponse.model_validate(response.json())
    assert response.json() == {
        "event_id": event["id"], "state": "groups", "revision": event["revision"],
        "groups_revision": 0, "frozen": False,
        "zones": [{"zone": event["zones"][0], "blocks": [{
            "position_from": 1, "position_to": 2, "points_half_units": 0, "games_diff": 0,
            "rows": [_zero_row(r) for r in event["registrations"]],
        }]}],
    }
    assert api.client.get(f"{BASE}/{event['id']}").json() == event


@pytest.mark.parametrize("score,expected", [
    ((0, 0), [
        {"played": 1, "won": 0, "drawn": 1, "lost": 0, "games_for": 0,
         "games_against": 0, "games_diff": 0, "points_half_units": 1},
        {"played": 1, "won": 0, "drawn": 1, "lost": 0, "games_for": 0,
         "games_against": 0, "games_diff": 0, "points_half_units": 1},
    ]),
    ((5, 3), [
        {"played": 1, "won": 1, "drawn": 0, "lost": 0, "games_for": 5,
         "games_against": 3, "games_diff": 2, "points_half_units": 2},
        {"played": 1, "won": 0, "drawn": 0, "lost": 1, "games_for": 3,
         "games_against": 5, "games_diff": -2, "points_half_units": 0},
    ]),
])
def test_standings_read_uses_saved_scores_with_exact_half_units_and_zero(americano_api, score, expected):
    api = americano_api
    event = _generated(api)["event"]
    event = _seed_round(api, event, 1, [score])
    response = _standings(api, event)
    assert response.status_code == 200, response.text
    actual = response.json()
    StandingsResponse.model_validate(actual)
    blocks = actual["zones"][0]["blocks"]
    assert [row for block in blocks for row in block["rows"]] == [
        {"registration": registration, **metrics}
        for registration, metrics in zip(event["registrations"], expected, strict=True)
    ]
    assert [(b["position_from"], b["position_to"]) for b in blocks] == (
        [(1, 2)] if score == (0, 0) else [(1, 1), (2, 2)]
    )
    assert (actual["revision"], actual["groups_revision"]) == (event["revision"], event["groups_revision"])


def test_standings_read_omits_pending_and_unsaved_scores_but_includes_saved_zero(americano_api):
    api = americano_api
    event = _generated(api, (4,))["event"]
    first = _round(api, event).json()
    event = _seed_round(api, event, 1, [(None, None), (0, 0)])
    event = _seed_round(api, event, 2, [(9, 0), (8, 1)], saved=False)
    response = _standings(api, event)
    assert response.status_code == 200
    blocks = response.json()["zones"][0]["blocks"]
    played_ids = {first["matches"][1][side]["id"] for side in ["registration_a", "registration_b"]}
    assert len(played_ids) == 2
    rows = [row for block in blocks for row in block["rows"]]
    assert len(rows) == 4
    for row in rows:
        played = row["registration"]["id"] in played_ids
        assert row == _zero_row(row["registration"]) | {
            "played": int(played), "drawn": int(played), "points_half_units": int(played),
        }
    assert [(block["position_from"], block["position_to"], block["points_half_units"])
            for block in blocks] == [(1, 2, 1), (3, 4, 0)]


@pytest.mark.parametrize("sizes,number,reasons", [
    ((7, 7), 1, ["bye", "bye"]), ((7, 7), 4, ["bye", "bye"]),
    ((16,), 1, ["capacity"] * 4), ((16,), 2, ["capacity"] * 12),
    ((8, 8), 2, ["capacity"] * 12),
    ((5, 4), 4, ["bye"] + ["zone_finished"] * 4),
    ((5, 4), 5, ["bye"] + ["zone_finished"] * 4),
    ((1, 3), 2, ["zone_finished", "bye"]),
    ((3, 1), 3, ["bye", "zone_finished"]),
])
def test_round_read_uses_requested_persisted_matches_and_actual_rest_reasons(americano_api, sizes, number, reasons):
    from app.americanos.fixture import ZoneInput, build_fixture

    api = americano_api
    event = _generated(api, sizes)["event"]
    for prior in range(1, number):
        event = _seed_round(api, event, prior)
    response = _round(api, event, number)
    assert response.status_code == 200, response.text
    actual = response.json()
    RoundResponse.model_validate(actual)
    planned = build_fixture([
        ZoneInput(z["id"], z["label"], tuple(r["id"] for r in event["registrations"] if r["zone_id"] == z["id"]))
        for z in event["zones"]
    ])[number - 1]
    assert actual["number"] == number and actual["total_rounds"] == event["total_rounds"]
    assert actual["max_unlocked_round"] == number and actual["saved"] is False
    assert [(m["zone_id"], m["registration_a"]["id"], m["registration_b"]["id"], m["display_order"])
            for m in actual["matches"]] == [
        (m.zone_id, m.registration_a_id, m.registration_b_id, m.display_order) for m in planned.matches
    ]
    assert 1 <= len(actual["matches"]) <= 6
    assert all(m["games_a"] is None and m["games_b"] is None for m in actual["matches"])
    assert [(r["registration"]["id"], r["reason"]) for r in actual["resting"]] == [
        (r.registration_id, r.reason) for r in planned.resting
    ]
    assert [r["reason"] for r in actual["resting"]] == reasons
    with Session(api.engine) as session:
        stored_round = session.exec(select(AmericanoRound).where(
            AmericanoRound.event_id == event["id"], AmericanoRound.number == number,
        )).one()
        stored_matches = session.exec(select(AmericanoGroupMatch).where(
            AmericanoGroupMatch.event_id == event["id"], AmericanoGroupMatch.round_id == stored_round.id,
        ).order_by(AmericanoGroupMatch.display_order)).all()
        assert [m["id"] for m in actual["matches"]] == [m.id for m in stored_matches]


@pytest.mark.parametrize("saved,unlocked", [
    ([False, True, True], 1), ([True, False, True], 2), ([True, True, True], 3),
])
def test_round_read_and_event_list_share_contiguous_saved_prefix_not_count(americano_api, saved, unlocked):
    api = americano_api
    event = _generated(api, (4,))["event"]
    for number, is_saved in enumerate(saved, 1):
        event = _seed_round(api, event, number, saved=is_saved)
    summary = api.client.get(BASE).json()[0]
    assert summary["saved_rounds"] == event["saved_rounds"] == sum(saved)
    assert summary["max_unlocked_round"] == event["max_unlocked_round"] == unlocked
    assert event["continuation"] == {"kind": "round", "round_number": unlocked}
    for number in range(1, 4):
        response = _round(api, event, number)
        if number <= unlocked:
            assert response.status_code == 200
            assert response.json()["saved"] is saved[number - 1]
            assert response.json()["max_unlocked_round"] == unlocked
        else:
            assert response.status_code == 409 and response.json()["code"] == "round_locked"


@pytest.mark.parametrize("sizes", [(2,), (1, 1)])
def test_round_read_missing_numbers_and_zero_round_review_are_404(americano_api, sizes):
    api = americano_api
    event = _generated(api, sizes)["event"]
    missing = 2 if sizes == (2,) else 1
    response = _round(api, event, missing)
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found" and body["detail"] == body["message"]
    if sizes == (1, 1):
        assert event["total_rounds"] == event["max_unlocked_round"] == 0
        assert event["continuation"] == {"kind": "qualification"}


@pytest.mark.parametrize("path_id", ["0", "-1", "1.0", "true", "9007199254740992"])
@pytest.mark.parametrize("part", ["event", "number"])
def test_round_read_path_ids_are_strict_positive_json_safe_integers(americano_api, path_id, part):
    api = americano_api
    event = _generated(api)["event"]
    path = f"{BASE}/{path_id if part == 'event' else event['id']}/rounds/{path_id if part == 'number' else 1}"
    response = api.client.get(path)
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert response.json()["fields"][0]["path"] == ["event_id" if part == "event" else "number"]


@pytest.mark.parametrize("kind", ["round", "standings"])
def test_read_endpoints_missing_event_are_flat_404(americano_api, kind):
    response = (_round if kind == "round" else _standings)(americano_api, {"id": 99999})
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found" and body["detail"] == body["message"]
    assert "current_revision" not in body


@pytest.mark.parametrize("zone_count", [1, 2])
def test_standings_read_empty_draft_includes_every_real_zone(americano_api, zone_count):
    api = americano_api
    event = create_event(api, zone_count=zone_count)
    response = _standings(api, event)
    assert response.status_code == 200
    assert response.json() == {
        "event_id": event["id"], "state": "draft", "revision": event["revision"],
        "groups_revision": 0, "frozen": False,
        "zones": [{"zone": zone, "blocks": []} for zone in event["zones"]],
    }


def test_standings_read_skips_unassigned_draft_pairs_and_preserves_empty_zone(americano_api):
    api = americano_api
    event = add_registration(api, add_registration(api, create_event(api, zone_count=2)))
    assert _standings(api, event).json()["zones"] == [{"zone": z, "blocks": []} for z in event["zones"]]
    response = api.client.put(f"{BASE}/{event['id']}/zones", json={
        "expected_revision": event["revision"], "zone_count": 2, "zone_a_registration_ids": [],
    })
    assert response.status_code == 200
    event = add_registration(api, response.json(), first="Sin zona")
    response = _standings(api, event)
    assert response.status_code == 200
    actual = response.json()
    assert actual["zones"][0] == {"zone": event["zones"][0], "blocks": []}
    assert actual["zones"][1]["blocks"] == [{
        "position_from": 1, "position_to": 2, "points_half_units": 0, "games_diff": 0,
        "rows": [_zero_row(r) for r in event["registrations"][:2]],
    }]
    assert event["registrations"][-1]["zone_id"] is None


@pytest.mark.parametrize("state", ["groups", "review", "playoffs", "completed"])
def test_standings_read_frozen_flag_depends_only_on_closed_groups_state(americano_api, state):
    api = americano_api
    event = _generated(api)["event"]
    event = _seed_round(api, event, 1, state=state)
    response = _standings(api, event)
    assert response.status_code == 200
    assert response.json()["state"] == state
    assert response.json()["frozen"] is (state in {"playoffs", "completed"})
    assert response.json()["groups_revision"] == event["groups_revision"]


def test_standings_read_recomputes_replaced_scores_without_accumulation(americano_api):
    api = americano_api
    event = _generated(api)["event"]
    event = _seed_round(api, event, 1, [(5, 3)])
    assert _standings(api, event).json()["zones"][0]["blocks"][0]["points_half_units"] == 2
    event = _seed_round(api, event, 1, [(0, 0)])
    actual = _standings(api, event).json()
    assert actual["groups_revision"] == event["groups_revision"]
    assert len(actual["zones"][0]["blocks"]) == 1
    assert actual["zones"][0]["blocks"][0]["rows"] == [
        _zero_row(r) | {"played": 1, "drawn": 1, "points_half_units": 1} for r in event["registrations"]
    ]
    assert _standings(api, event).json() == actual


def test_standings_read_two_zones_are_independent_and_sorted_by_label_not_id(americano_api):
    api = americano_api
    event = create_event(api, zone_count=2)
    with Session(api.engine) as session:
        for zone in session.exec(select(AmericanoZone)).all():
            session.delete(zone)
        session.flush()
        session.add(AmericanoZone(event_id=event["id"], label=AmericanoZoneLabel.B))
        session.flush()
        session.add(AmericanoZone(event_id=event["id"], label=AmericanoZoneLabel.A))
        session.commit()
    for _ in range(4):
        event = add_registration(api, api.client.get(f"{BASE}/{event['id']}").json())
    response = api.client.put(f"{BASE}/{event['id']}/zones", json={
        "expected_revision": event["revision"], "zone_count": 2,
        "zone_a_registration_ids": [r["id"] for r in event["registrations"][:2]],
    })
    assert response.status_code == 200
    event = response.json()
    assert event["zones"][0]["id"] > event["zones"][1]["id"]
    response = api.client.post(f"{BASE}/{event['id']}/fixture", json={"expected_revision": event["revision"]})
    assert response.status_code == 200
    event = _seed_round(api, response.json()["event"], 1, [(5, 3), (0, 0)])
    actual = _standings(api, event).json()
    assert [z["zone"] for z in actual["zones"]] == event["zones"]
    assert [len(z["blocks"]) for z in actual["zones"]] == [2, 1]
    assert actual["zones"][1]["blocks"][0]["points_half_units"] == 1
    for zone in actual["zones"]:
        assert all(row["registration"]["zone_id"] == zone["zone"]["id"] for b in zone["blocks"] for row in b["rows"])


@pytest.mark.parametrize("kind", ["round", "standings"])
def test_read_endpoints_refresh_cached_children_as_well_as_event_revision(americano_api, kind):
    from app.americanos import service

    api = americano_api
    generated = _generated(api)
    event, first = generated["event"], generated["first_round"]
    # Ordered transactions test stale ORM identity, not simultaneous PG contention.
    with Session(api.engine, expire_on_commit=False) as observer:
        cached_event = observer.get(AmericanoEvent, event["id"])
        cached_round = observer.exec(select(AmericanoRound).where(AmericanoRound.event_id == event["id"])).one()
        cached_match = observer.get(AmericanoGroupMatch, first["matches"][0]["id"])
        observer.commit()
        current = _seed_round(api, event, 1, [(0, 0)], state="playoffs")
        assert cached_event.revision == event["revision"] and cached_round.saved_at is None
        assert cached_match.games_a is None
        actual = (service.load_round(observer, event["id"], 1) if kind == "round"
                  else service.load_standings(observer, event["id"]))
        assert actual.revision == current["revision"] and actual.groups_revision == current["groups_revision"]
        if kind == "round":
            assert actual.saved is True and actual.read_only is True
            assert actual.matches[0].games_a == actual.matches[0].games_b == 0
        else:
            assert actual.frozen is True
            assert [r.played for b in actual.zones[0].blocks for r in b.rows] == [1, 1]


def test_standings_read_refreshes_draft_registration_names_in_cached_session(americano_api):
    from app.americanos import service
    from app.americanos.models import AmericanoRegistration

    api = americano_api
    event = add_registration(api, create_event(api))
    registration = event["registrations"][0]
    with Session(api.engine, expire_on_commit=False) as observer:
        cached = observer.get(AmericanoRegistration, registration["id"])
        observer.commit()
        response = api.client.patch(f"{BASE}/{event['id']}/registrations/{registration['id']}", json={
            "expected_revision": event["revision"], "player1_name": "Actualizado",
        })
        assert response.status_code == 200
        assert cached.player1_name == registration["player1_name"]
        actual = service.load_standings(observer, event["id"])
        assert actual.revision == response.json()["revision"]
        assert actual.zones[0].blocks[0].rows[0].registration.player1_name == "Actualizado"


@pytest.mark.parametrize("suffix,expected_status", [("rounds/1", 200), ("standings", 200),
                                                  ("rounds/2", 409), ("rounds/99999", 404)])
def test_read_endpoints_lock_event_for_share_then_only_select_and_release_without_commit(
    americano_api, suffix, expected_status,
):
    from sqlalchemy.dialects import postgresql

    api = americano_api
    event = _generated(api, (4,))["event"]
    statements, commits, rollbacks = [], [], []

    def executed(_connection, clause, _multiparams, _params, _options):
        statements.append(str(clause.compile(dialect=postgresql.dialect())))

    def committed(_connection):
        commits.append("commit")

    def rolled_back(_connection):
        rollbacks.append("rollback")

    sql_event.listen(api.engine, "before_execute", executed)
    sql_event.listen(api.engine, "commit", committed)
    sql_event.listen(api.engine, "rollback", rolled_back)
    try:
        response = api.client.get(f"{BASE}/{event['id']}/{suffix}")
    finally:
        sql_event.remove(api.engine, "before_execute", executed)
        sql_event.remove(api.engine, "commit", committed)
        sql_event.remove(api.engine, "rollback", rolled_back)
    assert response.status_code == expected_status
    assert "FROM admin_users" in statements[0]
    assert "FROM americano_events" in statements[1] and "FOR SHARE" in statements[1]
    assert all(sql.startswith("SELECT") and "FOR UPDATE" not in sql for sql in statements)
    assert commits == [] and rollbacks == ["rollback"]
    if expected_status == 409:
        assert all("FROM americano_group_matches" not in sql for sql in statements)
    assert api.client.get(f"{BASE}/{event['id']}").json() == event


@pytest.mark.parametrize("kind", ["round", "standings"])
def test_read_endpoints_leave_every_persisted_americano_row_unchanged(americano_api, kind):
    from sqlmodel import SQLModel

    api = americano_api
    event = _generated(api, (5, 4))["event"]
    event = _seed_round(api, event, 1)

    def snapshot():
        with api.engine.connect() as connection:
            return {table.name: connection.execute(table.select().order_by(*table.primary_key.columns)).all()
                    for table in SQLModel.metadata.sorted_tables if table.name.startswith("americano_")}

    before = snapshot()
    response = (_round if kind == "round" else _standings)(api, event)
    assert response.status_code == 200
    assert snapshot() == before


def test_standings_read_preserves_three_way_sporting_tie_and_registration_order_not_ids(americano_api):
    from app.americanos.models import AmericanoRegistration

    api = americano_api
    event = create_event(api)
    with Session(api.engine) as session:
        session.add_all([AmericanoRegistration(
            id=registration_id, event_id=event["id"], zone_id=event["zones"][0]["id"],
            player1_name="Nombres repetidos", player2_name="Permitidos", registration_order=order,
        ) for order, registration_id in enumerate([30, 10, 20], 1)])
        session.commit()
    response = api.client.post(f"{BASE}/{event['id']}/fixture", json={"expected_revision": event["revision"]})
    assert response.status_code == 200
    event = response.json()["event"]
    winners = {(30, 10), (10, 20), (20, 30)}
    for number in range(1, 4):
        current = _round(api, event, number)
        assert current.status_code == 200
        match = current.json()["matches"][0]
        pair = (match["registration_a"]["id"], match["registration_b"]["id"])
        event = _seed_round(api, event, number, [(5, 3) if pair in winners else (3, 5)])
    response = _standings(api, event)
    assert response.status_code == 200
    blocks = response.json()["zones"][0]["blocks"]
    assert len(blocks) == 1
    assert (blocks[0]["position_from"], blocks[0]["position_to"], blocks[0]["points_half_units"], blocks[0]["games_diff"]) == (1, 3, 2, 0)
    assert [r["registration"]["id"] for r in blocks[0]["rows"]] == [30, 10, 20]
    assert blocks[0]["rows"] == [
        _zero_row(registration) | {"played": 2, "won": 1, "lost": 1,
                                    "games_for": 8, "games_against": 8, "points_half_units": 2}
        for registration in event["registrations"]
    ]


@pytest.mark.parametrize("kind", ["round", "standings"])
def test_read_endpoints_never_mix_another_events_rounds_participants_or_scores(americano_api, kind):
    api = americano_api
    first = _generated(api)["event"]
    other = _generated(api, (4,))["event"]
    other = _seed_round(api, other, 1, [(9, 0), (9, 0)])
    response = (_round if kind == "round" else _standings)(api, first)
    assert response.status_code == 200
    first_ids = {r["id"] for r in first["registrations"]}
    if kind == "round":
        actual_ids = {m[side]["id"] for m in response.json()["matches"] for side in ["registration_a", "registration_b"]}
        assert all(m["games_a"] is None and m["games_b"] is None for m in response.json()["matches"])
        assert _round(api, first, 2).status_code == 404  # number 2 exists only in the other event
    else:
        rows = [r for z in response.json()["zones"] for b in z["blocks"] for r in b["rows"]]
        actual_ids = {r["registration"]["id"] for r in rows}
        assert all(r["played"] == r["points_half_units"] == 0 for r in rows)
    assert actual_ids == first_ids
    assert api.client.get(f"{BASE}/{other['id']}").json() == other


def test_standings_read_adds_a_win_and_zero_draw_without_float_points_or_unsaved_matches(americano_api):
    api = americano_api
    event = _generated(api, (4,))["event"]
    event = _seed_round(api, event, 1, [(5, 3), (None, None)])
    event = _seed_round(api, event, 2, [(0, 0), (None, None)])
    response = _standings(api, event)
    assert response.status_code == 200
    rows = [row for block in response.json()["zones"][0]["blocks"] for row in block["rows"]]
    ids = [r["id"] for r in event["registrations"]]
    assert [r["registration"]["id"] for r in rows] == [ids[0], ids[2], ids[1], ids[3]]
    assert rows[0] == _zero_row(event["registrations"][0]) | {
        "played": 2, "won": 1, "drawn": 1, "games_for": 5, "games_against": 3,
        "games_diff": 2, "points_half_units": 3,
    }
    assert [(r["points_half_units"], r["games_diff"]) for r in rows] == [(3, 2), (1, 0), (0, 0), (0, -2)]
    assert all(type(r["points_half_units"]) is int for r in rows)


def test_standings_read_zero_round_review_lists_singletons_without_inventing_games(americano_api):
    api = americano_api
    event = _generated(api, (1, 1))["event"]
    response = _standings(api, event)
    assert response.status_code == 200
    actual = response.json()
    assert actual["state"] == "review" and actual["frozen"] is False
    assert actual["zones"] == [{"zone": zone, "blocks": [{
        "position_from": 1, "position_to": 1, "points_half_units": 0, "games_diff": 0,
        "rows": [_zero_row(event["registrations"][index])],
    }]} for index, zone in enumerate(event["zones"])]


@pytest.mark.parametrize("event_id", ["0", "-1", "1.0", "true", "9007199254740992"])
def test_standings_read_event_path_is_strict_and_json_safe(americano_api, event_id):
    response = americano_api.client.get(f"{BASE}/{event_id}/standings")
    assert response.status_code == 422 and response.json()["code"] == "validation_error"
    assert response.json()["fields"][0]["path"] == ["event_id"]


def _results(api, event, number=1, score=(0, 0)):
    with Session(api.engine) as session:
        matches = session.exec(select(AmericanoGroupMatch).join(
            AmericanoRound, AmericanoRound.id == AmericanoGroupMatch.round_id,
        ).where(AmericanoGroupMatch.event_id == event["id"], AmericanoRound.number == number)
            .order_by(AmericanoGroupMatch.display_order)).all()
        return [{"match_id": m.id, "games_a": score[0], "games_b": score[1]} for m in matches]


def _save_round(api, event, number=1, *, results=None, revision=None):
    return api.client.put(f"{BASE}/{event['id']}/rounds/{number}/results", json={
        "expected_revision": event["revision"] if revision is None else revision,
        "results": _results(api, event, number) if results is None else results,
    })


def test_round_save_persists_complete_zero_round_and_returns_consistent_unlocked_response(americano_api):
    api = americano_api
    event = _generated(api, (4,))["event"]
    assert all(m["games_a"] is None and m["games_b"] is None for m in _round(api, event).json()["matches"])
    response = _save_round(api, event)
    assert response.status_code == 200, response.text
    actual = response.json()
    SaveRoundResponse.model_validate(actual)
    round_, standings = actual["round"], actual["standings"]
    assert round_["revision"] == standings["revision"] == event["revision"] + 1
    assert round_["groups_revision"] == standings["groups_revision"] == event["groups_revision"] + 1
    assert round_["state"] == standings["state"] == "groups"
    assert round_["saved"] is True and round_["max_unlocked_round"] == 2
    assert round_["locked"] is False and round_["read_only"] is False and standings["frozen"] is False
    assert len(round_["matches"]) == 2
    assert all(m["games_a"] == m["games_b"] == 0 for m in round_["matches"])
    assert standings["zones"][0]["blocks"] == [{
        "position_from": 1, "position_to": 4, "points_half_units": 1, "games_diff": 0,
        "rows": [_zero_row(r) | {"played": 1, "drawn": 1, "points_half_units": 1}
                 for r in event["registrations"]],
    }]
    assert _round(api, event).json() == round_
    assert _standings(api, event).json() == standings
    updated = api.client.get(f"{BASE}/{event['id']}").json()
    assert updated["saved_rounds"] == 1 and updated["total_rounds"] == 3
    assert updated["continuation"] == {"kind": "round", "round_number": 2}
    assert _round(api, event, 2).status_code == 200 and _round(api, event, 3).status_code == 409


def _db_rows(api):
    from sqlmodel import SQLModel

    with api.engine.connect() as connection:
        return {table.name: connection.execute(table.select().order_by(*table.primary_key.columns)).all()
                for table in SQLModel.metadata.sorted_tables if table.name.startswith("americano_")}


@pytest.fixture
def integer_storage_queries(americano_api):
    """Keep SQLite request tests sensitive to PostgreSQL INTEGER bind overflow.

    The disposable PG regression proves the real driver failure separately; this
    guard prevents the faster SQLite suite from silently accepting unsafe binds.
    """
    def check_bindings(_connection, _cursor, statement, parameters, _context, _many):
        if not statement.startswith("SELECT"):
            return
        values = parameters.values() if isinstance(parameters, dict) else parameters
        for value in values:
            if type(value) is int and not -(2**31) <= value < 2**31:
                raise OverflowError("Out-of-range PostgreSQL INTEGER query parameter")

    sql_event.listen(americano_api.engine, "before_cursor_execute", check_bindings)
    try:
        yield americano_api
    finally:
        sql_event.remove(americano_api.engine, "before_cursor_execute", check_bindings)


@pytest.mark.parametrize("match_id", [2_147_483_647, 2_147_483_648, 9_007_199_254_740_991])
def test_round_save_unknown_json_safe_match_is_invalid_reference_without_unsafe_binds(integer_storage_queries, match_id):
    api = integer_storage_queries
    event = _generated(api, (4,))["event"]
    _seed_ties(api, event)
    before = _db_rows(api)
    response = _save_round(api, event, results=_results(api, event, score=(5, 3)) + [
        {"match_id": match_id, "games_a": 0, "games_b": 0},
    ])
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_reference"
    assert response.json()["detail"] == response.json()["message"]
    assert "current_revision" not in response.json() and str(match_id) not in response.text
    assert _db_rows(api) == before
    assert _round(api, event, 2).status_code == 409
    # A rejected request leaves the actual round saveable at the same revision.
    retry = _save_round(api, event)
    assert retry.status_code == 200
    assert retry.json()["round"]["revision"] == event["revision"] + 1


@pytest.mark.parametrize("selection,code", [
    ("missing_last", "invalid_round_results"), ("empty", "invalid_round_results"),
    ("extra_other_round", "invalid_round_results"), ("replace_other_round", "invalid_round_results"),
    ("foreign_event", "invalid_reference"), ("nonexistent", "invalid_reference"),
])
def test_round_save_rejects_nonexact_match_membership_atomically(americano_api, selection, code):
    api = americano_api
    event = _generated(api, (4,))["event"]
    other = _generated(api, (4,))["event"]
    good = _results(api, event, score=(5, 3))
    other_round = _results(api, event, 2)[0]
    selected = {
        "missing_last": good[:1], "empty": [], "extra_other_round": good + [other_round],
        "replace_other_round": good[:1] + [other_round],
        "foreign_event": good[:1] + _results(api, other)[:1],
        "nonexistent": good + [{"match_id": 99999, "games_a": 0, "games_b": 0}],
    }[selection]
    before = _db_rows(api)
    response = _save_round(api, event, results=selected)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == code and body["detail"] == body["message"]
    assert _db_rows(api) == before
    assert _round(api, event, 2).status_code == 409
    assert api.client.get(f"{BASE}/{other['id']}").json() == other


@pytest.mark.parametrize("identity", [2_147_483_647, 2_147_483_648, 9_007_199_254_740_991])
@pytest.mark.parametrize("operation", [
    "load_event", "update_event", "add_registration", "update_registration_event",
    "delete_registration_event", "set_zones", "randomize_zones", "generate_fixture",
    "load_round_event", "load_standings", "save_round_event",
    "update_registration", "delete_registration", "load_round_number", "save_round_number",
])
def test_unknown_json_safe_path_identity_is_flat_404_without_unsafe_binds(
    integer_storage_queries, identity, operation,
):
    api = integer_storage_queries
    event = add_registration(api, create_event(api))
    # Missing nested identities must hide phase/revision even on a frozen event.
    if operation in {"update_registration", "delete_registration"}:
        with Session(api.engine) as session:
            stored = session.get(AmericanoEvent, event["id"])
            stored.state = AmericanoEventState.REVIEW
            session.add(stored)
            session.commit()
    eid = event["id"] if operation in {
        "update_registration", "delete_registration", "load_round_number", "save_round_number",
    } else identity
    registration_id = identity if operation in {"update_registration", "delete_registration"} else event["registrations"][0]["id"]
    number = identity if operation in {"load_round_number", "save_round_number"} else 1
    revision = {"expected_revision": event["revision"]}
    requests = {
        "load_event": ("GET", "", None),
        "update_event": ("PATCH", "", revision | {"name": "No change"}),
        "add_registration": ("POST", "/registrations", revision | {"player1_name": "No", "player2_name": "Change"}),
        "set_zones": ("PUT", "/zones", revision | {"zone_count": 1, "zone_a_registration_ids": []}),
        "randomize_zones": ("POST", "/zones/randomize", revision),
        "generate_fixture": ("POST", "/fixture", revision),
        "load_standings": ("GET", "/standings", None),
    }
    if operation.startswith("update_registration"):
        request = ("PATCH", f"/registrations/{registration_id}", {"expected_revision": 999, "player1_name": "No"})
    elif operation.startswith("delete_registration"):
        request = ("DELETE", f"/registrations/{registration_id}?expected_revision=999", None)
    elif operation.startswith("load_round") or operation.startswith("save_round"):
        # A real generated event is needed to reach round-number lookup on PUT.
        if operation.endswith("number"):
            event = _generated(api)["event"]
            eid = event["id"]
        request = (("GET", f"/rounds/{number}", None) if operation.startswith("load_round") else
                   ("PUT", f"/rounds/{number}/results", {"expected_revision": event["revision"], "results": []}))
    else:
        request = requests[operation]
    before = _db_rows(api)
    commits, rollbacks = [], []

    def committed(_connection):
        commits.append("commit")

    def rolled_back(_connection):
        rollbacks.append("rollback")

    sql_event.listen(api.engine, "commit", committed)
    sql_event.listen(api.engine, "rollback", rolled_back)
    try:
        method, suffix, payload = request
        response = api.client.request(method, f"{BASE}/{eid}{suffix}", json=payload)
    finally:
        sql_event.remove(api.engine, "commit", committed)
        sql_event.remove(api.engine, "rollback", rolled_back)
    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "detail": "Evento o recurso no encontrado.",
                               "message": "Evento o recurso no encontrado."}
    assert commits == [] and rollbacks == ["rollback"]
    assert _db_rows(api) == before


@pytest.mark.parametrize("identity", [2_147_483_648, 9_007_199_254_740_991])
@pytest.mark.parametrize("precedence", ["stale", "playoffs", "completed", "locked"])
def test_large_json_safe_references_preserve_revision_freeze_and_lock_precedence(
    integer_storage_queries, identity, precedence,
):
    api = integer_storage_queries
    event = _generated(api, (4,))["event"]
    if precedence in {"playoffs", "completed"}:
        event = _seed_round(api, event, 1, state=precedence)
    before = _db_rows(api)
    results = [{"match_id": identity, "games_a": 0, "games_b": 0}]
    # Large round numbers must not bypass the event's stale/frozen guards either.
    numbers = [2] if precedence == "locked" else [1, identity]
    for number in numbers:
        response = _save_round(api, event, number, results=results,
                               revision=event["revision"] - int(precedence == "stale"))
        assert response.status_code == 409
        assert response.json()["code"] == {
            "stale": "revision_conflict", "playoffs": "state_conflict",
            "completed": "state_conflict", "locked": "round_locked",
        }[precedence]
        assert response.json()["current_revision"] == event["revision"]
        assert _db_rows(api) == before


@pytest.mark.parametrize("identity", [2_147_483_647, 2_147_483_648, 9_007_199_254_740_991])
def test_zone_selection_unknown_json_safe_registration_remains_invalid_reference(integer_storage_queries, identity):
    api = integer_storage_queries
    event = add_registration(api, create_event(api, zone_count=2))
    before = _db_rows(api)
    response = api.client.put(f"{BASE}/{event['id']}/zones", json={
        "expected_revision": event["revision"], "zone_count": 2, "zone_a_registration_ids": [identity],
    })
    assert response.status_code == 422 and response.json()["code"] == "invalid_reference"
    assert _db_rows(api) == before


@pytest.mark.parametrize("number", [2, 3])
def test_round_save_rejects_locked_round_before_any_dml_or_unlock(americano_api, number):
    api = americano_api
    event = _generated(api, (4,))["event"]
    before = _db_rows(api)

    def forbid_dml(_connection, _cursor, statement, _parameters, _context, _many):
        assert statement.startswith("SELECT"), "A locked-round rejection must not attempt any mutation"

    sql_event.listen(api.engine, "before_cursor_execute", forbid_dml)
    try:
        response = _save_round(api, event, number)
    finally:
        sql_event.remove(api.engine, "before_cursor_execute", forbid_dml)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "round_locked" and body["current_revision"] == event["revision"]
    assert _db_rows(api) == before


def test_round_save_accepts_reordered_complete_results_with_real_wins(americano_api):
    api = americano_api
    event = _generated(api, (4,))["event"]
    results = _results(api, event, score=(5, 3))[::-1]
    response = _save_round(api, event, results=results)
    assert response.status_code == 200
    actual = response.json()
    assert [m["id"] for m in actual["round"]["matches"]] == [r["match_id"] for r in results[::-1]]
    assert all(m["games_a"] == 5 and m["games_b"] == 3 for m in actual["round"]["matches"])
    assert [b["points_half_units"] for b in actual["standings"]["zones"][0]["blocks"]] == [2, 0]


@pytest.mark.parametrize("sizes", [(2,), (4,)])
def test_round_save_last_round_enters_review_without_freezing_or_auto_confirming(americano_api, sizes):
    api = americano_api
    event = _generated(api, sizes)["event"]
    total = event["total_rounds"]
    for number in range(1, total + 1):
        response = _save_round(api, event, number)
        assert response.status_code == 200
        actual = response.json()
        last = number == total
        assert actual["round"]["state"] == actual["standings"]["state"] == ("review" if last else "groups")
        assert actual["round"]["read_only"] is False and actual["standings"]["frozen"] is False
        assert actual["round"]["max_unlocked_round"] == min(number + 1, total)
        event = api.client.get(f"{BASE}/{event['id']}").json()
        assert event["saved_rounds"] == number and event["groups_revision"] == number
        assert event["continuation"] == ({"kind": "qualification"} if last else {"kind": "round", "round_number": number + 1})
    rows = _db_rows(api)
    assert rows["americano_qualifier_snapshots"] == [] and rows["americano_knockout_matches"] == []
    assert event["confirmed_at"] is None and event["champion_registration_id"] is None
    corrected = _save_round(api, event, 1, results=_results(api, event, 1, score=(5, 3)))
    assert corrected.status_code == 200
    assert corrected.json()["round"]["state"] == corrected.json()["standings"]["state"] == "review"
    assert corrected.json()["round"]["groups_revision"] == event["groups_revision"] + 1
    assert corrected.json()["round"]["read_only"] is False


def _seed_ties(api, event):
    with Session(api.engine) as session:
        for zone in event["zones"]:
            registration = next(r for r in event["registrations"] if r["zone_id"] == zone["id"])
            session.add(AmericanoTieResolution(
                event_id=event["id"], zone_id=zone["id"], position=1,
                registration_id=registration["id"], source_groups_revision=event["groups_revision"],
            ))
        session.commit()


def _ties(api, event):
    with Session(api.engine) as session:
        return [row.model_dump() for row in session.exec(select(AmericanoTieResolution).where(
            AmericanoTieResolution.event_id == event["id"],
        ).order_by(AmericanoTieResolution.id)).all()]


@pytest.mark.parametrize("state", ["groups", "review"])
@pytest.mark.parametrize("changed", [False, True])
def test_round_save_only_effective_changes_advance_groups_revision_and_invalidate_all_own_ties(
    americano_api, state, changed,
):
    api = americano_api
    event = _generated(api, (4, 4) if state == "groups" else (2, 2))["event"]
    response = _save_round(api, event)
    assert response.status_code == 200
    event = api.client.get(f"{BASE}/{event['id']}").json()
    # Review is seeded explicitly here so idempotence/invalidation is tested independently of lifecycle.
    if state == "review":
        with Session(api.engine) as session:
            stored = session.get(AmericanoEvent, event["id"])
            stored.state = AmericanoEventState.REVIEW
            session.add(stored)
            session.commit()
        event = api.client.get(f"{BASE}/{event['id']}").json()
    other = _generated(api, (2, 2))["event"]
    other = _seed_round(api, other, 1, state="review")
    _seed_ties(api, event)
    _seed_ties(api, other)
    before, other_before = _ties(api, event), _ties(api, other)
    assert len(before) == len(other_before) == 2
    results = _results(api, event)
    if changed:
        results[0]["games_a"] = 9  # only one match/zone changes, but all event resolutions expire
    response = _save_round(api, event, results=results[::-1])
    assert response.status_code == 200
    actual = response.json()
    assert actual["round"]["revision"] == actual["standings"]["revision"] == event["revision"] + 1
    assert actual["round"]["groups_revision"] == actual["standings"]["groups_revision"] == event["groups_revision"] + int(changed)
    assert _ties(api, event) == ([] if changed else before)
    assert _ties(api, other) == other_before
    assert api.client.get(f"{BASE}/{other['id']}").json() == other


@pytest.mark.parametrize("saved_before", [False, True])
@pytest.mark.parametrize("failure", ["batch", "commit", "round_dto", "standings_dto", "envelope"])
def test_round_save_rolls_back_partial_batch_state_revisions_ties_and_dto_failures(
    americano_api, monkeypatch, saved_before, failure,
):
    from app.americanos import schemas, service

    api = americano_api
    event = _generated(api, (2, 2))["event"]
    if saved_before:
        assert _save_round(api, event).status_code == 200
        event = api.client.get(f"{BASE}/{event['id']}").json()
    _seed_ties(api, event)
    before = _db_rows(api)
    results = _results(api, event, score=(9, 0))
    partial_rows, flushed = [], []

    def fail_batch(cursor, statement, parameters, _context):
        if statement.startswith("UPDATE americano_group_matches"):
            assert len(parameters) >= 2
            cursor.execute(statement, parameters[0])
            partial_rows.append(cursor.rowcount)
            raise RuntimeError("injected save failure after first batch row")

    def fail_commit(session):
        if session.bind is api.engine:
            raise RuntimeError("injected save failure at commit")

    def fail_dto(*_args, **_kwargs):
        raise RuntimeError("injected save failure building response")

    def after_sql(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.startswith("UPDATE americano_group_matches"):
            flushed.append(statement)

    sql_event.listen(api.engine, "after_cursor_execute", after_sql)
    if failure == "batch":
        sql_event.listen(api.engine, "do_executemany", fail_batch)
    elif failure == "commit":
        sql_event.listen(Session, "before_commit", fail_commit)
    try:
        with monkeypatch.context() as patch:
            if failure == "round_dto":
                patch.setattr(service, "_round_detail", fail_dto)
            elif failure == "standings_dto":
                patch.setattr(service, "_standings_detail", fail_dto)
            elif failure == "envelope":
                patch.setattr(schemas, "SaveRoundResponse", fail_dto)
            with pytest.raises(RuntimeError, match="injected save failure"):
                _save_round(api, event, results=results)
    finally:
        sql_event.remove(api.engine, "after_cursor_execute", after_sql)
        if failure == "batch":
            sql_event.remove(api.engine, "do_executemany", fail_batch)
        elif failure == "commit":
            sql_event.remove(Session, "before_commit", fail_commit)
    if failure == "batch":
        assert partial_rows == [1]
    else:
        assert flushed
    assert _db_rows(api) == before
    assert api.client.get(f"{BASE}/{event['id']}").json() == event
    assert _round(api, event).json()["saved"] is saved_before
    retry = _save_round(api, event, results=results)
    assert retry.status_code == 200
    assert retry.json()["round"]["revision"] == event["revision"] + 1
    assert retry.json()["round"]["groups_revision"] == event["groups_revision"] + 1
    assert retry.json()["round"]["state"] == "review" and _ties(api, event) == []


@pytest.mark.parametrize("field", ["games_a", "games_b"])
@pytest.mark.parametrize("value", [None, "", True, False, 1.0, 1.5, "0", "5", -1, 10])
def test_round_save_rejects_noninteger_missing_or_out_of_range_games_without_zero_coercion(americano_api, field, value):
    api = americano_api
    event = _generated(api, (4,))["event"]
    results = _results(api, event)
    results[-1][field] = value
    before = _db_rows(api)
    response = _save_round(api, event, results=results)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error" and body["detail"] == body["message"]
    assert body["fields"][0]["path"] == ["results", 1, field]
    assert _db_rows(api) == before and _round(api, event, 2).status_code == 409


@pytest.mark.parametrize("invalid", ["missing_revision", "string_revision", "bool_revision", "float_revision",
                                     "missing_results", "null_results", "duplicate", "missing_game",
                                     "set_flag", "extra_body", "unsafe_id", "bool_id", "string_id"])
def test_round_save_requires_closed_unique_complete_strict_dto(americano_api, invalid):
    api = americano_api
    event = _generated(api, (4,))["event"]
    payload = {"expected_revision": event["revision"], "results": _results(api, event)}
    if invalid == "missing_revision":
        payload.pop("expected_revision")
    elif invalid in {"string_revision", "bool_revision", "float_revision"}:
        payload["expected_revision"] = {"string_revision": "1", "bool_revision": True, "float_revision": 1.0}[invalid]
    elif invalid == "missing_results":
        payload.pop("results")
    elif invalid == "null_results":
        payload["results"] = None
    elif invalid == "duplicate":
        payload["results"].append(payload["results"][0].copy())
    elif invalid == "missing_game":
        payload["results"][-1].pop("games_b")
    elif invalid == "set_flag":
        payload["results"][0]["set_complete"] = True
    elif invalid == "extra_body":
        payload["source_groups_revision"] = 0
    else:
        payload["results"][0]["match_id"] = {"unsafe_id": 9007199254740992, "bool_id": True, "string_id": "1"}[invalid]
    before = _db_rows(api)
    response = api.client.put(f"{BASE}/{event['id']}/rounds/1/results", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error" and body["fields"] and body["detail"] == body["message"]
    assert _db_rows(api) == before


@pytest.mark.parametrize("state", ["draft", "playoffs", "completed"])
@pytest.mark.parametrize("stale", [False, True])
def test_round_save_checks_revision_and_phase_under_event_lock_before_any_children(americano_api, state, stale):
    from sqlalchemy.dialects import postgresql

    api = americano_api
    event = (add_registration(api, add_registration(api, create_event(api))) if state == "draft"
             else _seed_round(api, _generated(api)["event"], 1, state=state))
    results = _results(api, event)
    before = _db_rows(api)
    statements = []

    def executed(_connection, clause, _multiparams, _params, _options):
        statements.append(str(clause.compile(dialect=postgresql.dialect())))

    sql_event.listen(api.engine, "before_execute", executed)
    try:
        response = _save_round(api, event, results=results, revision=event["revision"] - int(stale))
    finally:
        sql_event.remove(api.engine, "before_execute", executed)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == ("revision_conflict" if stale else "state_conflict")
    assert body["current_revision"] == event["revision"] and body["detail"] == body["message"]
    assert "FROM admin_users" in statements[0] and "FOR UPDATE" in statements[1]
    assert all("FROM admin_users" in sql or "FROM americano_events" in sql for sql in statements)
    assert _db_rows(api) == before


@pytest.mark.parametrize("offset", [-1, 1])
def test_round_save_rejects_old_or_future_revision_without_overwriting_or_unlocking(americano_api, offset):
    api = americano_api
    event = _generated(api, (4,))["event"]
    before = _db_rows(api)
    response = _save_round(api, event, revision=event["revision"] + offset)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "revision_conflict" and body["current_revision"] == event["revision"]
    assert body["fields"][0]["path"] == ["expected_revision"]
    assert _db_rows(api) == before and _round(api, event, 2).status_code == 409


@pytest.mark.parametrize("target", ["missing_event", "missing_round", "zero_round_review"])
def test_round_save_missing_event_or_round_is_404_without_fabricating_rounds(americano_api, target):
    api = americano_api
    event = _generated(api, (1, 1) if target == "zero_round_review" else (2,))["event"]
    if target == "missing_event":
        event = event | {"id": 99999}
    before = _db_rows(api)
    response = _save_round(api, event, 99999 if target == "missing_round" else 1, results=[])
    assert response.status_code == 404 and response.json()["code"] == "not_found"
    assert response.json()["detail"] == response.json()["message"]
    assert _db_rows(api) == before


@pytest.mark.parametrize("path_id", ["0", "-1", "1.0", "true", "9007199254740992"])
@pytest.mark.parametrize("part", ["event", "number"])
def test_round_save_path_ids_are_strict_positive_safe_integers(americano_api, path_id, part):
    api = americano_api
    event = _generated(api)["event"]
    response = api.client.put(
        f"{BASE}/{path_id if part == 'event' else event['id']}/rounds/{path_id if part == 'number' else 1}/results",
        json={"expected_revision": event["revision"], "results": _results(api, event)},
    )
    assert response.status_code == 422 and response.json()["code"] == "validation_error"
    assert response.json()["fields"][0]["path"] == ["event_id" if part == "event" else "number"]


@pytest.mark.parametrize("sizes", [(2,), (4,)])
@pytest.mark.parametrize("changed_retry", [False, True])
def test_round_save_two_ordered_sessions_reject_stale_then_accept_only_explicit_rebased_retry(
    americano_api, sizes, changed_retry,
):
    from app.americanos import service
    from app.americanos.schemas import SaveRoundRequest

    api = americano_api
    event = _generated(api, sizes)["event"]
    results = _results(api, event)
    # Sequential real Sessions on the fixture DB; not a simultaneous-writer lock test.
    with Session(api.engine, expire_on_commit=False) as observer:
        cached_event = observer.get(AmericanoEvent, event["id"])
        cached_round = observer.exec(select(AmericanoRound).where(
            AmericanoRound.event_id == event["id"], AmericanoRound.number == 1,
        )).one()
        cached_matches = observer.exec(select(AmericanoGroupMatch).where(
            AmericanoGroupMatch.round_id == cached_round.id,
        )).all()
        observer.commit()
        response = _save_round(api, event, results=results)
        assert response.status_code == 200
        first = response.json()
        assert cached_event.revision == event["revision"] and cached_round.saved_at is None
        assert all(m.games_a is None for m in cached_matches)
        with pytest.raises(service.AmericanoError) as rejected:
            service.save_round(observer, event["id"], 1, SaveRoundRequest(
                expected_revision=event["revision"], results=results,
            ))
        assert rejected.value.status == 409 and rejected.value.body.code == "revision_conflict"
        assert rejected.value.body.current_revision == first["round"]["revision"]
        assert _round(api, event).json() == first["round"]
        assert _standings(api, event).json() == first["standings"]
        canonical = api.client.get(f"{BASE}/{event['id']}").json()
        _seed_ties(api, canonical)
        before_ties = _ties(api, canonical)
        if changed_retry:
            results[0]["games_a"] = 9
        retried = service.save_round(observer, event["id"], 1, SaveRoundRequest(
            expected_revision=first["round"]["revision"], results=results,
        ))
        assert not observer.in_transaction()
        assert retried.round.revision == retried.standings.revision == first["round"]["revision"] + 1
        assert retried.round.groups_revision == retried.standings.groups_revision == first["round"]["groups_revision"] + int(changed_retry)
        assert _ties(api, canonical) == ([] if changed_retry else before_ties)


@pytest.mark.parametrize("state", ["playoffs", "completed"])
def test_round_save_cached_open_state_cannot_overwrite_groups_after_another_session_closed_them(americano_api, state):
    from app.americanos import service
    from app.americanos.schemas import SaveRoundRequest

    api = americano_api
    event = _generated(api)["event"]
    results = _results(api, event)
    with Session(api.engine, expire_on_commit=False) as observer:
        cached = observer.get(AmericanoEvent, event["id"])
        observer.commit()
        canonical = _seed_round(api, event, 1, state=state)
        assert cached.state == AmericanoEventState.GROUPS
        before = _db_rows(api)
        with pytest.raises(service.AmericanoError) as rejected:
            service.save_round(observer, event["id"], 1, SaveRoundRequest(
                expected_revision=canonical["revision"], results=results,
            ))
        assert rejected.value.status == 409 and rejected.value.body.code == "state_conflict"
        assert rejected.value.body.current_revision == canonical["revision"]
    assert _db_rows(api) == before


@pytest.mark.parametrize("sizes", [(2,), (4,)])
@pytest.mark.parametrize("operation", ["first", "identical", "correction"])
def test_round_save_locks_event_first_builds_both_dtos_and_commits_once_without_read_rollback(
    americano_api, sizes, operation,
):
    from sqlalchemy.dialects import postgresql

    api = americano_api
    event = _generated(api, sizes)["event"]
    if operation != "first":
        assert _save_round(api, event).status_code == 200
        event = api.client.get(f"{BASE}/{event['id']}").json()
    results = _results(api, event, score=(9, 0) if operation == "correction" else (0, 0))
    statements, commits, rollbacks = [], [], []

    def executed(_connection, clause, _multiparams, _params, _options):
        statements.append(str(clause.compile(dialect=postgresql.dialect())))

    def committed(_connection):
        commits.append("commit")

    def rolled_back(_connection):
        rollbacks.append("rollback")

    sql_event.listen(api.engine, "before_execute", executed)
    sql_event.listen(api.engine, "commit", committed)
    sql_event.listen(api.engine, "rollback", rolled_back)
    try:
        response = _save_round(api, event, results=results)
    finally:
        sql_event.remove(api.engine, "before_execute", executed)
        sql_event.remove(api.engine, "commit", committed)
        sql_event.remove(api.engine, "rollback", rolled_back)
    assert response.status_code == 200
    assert "FROM admin_users" in statements[0]
    assert "FROM americano_events" in statements[1] and "FOR UPDATE" in statements[1]
    assert all("FOR SHARE" not in sql for sql in statements)
    assert commits == ["commit"] and rollbacks == []
    actual = response.json()
    assert actual["round"]["revision"] == actual["standings"]["revision"] == event["revision"] + 1
    assert actual["round"]["groups_revision"] == event["groups_revision"] + int(operation != "identical")
    assert _round(api, event).json() == actual["round"]
    assert _standings(api, event).json() == actual["standings"]


@pytest.mark.parametrize("sizes", [(16,), (7, 7)])
def test_round_save_handles_six_global_matches_and_next_capacity_fragment(americano_api, sizes):
    api = americano_api
    event = _generated(api, sizes)["event"]
    assert len(_results(api, event)) == 6
    first = _save_round(api, event)
    assert first.status_code == 200 and len(first.json()["round"]["matches"]) == 6
    event = api.client.get(f"{BASE}/{event['id']}").json()
    second = _save_round(api, event, 2)
    assert second.status_code == 200
    actual = second.json()
    assert len(actual["round"]["matches"]) == (2 if sizes == (16,) else 6)
    assert actual["round"]["saved"] is True and actual["round"]["max_unlocked_round"] == 3
    assert actual["round"]["groups_revision"] == actual["standings"]["groups_revision"] == 2
    assert sum(r["played"] for z in actual["standings"]["zones"] for b in z["blocks"] for r in b["rows"]) == (
        16 if sizes == (16,) else 24
    )


def test_round_save_eleven_of_twelve_fields_never_persists_or_unlocks_until_explicit_complete_retry(americano_api):
    api = americano_api
    event = _generated(api, (7, 7))["event"]
    complete = _results(api, event)
    assert len(complete) == 6
    incomplete = [row.copy() for row in complete]
    incomplete[-1].pop("games_b")
    before = _db_rows(api)
    response = _save_round(api, event, results=incomplete)
    assert response.status_code == 422
    assert response.json()["fields"][0]["path"] == ["results", 5, "games_b"]
    assert _db_rows(api) == before and _round(api, event, 2).status_code == 409
    response = _save_round(api, event, results=complete)
    assert response.status_code == 200 and response.json()["round"]["max_unlocked_round"] == 2


def test_round_save_correcting_an_older_round_keeps_other_saved_rounds_and_recomputes_metrics(americano_api):
    api = americano_api
    event = _generated(api, (4,))["event"]
    assert _save_round(api, event).status_code == 200
    event = api.client.get(f"{BASE}/{event['id']}").json()
    second = _save_round(api, event, 2, results=_results(api, event, 2, score=(5, 3)))
    assert second.status_code == 200
    saved_second = second.json()["round"]
    event = api.client.get(f"{BASE}/{event['id']}").json()
    correction = _save_round(api, event, 1, results=_results(api, event, 1, score=(9, 0)))
    assert correction.status_code == 200
    actual = correction.json()
    assert actual["round"]["state"] == "groups" and actual["round"]["max_unlocked_round"] == 3
    assert _round(api, event, 2).json() == saved_second | {
        "revision": actual["round"]["revision"], "groups_revision": actual["round"]["groups_revision"],
    }
    event = api.client.get(f"{BASE}/{event['id']}").json()
    restored = _save_round(api, event, 1)
    assert restored.status_code == 200
    previous_standings = second.json()["standings"]
    assert restored.json()["standings"] == previous_standings | {
        "revision": restored.json()["round"]["revision"],
        "groups_revision": restored.json()["round"]["groups_revision"],
    }


@pytest.mark.parametrize("score", [(6, 3), (5, 4)])
def test_round_save_same_winner_score_correction_still_invalidates_ties_and_recomputes_games(americano_api, score):
    api = americano_api
    event = _generated(api, (2, 2))["event"]
    results = _results(api, event, score=(5, 3))
    saved = _save_round(api, event, results=results)
    assert saved.status_code == 200
    event = api.client.get(f"{BASE}/{event['id']}").json()
    other = _seed_round(api, _generated(api, (2, 2))["event"], 1, state="review")
    _seed_ties(api, event)
    _seed_ties(api, other)
    peer_ties = _ties(api, other)
    assert len(_ties(api, event)) == len(peer_ties) == 2

    def rows(standings):
        return {r["registration"]["id"]: r for z in standings["zones"] for b in z["blocks"] for r in b["rows"]}

    before = rows(saved.json()["standings"])
    results[0] |= {"games_a": score[0], "games_b": score[1]}
    corrected = _save_round(api, event, results=results)
    assert corrected.status_code == 200
    actual = corrected.json()
    assert actual["round"]["revision"] == actual["standings"]["revision"] == event["revision"] + 1
    assert actual["round"]["groups_revision"] == actual["standings"]["groups_revision"] == event["groups_revision"] + 1
    after = rows(actual["standings"])
    point_fields = ("played", "won", "drawn", "lost", "points_half_units")
    assert {i: tuple(r[f] for f in point_fields) for i, r in after.items()} == {
        i: tuple(r[f] for f in point_fields) for i, r in before.items()
    }
    winner = actual["round"]["matches"][0]["registration_a"]["id"]
    loser = actual["round"]["matches"][0]["registration_b"]["id"]
    assert (after[winner]["games_for"], after[winner]["games_against"], after[winner]["games_diff"]) == (
        score[0], score[1], score[0] - score[1],
    )
    assert after[loser]["games_diff"] == score[1] - score[0]
    assert _ties(api, event) == [] and _ties(api, other) == peer_ties
    event = api.client.get(f"{BASE}/{event['id']}").json()
    _seed_ties(api, event)
    current_ties = _ties(api, event)
    repeated = _save_round(api, event, results=results)
    assert repeated.status_code == 200
    assert repeated.json()["round"]["revision"] == event["revision"] + 1
    assert repeated.json()["round"]["groups_revision"] == event["groups_revision"]
    assert _ties(api, event) == current_ties and _ties(api, other) == peer_ties
