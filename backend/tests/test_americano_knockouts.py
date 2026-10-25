"""D8 result persistence and correction API on an independent in-memory DB."""

import pytest
from sqlalchemy import event as sql_event
from sqlmodel import Session, select

from app.americanos import service
from app.americanos.models import (
    AmericanoEvent, AmericanoEventState, AmericanoGroupMatch, AmericanoKnockoutMatch,
    AmericanoQualifierSnapshot, AmericanoRegistration, AmericanoRound, AmericanoTieResolution,
)
from app.americanos.schemas import PlayoffsResponse

from .americano_fixtures import BASE, americano_api, create_event  # noqa: F401
from .test_americano_confirmation import _confirm, _playoffs, _ready


def _closed(api, sizes=(2,), stage="final"):
    event, preview = _ready(api, sizes, stage)
    response = _confirm(api, preview)
    assert response.status_code == 200, response.text
    return response.json()["playoffs"]


def _node(bracket, stage=None, slot=1):
    return next(node for node in bracket["nodes"] if node["stage"] == (stage or bracket["start_stage"]) and node["slot"] == slot)


def _save(api, bracket, node=None, score=(6, 0), **overrides):
    node = node or _node(bracket)
    return api.client.put(f"{BASE}/{bracket['event_id']}/playoffs/{node['id']}/result", json={
        "expected_revision": bracket["revision"], "games_a": score[0], "games_b": score[1],
        "set_complete": True, **overrides,
    })


def _accepted(api, bracket, node=None, score=(6, 0)):
    response = _save(api, bracket, node, score)
    assert response.status_code == 200, response.text
    result = response.json()
    PlayoffsResponse.model_validate(result)
    assert result["revision"] == bracket["revision"] + 1
    assert result["groups_revision"] == bracket["groups_revision"]
    assert _playoffs(api, bracket["event_id"]) == result
    return result


def _group_rows(api, event_id):
    with Session(api.engine) as session:
        return [[row.model_dump() for row in session.exec(select(model).where(model.event_id == event_id)).all()]
                for model in (AmericanoRegistration, AmericanoRound, AmericanoGroupMatch,
                              AmericanoTieResolution, AmericanoQualifierSnapshot)]


@pytest.mark.parametrize("score", [(6, n) for n in range(5)] + [(7, 5), (7, 6)] + [(n, 6) for n in range(5)] + [(5, 7), (6, 7)])
def test_fourteen_approved_terminals_complete_final_with_derived_champion(americano_api, score):
    api = americano_api
    bracket = _closed(api)
    frozen = _group_rows(api, bracket["event_id"])
    node = _node(bracket)
    result = _accepted(api, bracket, score=score)
    saved = _node(result)
    winner = node["registration_a" if score[0] > score[1] else "registration_b"]["id"]
    assert (saved["games_a"], saved["games_b"], saved["set_complete"]) == (*score, True)
    assert saved["winner_registration_id"] == result["champion"]["id"] == winner
    assert saved["can_edit"] is True and saved["edit_block_reason"] is None
    assert result["state"] == "completed" and result["snapshots"] == bracket["snapshots"]
    assert _group_rows(api, bracket["event_id"]) == frozen
    assert api.client.get(f"{BASE}/{bracket['event_id']}").json()["state"] == "completed"


@pytest.mark.parametrize("score", [(5, 3), (3, 5), (6, 5), (5, 6), (8, 6), (6, 8), (7, 4), (4, 7), (9, 0), (0, 9), (10, 8), (8, 10), (1, 0), (0, 1)])
def test_nonterminal_sets_are_flat_422_and_never_persist(americano_api, score):
    api = americano_api
    bracket = _closed(api)
    response = _save(api, bracket, score=score)
    assert response.status_code == 422 and response.json()["code"] == "invalid_set"
    assert response.json()["detail"] == response.json()["message"]
    assert _playoffs(api, bracket["event_id"]) == bracket


@pytest.mark.parametrize("changes", [
    {"games_a": None}, {"games_b": ""}, {"games_a": "6"}, {"games_a": 6.0},
    {"games_b": True}, {"games_a": -1}, {"games_b": 6}, {"set_complete": False},
    {"set_complete": 1}, {"set_complete": "true"}, {"expected_revision": True},
    {"sets": [{"games_a": 6, "games_b": 0}]}, {"winner_registration_id": 1},
])
def test_result_payload_is_closed_and_strict(americano_api, changes):
    api = americano_api
    bracket = _closed(api)
    response = _save(api, bracket, **changes)
    assert response.status_code == 422 and response.json()["code"] == "validation_error"
    assert _playoffs(api, bracket["event_id"]) == bracket


@pytest.mark.parametrize("stage,sizes", [
    ("final", (2,)), ("final", (1, 1)), ("semifinal", (4,)),
    ("semifinal", (2, 2)), ("quarterfinal", (8,)), ("quarterfinal", (4, 4)),
])
def test_all_six_brackets_advance_to_champion_without_changing_groups_or_snapshots(americano_api, stage, sizes):
    api = americano_api
    bracket = _closed(api, sizes, stage)
    frozen = _group_rows(api, bracket["event_id"])
    for node_id in [node["id"] for node in bracket["nodes"]]:
        node = next(node for node in bracket["nodes"] if node["id"] == node_id)
        assert node["can_edit"] is True
        before = bracket
        bracket = _accepted(api, bracket, node)
        saved = next(candidate for candidate in bracket["nodes"] if candidate["id"] == node_id)
        assert saved["winner_registration_id"] == node["registration_a"]["id"]
        if node["next_match_id"] is not None:
            target_before = next(candidate for candidate in before["nodes"] if candidate["id"] == node["next_match_id"])
            target_after = next(candidate for candidate in bracket["nodes"] if candidate["id"] == node["next_match_id"])
            own, other = node["next_side"], "b" if node["next_side"] == "a" else "a"
            assert target_after[f"registration_{own}"] == node["registration_a"]
            assert target_after[f"registration_{other}"] == target_before[f"registration_{other}"]
            assert bracket["state"] == "playoffs" and bracket["champion"] is None
        assert _group_rows(api, bracket["event_id"]) == frozen
    assert bracket["state"] == "completed"
    final = _node(bracket, "final")
    assert bracket["champion"] == final["registration_a"]
    assert all(not node["can_edit"] and node["edit_block_reason"] == "descendant_played" for node in bracket["nodes"] if node["stage"] != "final")


def test_pending_participants_reject_409_and_get_flags_agree(americano_api):
    api = americano_api
    bracket = _closed(api, (4,), "semifinal")
    for first_saved in [False, True]:
        if first_saved:
            bracket = _accepted(api, bracket)
        final = _node(bracket, "final")
        assert not final["can_edit"] and final["edit_block_reason"] == "participants_pending"
        response = _save(api, bracket, final)
        assert response.status_code == 409 and response.json()["code"] == "participants_pending"
        assert response.json()["current_revision"] == bracket["revision"]
        assert _playoffs(api, bracket["event_id"]) == bracket


@pytest.mark.parametrize("slot", [1, 2])
@pytest.mark.parametrize("score", [(6, 1), (0, 6)])
def test_correction_preserves_other_finalist_and_changes_only_own_side(americano_api, slot, score):
    api = americano_api
    bracket = _closed(api, (4,), "semifinal")
    bracket = _accepted(api, bracket, _node(bracket, "semifinal", 1))
    bracket = _accepted(api, bracket, _node(bracket, "semifinal", 2))
    old = bracket
    target = _node(bracket, "semifinal", slot)
    bracket = _accepted(api, bracket, target, score)
    saved = _node(bracket, "semifinal", slot)
    own, other = target["next_side"], "b" if target["next_side"] == "a" else "a"
    assert _node(bracket, "final")[f"registration_{own}"]["id"] == saved["winner_registration_id"]
    assert _node(bracket, "final")[f"registration_{other}"] == _node(old, "final")[f"registration_{other}"]
    assert _node(bracket, "semifinal", 3 - slot) == _node(old, "semifinal", 3 - slot)
    assert bracket["state"] == "playoffs" and bracket["champion"] is None


@pytest.mark.parametrize("score", [(6, 0), (6, 1), (0, 6)])
def test_any_played_descendant_blocks_even_identical_or_same_winner_correction(americano_api, score):
    api = americano_api
    bracket = _closed(api, (8,), "quarterfinal")
    for slot in [1, 2]:
        bracket = _accepted(api, bracket, _node(bracket, "quarterfinal", slot))
    bracket = _accepted(api, bracket, _node(bracket, "semifinal", 1))
    target = _node(bracket, "quarterfinal", 1)
    assert not target["can_edit"] and target["edit_block_reason"] == "descendant_played"
    response = _save(api, bracket, target, score)
    assert response.status_code == 409 and response.json()["code"] == "descendant_played"
    assert response.json()["current_revision"] == bracket["revision"]
    assert _playoffs(api, bracket["event_id"]) == bracket


def test_unplayed_sibling_branch_does_not_block_correction_and_identical_put_advances_revision(americano_api):
    api = americano_api
    bracket = _closed(api, (8,), "quarterfinal")
    for slot in [1, 2, 3]:
        bracket = _accepted(api, bracket, _node(bracket, "quarterfinal", slot))
    bracket = _accepted(api, bracket, _node(bracket, "semifinal", 1))
    target = _node(bracket, "quarterfinal", 3)
    assert target["can_edit"] is True
    previous = bracket
    bracket = _accepted(api, bracket, target)
    assert bracket["nodes"] == previous["nodes"] and bracket["snapshots"] == previous["snapshots"]
    bracket = _accepted(api, bracket, _node(bracket, "quarterfinal", 3), (0, 6))
    assert _node(bracket, "semifinal", 1) == _node(previous, "semifinal", 1)


def test_final_correction_after_completed_atomically_replaces_champion_and_keeps_groups_closed(americano_api):
    api = americano_api
    bracket = _closed(api)
    frozen = _group_rows(api, bracket["event_id"])
    bracket = _accepted(api, bracket)
    first = bracket["champion"]["id"]
    bracket = _accepted(api, bracket, score=(0, 6))
    assert bracket["state"] == "completed" and bracket["champion"]["id"] != first
    assert bracket["champion"] == _node(bracket)["registration_b"]
    assert _group_rows(api, bracket["event_id"]) == frozen
    assert api.client.get(f"{BASE}/{bracket['event_id']}/qualification").json()["frozen"] is True
    response = api.client.put(f"{BASE}/{bracket['event_id']}/rounds/1/results", json={"expected_revision": bracket["revision"], "results": []})
    assert response.status_code == 409 and response.json()["code"] == "state_conflict"


def test_stale_revision_never_overwrites_current_result(americano_api):
    api = americano_api
    old = _closed(api)
    current = _accepted(api, old)
    response = _save(api, old, score=(0, 6))
    assert response.status_code == 409 and response.json()["code"] == "revision_conflict"
    assert response.json()["current_revision"] == current["revision"]
    assert _playoffs(api, old["event_id"]) == current


@pytest.mark.parametrize("foreign_id", ["other", 9999, 2_147_483_648, 9_007_199_254_740_991])
@pytest.mark.parametrize("phase", ["draft", "playoffs"])
def test_foreign_and_huge_nested_nodes_are_404_before_revision_or_phase_disclosure(americano_api, foreign_id, phase):
    api = americano_api
    peer = _closed(api)
    target = _closed(api) if phase == "playoffs" else {"event_id": create_event(api)["id"], "revision": 1}
    node_id = _node(peer)["id"] if foreign_id == "other" else foreign_id
    response = _save(api, target, {"id": node_id}, expected_revision=999999)
    assert response.status_code == 404 and response.json()["code"] == "not_found"
    assert "current_revision" not in response.json()
    assert _playoffs(api, peer["event_id"]) == peer


@pytest.mark.parametrize("phase", ["draft", "groups", "review"])
def test_own_node_in_invalid_event_phase_is_conflict_not_writable(americano_api, phase):
    api = americano_api
    bracket = _closed(api)
    with Session(api.engine) as session:
        event = session.get(AmericanoEvent, bracket["event_id"])
        event.state = AmericanoEventState(phase)
        session.add(event)
        session.commit()
    response = _save(api, bracket)
    assert response.status_code == 409 and response.json()["code"] == "state_conflict"
    assert response.json()["current_revision"] == bracket["revision"]


@pytest.mark.parametrize("failure", ["result", "advance", "champion", "output", "commit"])
def test_failures_roll_back_result_advance_champion_and_revision(americano_api, monkeypatch, failure):
    api = americano_api
    bracket = _closed(api) if failure == "champion" else _closed(api, (4,), "semifinal")
    if failure == "champion":
        bracket = _accepted(api, bracket)
    before = bracket
    frozen = _group_rows(api, bracket["event_id"])

    def fail_sql(_connection, _cursor, statement, _parameters, _context, _many):
        upper = statement.lstrip().upper()
        if (failure == "result" and upper.startswith("UPDATE AMERICANO_KNOCKOUT_MATCHES") and "GAMES_A" in upper
                or failure == "advance" and upper.startswith("UPDATE AMERICANO_KNOCKOUT_MATCHES")
                and ("REGISTRATION_A_ID" in upper or "REGISTRATION_B_ID" in upper)
                or failure == "champion" and upper.startswith("UPDATE AMERICANO_EVENTS") and "CHAMPION_REGISTRATION_ID" in upper):
            raise RuntimeError("injected knockout failure")

    def fail(*_args, **_kwargs):
        raise RuntimeError("injected knockout failure")

    original_commit = Session.commit

    def fail_commit(session):
        if session.bind is api.engine:
            fail()
        return original_commit(session)

    sql_event.listen(api.engine, "before_cursor_execute", fail_sql)
    try:
        with monkeypatch.context() as patch:
            if failure == "output":
                patch.setattr(service, "_playoffs_detail", fail)
            if failure == "commit":
                patch.setattr(Session, "commit", fail_commit)
            with pytest.raises(RuntimeError, match="injected knockout failure"):
                _save(api, bracket, score=(0, 6))
    finally:
        sql_event.remove(api.engine, "before_cursor_execute", fail_sql)
    assert _playoffs(api, bracket["event_id"]) == before
    assert _group_rows(api, bracket["event_id"]) == frozen
    assert _save(api, bracket, score=(0, 6)).status_code == 200


@pytest.mark.parametrize("damage", ["seed_participant", "destination", "seed_snapshot", "source_participant"])
def test_adapter_uses_snapshot_and_canonical_sources_not_guessed_identity(americano_api, damage):
    api = americano_api
    bracket = _closed(api, (8,), "quarterfinal")
    if damage == "source_participant":
        bracket = _accepted(api, bracket)
    with Session(api.engine) as session:
        nodes = session.exec(select(AmericanoKnockoutMatch).where(AmericanoKnockoutMatch.event_id == bracket["event_id"])).all()
        q1 = next(node for node in nodes if node.stage.value == "quarterfinal" and node.slot == 1)
        q2 = next(node for node in nodes if node.stage.value == "quarterfinal" and node.slot == 2)
        if damage == "seed_participant":
            q1.registration_a_id = q2.registration_a_id
            session.add(q1)
        elif damage == "destination":
            # Same-event FK and CHECK valid, but not the approved topology.
            q1.next_match_id = q2.id
            q1.next_side = "a"
            session.add(q1)
        elif damage == "seed_snapshot":
            snapshot = session.exec(select(AmericanoQualifierSnapshot).where(AmericanoQualifierSnapshot.event_id == bracket["event_id"])).first()
            session.delete(snapshot)
        else:
            semifinal = next(node for node in nodes if node.stage.value == "semifinal" and node.slot == 1)
            semifinal.registration_a_id = q1.registration_b_id
            session.add(semifinal)
        session.commit()
    response = _save(api, bracket, _node(bracket, "quarterfinal", 2))
    assert response.status_code == 422 and response.json()["code"] == "invalid_configuration", response.text


@pytest.mark.parametrize("event_id", [9999, 2_147_483_648, 9_007_199_254_740_991])
def test_missing_and_out_of_db_integer_events_are_flat_404(americano_api, event_id):
    response = _save(americano_api, {"event_id": event_id, "revision": 1}, {"id": 1})
    assert response.status_code == 404 and response.json()["code"] == "not_found"


@pytest.mark.parametrize("mode", ["anonymous", "expired", "inactive"])
def test_result_route_uses_existing_admin_guard_without_identity_leaks(americano_api, mode):
    api = americano_api
    api.authenticate(mode)
    response = _save(api, {"event_id": 9999, "revision": 1}, {"id": 9999}, games_a=True)
    assert response.status_code == 401 and response.json() == {"detail": "Not authenticated"}


def test_valid_result_writes_only_its_event_and_never_league_tables(americano_api):
    api = americano_api
    bracket = _closed(api)
    peer = _closed(api)
    peer_rows = _group_rows(api, peer["event_id"])
    writes = []

    def executed(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(statement)

    sql_event.listen(api.engine, "before_cursor_execute", executed)
    try:
        assert _save(api, bracket).status_code == 200
    finally:
        sql_event.remove(api.engine, "before_cursor_execute", executed)
    assert writes and all("americano_" in statement for statement in writes)
    assert _playoffs(api, peer["event_id"]) == peer
    assert _group_rows(api, peer["event_id"]) == peer_rows


def test_result_event_first_lock_and_single_commit_ordering_sqlite_probe(americano_api):
    """Inspect statements/transaction only; this is not PostgreSQL lock evidence."""
    api = americano_api
    bracket = _closed(api, (4,), "semifinal")
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
        assert _save(api, bracket).status_code == 200
    finally:
        sql_event.remove(api.engine, "before_execute", executed)
        sql_event.remove(api.engine, "commit", committed)
    assert "FROM americano_events" in str(statements[0])
    assert statements[0]._for_update_arg is not None and statements[0]._for_update_arg.read is False
    assert len(connections) == len(commits) == 1 and commits[0] in connections
