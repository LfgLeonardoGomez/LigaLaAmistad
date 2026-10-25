"""Draft request contracts, revisions and atomic zone persistence."""

import datetime
from itertools import combinations

import pytest
from pydantic import TypeAdapter
from sqlalchemy import event as sql_event
from sqlmodel import Session, select

from app.americanos.models import (
    AmericanoEvent, AmericanoEventState, AmericanoGroupMatch, AmericanoRegistration,
    AmericanoRound, AmericanoZone,
)
from app.americanos.schemas import EventDetail, GenerateFixtureResponse, ListEventsResponse

from .americano_fixtures import BASE, add_registration, americano_api, create_event  # noqa: F401


@pytest.mark.parametrize("zone_count,stage,required", [
    (1, "final", 2), (2, "final", 1), (1, "semifinal", 4),
    (2, "semifinal", 2), (1, "quarterfinal", 8), (2, "quarterfinal", 4),
])
def test_empty_draft_has_canonical_detail(americano_api, zone_count, stage, required):
    api = americano_api
    detail = create_event(api, name="  Sábado ñ  ", zone_count=zone_count, start_stage=stage)
    EventDetail.model_validate(detail)
    assert detail["name"] == "Sábado ñ"
    assert (detail["state"], detail["revision"], detail["groups_revision"]) == ("draft", 1, 0)
    assert detail["registrations"] == []
    assert detail["registration_count"] == detail["total_rounds"] == detail["saved_rounds"] == 0
    assert detail["max_unlocked_round"] == 0
    assert detail["continuation"] == {"kind": "setup"}
    assert detail["confirmed_at"] is None and detail["champion_registration_id"] is None
    assert [zone["label"] for zone in detail["zones"]] == (["A"] if zone_count == 1 else ["A", "B"])
    assert detail["can_generate"] is False
    assert detail["quotas"] == [
        {"zone_id": zone["id"], "required": required, "registered": 0, "sufficient": False}
        for zone in detail["zones"]
    ]
    assert [issue["code"] for issue in detail["configuration_issues"]] == [
        "insufficient_registrations",
    ] * zone_count
    response = api.client.get(f"{BASE}/{detail['id']}")
    assert response.status_code == 200
    assert response.json() == detail


def test_list_empty_then_newest_first_with_repeated_names(americano_api):
    api = americano_api
    assert api.client.get(BASE).json() == []
    first = create_event(api)
    second = create_event(api)
    response = api.client.get(BASE, follow_redirects=False)
    assert response.status_code == 200
    summaries = TypeAdapter(ListEventsResponse).validate_python(response.json())
    assert [summary.id for summary in summaries] == [second["id"], first["id"]]
    assert [summary.name for summary in summaries] == ["Encuentro", "Encuentro"]
    assert "registrations" not in response.json()[0]


@pytest.mark.parametrize("state,expected", [
    ("groups", {"kind": "round", "round_number": 2}),
    ("review", {"kind": "qualification"}),
    ("playoffs", {"kind": "playoffs"}), ("completed", {"kind": "playoffs"}),
])
def test_history_continuation_counts_real_rounds_without_writes(americano_api, state, expected):
    api = americano_api
    detail = create_event(api)
    with Session(api.engine) as session:
        stored = session.get(AmericanoEvent, detail["id"])
        stored.state = AmericanoEventState(state)
        stored.revision = 9
        stored.groups_revision = 4
        session.add(stored)
        session.add_all([
            AmericanoRound(event_id=stored.id, number=1, saved_at=datetime.datetime.now(datetime.UTC)),
            AmericanoRound(event_id=stored.id, number=2),
            AmericanoRound(event_id=stored.id, number=3, saved_at=datetime.datetime.now(datetime.UTC)),
        ])
        session.commit()
        session.refresh(stored)
        before = stored.model_dump()
    response = api.client.get(f"{BASE}/{detail['id']}")
    assert response.status_code == 200
    actual = response.json()
    assert (actual["total_rounds"], actual["saved_rounds"], actual["max_unlocked_round"]) == (3, 2, 2)
    assert actual["continuation"] == expected
    assert actual["can_generate"] is False
    assert api.client.get(BASE).json()[0]["continuation"] == expected
    with Session(api.engine) as session:
        assert session.get(AmericanoEvent, detail["id"]).model_dump() == before


def test_unknown_event_returns_flat_not_found(americano_api):
    response = americano_api.client.get(f"{BASE}/999")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert body["detail"] == body["message"]
    assert "current_revision" not in body


@pytest.mark.parametrize("changes", [
    {"zone_count": True}, {"zone_count": "1"}, {"zone_count": 1.0},
    {"name": "  "}, {"start_stage": "semi"}, {"revision": 1}, {"name": None},
])
def test_create_strict_validation_is_flat_and_atomic(americano_api, changes):
    api = americano_api
    payload = {"name": "Evento", "zone_count": 1, "start_stage": "final"} | changes
    response = api.client.post(BASE, json=payload)
    assert response.status_code == 422
    error = response.json()
    assert error["code"] == "validation_error"
    assert error["detail"] == error["message"]
    assert error["fields"] and "body" not in error["fields"][0]["path"]
    with Session(api.engine) as session:
        assert session.exec(select(AmericanoEvent)).all() == []
        assert session.exec(select(AmericanoZone)).all() == []


@pytest.mark.parametrize("zone_count", [1, 2])
def test_create_rolls_back_event_and_zones_after_insert_failure(americano_api, zone_count):
    api = americano_api

    def fail_zone(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.startswith("INSERT INTO americano_zones"):
            raise RuntimeError("injected zone failure")

    sql_event.listen(api.engine, "before_cursor_execute", fail_zone)
    try:
        with pytest.raises(RuntimeError, match="injected zone failure"):
            create_event(api, zone_count=zone_count)
    finally:
        sql_event.remove(api.engine, "before_cursor_execute", fail_zone)
    assert api.client.get(BASE).json() == []
    recovered = create_event(api, name="Recuperado", zone_count=zone_count)
    assert recovered["revision"] == 1
    assert len(recovered["zones"]) == zone_count


@pytest.mark.parametrize("changes", [
    {"name": "  Nuevo  "}, {"start_stage": "semifinal"},
    {"name": "Encuentro", "zone_count": 1, "start_stage": "final"},
])
def test_patch_changes_once_and_identical_patch_also_advances_revision(americano_api, changes):
    api = americano_api
    detail = create_event(api)
    response = api.client.patch(f"{BASE}/{detail['id']}", json={"expected_revision": 1} | changes)
    assert response.status_code == 200
    updated = response.json()
    EventDetail.model_validate(updated)
    assert updated["revision"] == 2 and updated["groups_revision"] == 0
    for key, value in changes.items():
        assert updated[key] == (value.strip() if isinstance(value, str) else value)
    assert updated["zones"] == detail["zones"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == updated


@pytest.mark.parametrize("invalid_selection,code", [
    ("foreign", "invalid_reference"), ("missing", "invalid_reference"),
    ("incomplete_single", "invalid_configuration"),
])
def test_manual_zones_reject_invalid_selection_before_changing_zone_count(
    americano_api, invalid_selection, code,
):
    api = americano_api
    detail = add_registration(api, add_registration(api, create_event(api)))
    other = add_registration(api, create_event(api))
    selected = [r["id"] for r in detail["registrations"]]
    count = 2
    if invalid_selection == "foreign":
        selected.append(other["registrations"][0]["id"])
    elif invalid_selection == "missing":
        selected.append(99999)
    else:
        count, selected = 1, selected[:1]
    response = api.client.put(f"{BASE}/{detail['id']}/zones", json={
        "expected_revision": detail["revision"], "zone_count": count,
        "zone_a_registration_ids": selected,
    })
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == code and body["detail"] == body["message"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail
    assert api.client.get(f"{BASE}/{other['id']}").json() == other


def test_zone_count_change_preserves_a_and_rehomes_b_before_deleting_it(americano_api):
    api = americano_api
    detail = create_event(api, zone_count=2)
    a, b = detail["zones"]
    with Session(api.engine) as session:
        session.add_all([
            AmericanoRegistration(event_id=detail["id"], zone_id=zone_id,
                                  player1_name="Ana", player2_name="Sol", registration_order=order)
            for order, zone_id in enumerate([a["id"], b["id"], None], 1)
        ])
        session.commit()
    response = api.client.patch(f"{BASE}/{detail['id']}", json={
        "expected_revision": 1, "zone_count": 1,
    })
    assert response.status_code == 200
    one = response.json()
    assert one["zones"] == [a]
    assert [r["zone_id"] for r in one["registrations"]] == [a["id"]] * 3
    assert one["quotas"] == [{"zone_id": a["id"], "required": 2, "registered": 3, "sufficient": True}]
    assert one["configuration_issues"] == [] and one["can_generate"] is True
    response = api.client.patch(f"{BASE}/{detail['id']}", json={
        "expected_revision": 2, "zone_count": 2,
    })
    assert response.status_code == 200
    two = response.json()
    assert two["zones"][0] == a and two["zones"][1]["label"] == "B"
    assert [r["zone_id"] for r in two["registrations"]] == [a["id"]] * 3
    assert two["revision"] == 3 and two["groups_revision"] == 0
    assert two["quotas"][1]["registered"] == 0 and two["can_generate"] is False


@pytest.mark.parametrize("state", ["groups", "review", "playoffs", "completed"])
def test_patch_after_draft_returns_flat_phase_conflict_without_changes(americano_api, state):
    api = americano_api
    detail = create_event(api)
    with Session(api.engine) as session:
        stored = session.get(AmericanoEvent, detail["id"])
        stored.state = AmericanoEventState(state)
        session.add(stored)
        session.commit()
    response = api.client.patch(f"{BASE}/{detail['id']}", json={
        "expected_revision": 1, "name": "No guardar", "zone_count": 2,
    })
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "state_conflict" and body["current_revision"] == 1
    assert body["detail"] == body["message"]
    with Session(api.engine) as session:
        stored = session.get(AmericanoEvent, detail["id"])
        assert stored.name == "Encuentro" and stored.zone_count == 1 and stored.revision == 1


@pytest.mark.parametrize("old_revision", [1, 3])
def test_patch_stale_or_future_revision_never_overwrites(americano_api, old_revision):
    api = americano_api
    detail = create_event(api)
    assert api.client.patch(f"{BASE}/{detail['id']}", json={
        "expected_revision": 1, "name": "Canónico",
    }).status_code == 200
    response = api.client.patch(f"{BASE}/{detail['id']}", json={
        "expected_revision": old_revision, "name": "Obsoleto",
    })
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "revision_conflict" and body["current_revision"] == 2
    assert body["detail"] == body["message"]
    assert body["fields"][0]["path"] == ["expected_revision"]
    assert api.client.get(f"{BASE}/{detail['id']}").json()["name"] == "Canónico"


@pytest.mark.parametrize("payload", [
    {"expected_revision": 1}, {"expected_revision": 1, "name": None},
    {"expected_revision": True, "name": "Nuevo"}, {"expected_revision": 1, "zone_count": 1.0},
    {"expected_revision": 1, "state": "draft"}, {"expected_revision": 1, "name": " "},
])
def test_patch_invalid_payload_preserves_draft(americano_api, payload):
    api = americano_api
    detail = create_event(api)
    response = api.client.patch(f"{BASE}/{detail['id']}", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


@pytest.mark.parametrize("zone_count", [1, 2])
def test_add_trims_names_allows_duplicates_assigns_order_and_reports_real_quotas(americano_api, zone_count):
    api = americano_api
    detail = create_event(api, zone_count=zone_count)
    detail = add_registration(api, detail, first="  Ana ñ  ", second=" Sol ")
    detail = add_registration(api, detail, first="  Ana ñ  ", second=" Sol ")
    EventDetail.model_validate(detail)
    assert detail["revision"] == 3 and detail["groups_revision"] == 0
    assert detail["registration_count"] == 2
    registrations = detail["registrations"]
    assert registrations[0]["id"] != registrations[1]["id"]
    assert [r["registration_order"] for r in registrations] == [1, 2]
    assert [(r["player1_name"], r["player2_name"]) for r in registrations] == [("Ana ñ", "Sol")] * 2
    expected_zone = detail["zones"][0]["id"] if zone_count == 1 else None
    assert [r["zone_id"] for r in registrations] == [expected_zone] * 2
    if zone_count == 1:
        assert detail["can_generate"] is True and detail["configuration_issues"] == []
        assert detail["quotas"][0]["registered"] == 2
    else:
        assert detail["can_generate"] is False
        assert [q["registered"] for q in detail["quotas"]] == [0, 0]
        assert detail["configuration_issues"][-1]["registration_ids"] == [r["id"] for r in registrations]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail
    assert api.client.get(BASE).json()[0]["registration_count"] == 2


@pytest.mark.parametrize("size", [5, 8, 14, 17])
def test_variable_registration_counts_have_no_fixed_capacity(americano_api, size):
    api = americano_api
    detail = create_event(api, start_stage="quarterfinal")
    for index in range(size):
        detail = add_registration(api, detail, first=f"Pareja {index}")
    assert detail["registration_count"] == size and detail["revision"] == size + 1
    assert [r["registration_order"] for r in detail["registrations"]] == list(range(1, size + 1))
    assert detail["can_generate"] is (size >= 8)


@pytest.mark.parametrize("payload", [
    {"expected_revision": "1", "player1_name": "A", "player2_name": "B"},
    {"expected_revision": 1, "player1_name": " ", "player2_name": "B"},
    {"expected_revision": 1, "player1_name": "A"},
    {"expected_revision": 1, "player1_name": "A", "player2_name": "B", "zone_id": 1},
])
def test_add_rejects_strict_or_client_assigned_fields_without_mutation(americano_api, payload):
    api = americano_api
    detail = create_event(api)
    response = api.client.post(f"{BASE}/{detail['id']}/registrations", json=payload)
    assert response.status_code == 422 and response.json()["code"] == "validation_error"
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


@pytest.mark.parametrize("changes", [
    {"player1_name": "  Eva  "}, {"player2_name": "  Luz  "},
    {"player1_name": "Ana", "player2_name": "Sol"},
])
def test_update_registration_preserves_identity_order_zone_and_other_event(americano_api, changes):
    api = americano_api
    detail = add_registration(api, create_event(api))
    other = add_registration(api, create_event(api))
    original = detail["registrations"][0]
    response = api.client.patch(f"{BASE}/{detail['id']}/registrations/{original['id']}", json={
        "expected_revision": detail["revision"], **changes,
    })
    assert response.status_code == 200
    updated = response.json()
    assert updated["revision"] == 3 and updated["groups_revision"] == 0
    assert updated["registrations"] == [original | {key: value.strip() for key, value in changes.items()}]
    assert api.client.get(f"{BASE}/{other['id']}").json() == other
    assert api.client.get(f"{BASE}/{detail['id']}").json() == updated


@pytest.mark.parametrize("deleted_index", [0, 1, 2])
def test_delete_returns_detail_and_next_order_never_collides_with_survivors(americano_api, deleted_index):
    api = americano_api
    detail = create_event(api)
    for name in ["Ana", "Eva", "Luz"]:
        detail = add_registration(api, detail, first=name)
    removed = detail["registrations"][deleted_index]
    survivors = [r for r in detail["registrations"] if r != removed]
    response = api.client.delete(
        f"{BASE}/{detail['id']}/registrations/{removed['id']}?expected_revision={detail['revision']}",
    )
    assert response.status_code == 200
    deleted = response.json()
    EventDetail.model_validate(deleted)
    compact_survivors = [r | {"registration_order": order} for order, r in enumerate(survivors, 1)]
    assert deleted["registrations"] == compact_survivors
    assert deleted["revision"] == 5 and deleted["registration_count"] == 2
    assert deleted["groups_revision"] == 0
    replay = api.client.delete(
        f"{BASE}/{detail['id']}/registrations/{removed['id']}?expected_revision=5",
    )
    assert replay.status_code == 404
    assert api.client.get(f"{BASE}/{detail['id']}").json() == deleted
    added = add_registration(api, deleted, first="Nueva")
    assert added["registrations"][:-1] == compact_survivors
    orders = [r["registration_order"] for r in added["registrations"]]
    assert orders == [1, 2, 3]


def test_delete_last_registration_returns_empty_draft_not_204(americano_api):
    api = americano_api
    detail = add_registration(api, create_event(api, zone_count=2))
    response = api.client.delete(
        f"{BASE}/{detail['id']}/registrations/{detail['registrations'][0]['id']}?expected_revision=2",
    )
    assert response.status_code == 200
    deleted = response.json()
    assert deleted["registrations"] == [] and deleted["registration_count"] == 0
    assert deleted["revision"] == 3 and deleted["can_generate"] is False
    assert deleted["zones"] == detail["zones"]
    assert all(issue["code"] == "insufficient_registrations" for issue in deleted["configuration_issues"])
    added = add_registration(api, deleted)
    assert added["registrations"][0]["registration_order"] == 1


@pytest.mark.parametrize("zone_count", [1, 2])
def test_bulk_registration_adds_multiple_pairs_in_one_revision(americano_api, zone_count):
    api = americano_api
    detail = create_event(api, zone_count=zone_count)
    payload = {
        "expected_revision": detail["revision"],
        "registrations": [
            {"player1_name": "  Ana ", "player2_name": " Sol  "},
            {"player1_name": "Eva", "player2_name": "Luz"},
            {"player1_name": "Mia", "player2_name": "Noe"},
        ],
    }
    response = api.client.post(f"{BASE}/{detail['id']}/registrations/bulk", json=payload)
    assert response.status_code == 201, response.text
    updated = response.json()
    assert updated["revision"] == detail["revision"] + 1
    assert [r["registration_order"] for r in updated["registrations"]] == [1, 2, 3]
    assert [(r["player1_name"], r["player2_name"]) for r in updated["registrations"]] == [
        ("Ana", "Sol"), ("Eva", "Luz"), ("Mia", "Noe"),
    ]
    if zone_count == 1:
        assert all(r["zone_id"] == updated["zones"][0]["id"] for r in updated["registrations"])
    else:
        assert all(r["zone_id"] is None for r in updated["registrations"])


@pytest.mark.parametrize("assignment", ["manual", "random"])
def test_clear_zones_unassigns_saved_manual_or_random_distribution(americano_api, assignment):
    api = americano_api
    detail = create_event(api, zone_count=2)
    detail = api.client.post(f"{BASE}/{detail['id']}/registrations/bulk", json={
        "expected_revision": detail["revision"],
        "registrations": [
            {"player1_name": f"P{i}", "player2_name": f"Q{i}"} for i in range(4)
        ],
    }).json()
    if assignment == "manual":
        response = api.client.put(f"{BASE}/{detail['id']}/zones", json={
            "expected_revision": detail["revision"], "zone_count": 2,
            "zone_a_registration_ids": [r["id"] for r in detail["registrations"][:2]],
        })
    else:
        response = api.client.post(f"{BASE}/{detail['id']}/zones/randomize", json={
            "expected_revision": detail["revision"],
        })
    assert response.status_code == 200
    assigned = response.json()
    assert all(r["zone_id"] is not None for r in assigned["registrations"])
    response = api.client.delete(f"{BASE}/{detail['id']}/zones?expected_revision={assigned['revision']}")
    assert response.status_code == 200, response.text
    cleared = response.json()
    assert cleared["revision"] == assigned["revision"] + 1
    assert all(r["zone_id"] is None for r in cleared["registrations"])
    assert cleared["can_generate"] is False
    assert "unassigned_registrations" in {issue["code"] for issue in cleared["configuration_issues"]}


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
@pytest.mark.parametrize("state", ["groups", "review", "playoffs", "completed"])
def test_registration_mutations_reject_every_non_draft_phase(americano_api, method, state):
    api = americano_api
    detail = add_registration(api, create_event(api))
    registration = detail["registrations"][0]
    with Session(api.engine) as session:
        stored = session.get(AmericanoEvent, detail["id"])
        stored.state = AmericanoEventState(state)
        session.add(stored)
        if state == "groups":
            session.add(AmericanoRound(event_id=stored.id, number=1))
        session.commit()
    before = api.client.get(f"{BASE}/{detail['id']}").json()
    path = f"{BASE}/{detail['id']}/registrations"
    payload = {"expected_revision": 2, "player1_name": "No guardar", "player2_name": "Tampoco"}
    if method != "POST":
        path += f"/{registration['id']}"
    if method == "DELETE":
        response = api.client.delete(path + "?expected_revision=2")
    else:
        response = api.client.request(method, path, json=payload)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "state_conflict" and body["current_revision"] == 2
    assert body["detail"] == body["message"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == before


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
def test_registration_stale_revision_keeps_canonical_data(americano_api, method):
    api = americano_api
    detail = add_registration(api, create_event(api))
    path = f"{BASE}/{detail['id']}/registrations"
    if method != "POST":
        path += f"/{detail['registrations'][0]['id']}"
    if method == "DELETE":
        response = api.client.delete(path + "?expected_revision=1")
    else:
        response = api.client.request(method, path, json={
            "expected_revision": 1, "player1_name": "Obsoleta", "player2_name": "Obsoleto",
        })
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "revision_conflict" and body["current_revision"] == 2
    assert body["fields"][0]["path"] == ["expected_revision"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


@pytest.mark.parametrize("payload", [
    {"expected_revision": 2}, {"expected_revision": 2, "player1_name": None},
    {"expected_revision": 2, "player2_name": " "},
    {"expected_revision": 2, "registration_order": 9},
    {"expected_revision": 2, "zone_id": 1},
])
def test_update_registration_rejects_null_empty_and_server_fields(americano_api, payload):
    api = americano_api
    detail = add_registration(api, create_event(api))
    response = api.client.patch(
        f"{BASE}/{detail['id']}/registrations/{detail['registrations'][0]['id']}", json=payload,
    )
    assert response.status_code == 422 and response.json()["code"] == "validation_error"
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


@pytest.mark.parametrize("query", ["", "?expected_revision=0", "?expected_revision=true",
                                   "?expected_revision=2.0", "?expected_revision=-1"])
def test_delete_requires_positive_integer_revision_in_query(americano_api, query):
    api = americano_api
    detail = add_registration(api, create_event(api))
    response = api.client.delete(
        f"{BASE}/{detail['id']}/registrations/{detail['registrations'][0]['id']}" + query,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["fields"][0]["path"] == ["expected_revision"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


@pytest.mark.parametrize("operation", ["create", "update", "add", "bulk", "rename", "delete", "zones", "randomize", "clear"])
def test_each_mutation_commits_once_and_locks_event_before_children(americano_api, operation):
    # SQL compilation verifies lock intent only; SQLite cannot prove row locking.
    from sqlalchemy.dialects import postgresql

    api = americano_api
    detail = add_registration(api, create_event(api, zone_count=2))
    commits, statements = [], []

    def committed(_connection):
        commits.append("commit")

    def executed(_connection, clause, _multiparams, _params, _options):
        statements.append(str(clause.compile(dialect=postgresql.dialect())))

    sql_event.listen(api.engine, "commit", committed)
    sql_event.listen(api.engine, "before_execute", executed)
    try:
        response = _mutate(api, operation, detail)
    finally:
        sql_event.remove(api.engine, "commit", committed)
        sql_event.remove(api.engine, "before_execute", executed)
    assert response.status_code == (201 if operation in {"create", "add", "bulk"} else 200)
    assert commits == ["commit"]
    assert response.json()["revision"] == (1 if operation == "create" else 3)
    assert response.json()["groups_revision"] == 0
    assert "FROM admin_users" in statements[0]  # real auth opens the shared transaction
    if operation != "create":
        assert "FROM americano_events" in statements[1] and "FOR UPDATE" in statements[1]
    assert all("FOR SHARE" not in statement for statement in statements)


@pytest.mark.parametrize("operation", ["create", "update", "add", "bulk", "rename", "delete", "zones", "randomize", "clear"])
def test_commit_failure_rolls_back_all_rows_and_revision(americano_api, operation):
    api = americano_api
    detail = add_registration(api, create_event(api, zone_count=2))
    before = api.client.get(BASE).json()

    def fail_commit(session):
        if session.bind is api.engine:
            raise RuntimeError("injected commit failure")

    sql_event.listen(Session, "before_commit", fail_commit)
    try:
        with pytest.raises(RuntimeError, match="injected commit failure"):
            _mutate(api, operation, detail)
    finally:
        sql_event.remove(Session, "before_commit", fail_commit)
    assert api.client.get(BASE).json() == before
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail
    # A fresh request after rollback must still be able to use the old revision.
    assert _mutate(api, operation, detail).status_code in {200, 201}


def _mutate(api, operation, detail):
    path = f"{BASE}/{detail['id']}"
    revision = detail["revision"]
    if operation == "create":
        return api.client.post(BASE, json={"name": "Nuevo", "zone_count": 2, "start_stage": "final"})
    if operation == "update":
        return api.client.patch(path, json={"expected_revision": revision, "name": "Nuevo", "zone_count": 1})
    if operation == "clear":
        return api.client.delete(path + f"/zones?expected_revision={revision}")
    if operation in {"zones", "randomize"}:
        return _assign_zones(api, operation, detail)
    path += "/registrations"
    if operation == "add":
        return api.client.post(path, json={"expected_revision": revision, "player1_name": "Eva", "player2_name": "Luz"})
    if operation == "bulk":
        return api.client.post(path + "/bulk", json={"expected_revision": revision, "registrations": [
            {"player1_name": "Eva", "player2_name": "Luz"},
            {"player1_name": "Ana", "player2_name": "Sol"},
        ]})
    path += f"/{detail['registrations'][0]['id']}"
    if operation == "rename":
        return api.client.patch(path, json={"expected_revision": revision, "player2_name": "Luz"})
    return api.client.delete(path + f"?expected_revision={revision}")


@pytest.mark.parametrize("path", [BASE, BASE + "/1"])
def test_get_uses_share_lock_without_commit_or_dml(americano_api, path):
    from sqlalchemy.dialects import postgresql

    api = americano_api
    add_registration(api, create_event(api))
    statements, commits = [], []

    def executed(_connection, clause, _multiparams, _params, _options):
        statements.append(str(clause.compile(dialect=postgresql.dialect())))

    def committed(_connection):
        commits.append("commit")

    sql_event.listen(api.engine, "before_execute", executed)
    sql_event.listen(api.engine, "commit", committed)
    try:
        response = api.client.get(path)
    finally:
        sql_event.remove(api.engine, "before_execute", executed)
        sql_event.remove(api.engine, "commit", committed)
    assert response.status_code == 200
    assert commits == []
    assert statements and all(statement.startswith("SELECT") for statement in statements)
    assert "FROM americano_events" in statements[1] and "FOR SHARE" in statements[1]


@pytest.mark.parametrize("path_id", ["0", "-1", "1.0", "true", "9007199254740992", "9999999999999999999999"])
def test_path_ids_are_positive_safe_integers_before_database_access(americano_api, path_id):
    api = americano_api
    create_event(api)
    response = api.client.get(f"{BASE}/{path_id}")
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert response.json()["fields"][0]["path"] == ["event_id"]


@pytest.mark.parametrize("operation", ["update", "add", "bulk", "rename", "delete", "clear"])
def test_mutations_of_missing_event_return_flat_404(americano_api, operation):
    detail = {"id": 999, "revision": 1, "registrations": [{"id": 999}]}
    response = _mutate(americano_api, operation, detail)
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found" and body["detail"] == body["message"]
    assert "current_revision" not in body


def test_expanding_to_two_zones_keeps_a_and_new_registration_is_unassigned(americano_api):
    api = americano_api
    detail = add_registration(api, create_event(api))
    a = detail["zones"][0]
    response = api.client.patch(f"{BASE}/{detail['id']}", json={"expected_revision": 2, "zone_count": 2})
    assert response.status_code == 200
    detail = add_registration(api, response.json(), first="Nueva")
    assert detail["zones"][0] == a
    assert [r["zone_id"] for r in detail["registrations"]] == [a["id"], None]
    assert detail["quotas"][0]["sufficient"] is True
    assert detail["quotas"][1]["sufficient"] is False
    assert detail["configuration_issues"][-1]["registration_ids"] == [detail["registrations"][1]["id"]]


def test_two_sufficient_zones_and_zero_round_review_use_actual_data(americano_api):
    api = americano_api
    detail = create_event(api, zone_count=2)
    detail = add_registration(api, add_registration(api, detail))
    with Session(api.engine) as session:
        registrations = session.exec(select(AmericanoRegistration).order_by(AmericanoRegistration.id)).all()
        for registration, zone in zip(registrations, detail["zones"], strict=True):
            registration.zone_id = zone["id"]
            session.add(registration)
        session.commit()
    eligible = api.client.get(f"{BASE}/{detail['id']}").json()
    assert eligible["can_generate"] is True and eligible["configuration_issues"] == []
    assert [quota["registered"] for quota in eligible["quotas"]] == [1, 1]
    with Session(api.engine) as session:
        stored = session.get(AmericanoEvent, detail["id"])
        stored.state = AmericanoEventState.REVIEW
        session.add(stored)
        session.commit()
    review = api.client.get(f"{BASE}/{detail['id']}").json()
    assert review["total_rounds"] == review["saved_rounds"] == review["max_unlocked_round"] == 0
    assert review["continuation"] == {"kind": "qualification"} and review["can_generate"] is False
    with Session(api.engine) as session:
        stored = session.get(AmericanoEvent, detail["id"])
        stored.state = AmericanoEventState.COMPLETED
        stored.confirmed_at = datetime.datetime(2026, 10, 21, 12, tzinfo=datetime.UTC)
        stored.champion_registration_id = detail["registrations"][0]["id"]
        session.add(stored)
        session.commit()
    completed = api.client.get(f"{BASE}/{detail['id']}").json()
    assert completed["champion_registration_id"] == detail["registrations"][0]["id"]
    assert completed["confirmed_at"] == "2026-10-21T12:00:00+00:00"
    assert completed["continuation"] == {"kind": "playoffs"}


def test_manual_zones_persist_unequal_a_selection_and_b_complement(americano_api):
    api = americano_api
    detail = create_event(api, zone_count=2, start_stage="semifinal")
    for index in range(9):
        detail = add_registration(api, detail, first=f"Pareja {index}")
    selected = [r["id"] for r in detail["registrations"][:5]]
    response = api.client.put(f"{BASE}/{detail['id']}/zones", json={
        "expected_revision": detail["revision"], "zone_count": 2,
        "zone_a_registration_ids": selected,
    })
    assert response.status_code == 200, response.text
    updated = response.json()
    EventDetail.model_validate(updated)
    a, b = updated["zones"]
    assert updated["registrations"] == [
        r | {"zone_id": a["id"] if r["id"] in selected else b["id"]}
        for r in detail["registrations"]
    ]
    assert [q["registered"] for q in updated["quotas"]] == [5, 4]
    assert updated["can_generate"] is True and updated["configuration_issues"] == []
    assert updated["revision"] == detail["revision"] + 1
    assert updated["groups_revision"] == 0 and updated["state"] == "draft"
    assert updated["total_rounds"] == 0
    assert api.client.get(f"{BASE}/{detail['id']}").json() == updated


def test_random_zones_are_balanced_persisted_and_never_reshuffled_by_reads(americano_api):
    api = americano_api
    detail = create_event(api, zone_count=2)
    for index in range(15):
        detail = add_registration(api, detail, first=f"Pareja {index}")
    response = api.client.post(f"{BASE}/{detail['id']}/zones/randomize", json={
        "expected_revision": detail["revision"],
    })
    assert response.status_code == 200, response.text
    updated = response.json()
    EventDetail.model_validate(updated)
    assert sorted(q["registered"] for q in updated["quotas"]) == [7, 8]
    assert {r["id"] for r in updated["registrations"]} == {r["id"] for r in detail["registrations"]}
    assert all(r["zone_id"] in {z["id"] for z in detail["zones"]} for r in updated["registrations"])
    assert updated["revision"] == detail["revision"] + 1 and updated["groups_revision"] == 0
    assert updated["can_generate"] is True and updated["state"] == "draft"
    assert updated["configuration_issues"] == [] and updated["total_rounds"] == 0
    for _ in range(3):
        assert api.client.get(f"{BASE}/{detail['id']}").json() == updated
        assert api.client.get(BASE).json()[0]["revision"] == updated["revision"]
    with Session(api.engine) as session:
        stored = session.exec(select(AmericanoRegistration).where(
            AmericanoRegistration.event_id == detail["id"],
        ).order_by(AmericanoRegistration.registration_order)).all()
        assert [(r.id, r.zone_id) for r in stored] == [
            (r["id"], r["zone_id"]) for r in updated["registrations"]
        ]


@pytest.mark.parametrize("size", [0, 2])
def test_random_zones_reject_single_zone_without_mutating_draft(americano_api, size):
    api = americano_api
    detail = create_event(api)
    for _ in range(size):
        detail = add_registration(api, detail)
    response = api.client.post(f"{BASE}/{detail['id']}/zones/randomize", json={
        "expected_revision": detail["revision"],
    })
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "invalid_configuration" and body["detail"] == body["message"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


def _assign_zones(api, operation, detail, **changes):
    payload = {"expected_revision": detail["revision"]}
    if operation == "clear":
        return api.client.delete(f"{BASE}/{detail['id']}/zones?expected_revision={changes.get('expected_revision', payload['expected_revision'])}")
    if operation == "randomize":
        return api.client.post(f"{BASE}/{detail['id']}/zones/randomize", json=payload | changes)
    payload |= {
        "zone_count": detail["zone_count"],
        "zone_a_registration_ids": [r["id"] for r in detail["registrations"]],
    }
    return api.client.put(f"{BASE}/{detail['id']}/zones", json=payload | changes)


@pytest.mark.parametrize("size", [0, 1, 3])
def test_manual_zones_single_requires_all_but_not_sufficient_capacity(americano_api, size):
    api = americano_api
    detail = create_event(api, zone_count=2)
    a = detail["zones"][0]
    for _ in range(size):
        detail = add_registration(api, detail)
    response = _assign_zones(api, "zones", detail, zone_count=1)
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["zones"] == [a] and updated["zone_count"] == 1
    assert updated["registrations"] == [r | {"zone_id": a["id"]} for r in detail["registrations"]]
    assert updated["can_generate"] is (size >= 2)
    assert updated["revision"] == detail["revision"] + 1
    assert api.client.get(f"{BASE}/{detail['id']}").json() == updated


def test_manual_zones_change_count_preserves_a_identity_and_accepts_identical_put(americano_api):
    api = americano_api
    detail = add_registration(api, add_registration(api, add_registration(api, create_event(api))))
    a = detail["zones"][0]
    ids = [r["id"] for r in detail["registrations"]]
    response = _assign_zones(api, "zones", detail, zone_count=2, zone_a_registration_ids=ids[:1])
    assert response.status_code == 200
    two = response.json()
    assert two["zones"][0] == a and two["zones"][1]["label"] == "B"
    assert [q["registered"] for q in two["quotas"]] == [1, 2] and two["can_generate"] is True
    assert two["revision"] == detail["revision"] + 1
    response = _assign_zones(api, "zones", two, zone_a_registration_ids=ids[:1])
    assert response.status_code == 200
    repeated = response.json()
    assert repeated == two | {"revision": two["revision"] + 1}
    response = _assign_zones(api, "zones", repeated, zone_count=1, zone_a_registration_ids=ids[::-1])
    assert response.status_code == 200
    one = response.json()
    assert one["zones"] == [a] and one["zone_count"] == 1
    assert one["registrations"] == detail["registrations"]
    assert one["revision"] == repeated["revision"] + 1 and one["groups_revision"] == 0
    assert api.client.get(f"{BASE}/{detail['id']}").json() == one


@pytest.mark.parametrize("select_all", [False, True])
def test_manual_zones_allow_empty_or_full_a_in_two_zone_draft(americano_api, select_all):
    api = americano_api
    detail = add_registration(api, add_registration(api, create_event(api, zone_count=2)))
    selected = [r["id"] for r in detail["registrations"]] if select_all else []
    response = _assign_zones(api, "zones", detail, zone_a_registration_ids=selected)
    assert response.status_code == 200
    updated = response.json()
    expected_zone = updated["zones"][0 if select_all else 1]["id"]
    assert [r["zone_id"] for r in updated["registrations"]] == [expected_zone] * 2
    assert updated["can_generate"] is False
    assert [issue["code"] for issue in updated["configuration_issues"]] == ["insufficient_registrations"]
    assert updated["revision"] == detail["revision"] + 1


@pytest.mark.parametrize("zone_count,stage,required", [
    (1, "quarterfinal", 8), (2, "quarterfinal", 4),
    (1, "semifinal", 4), (2, "semifinal", 2),
    (1, "final", 2), (2, "final", 1),
])
@pytest.mark.parametrize("shortage", [0, 1])
def test_manual_zones_report_exact_stage_quotas_without_rejecting_incomplete_drafts(
    americano_api, zone_count, stage, required, shortage,
):
    api = americano_api
    detail = create_event(api, zone_count=zone_count, start_stage=stage)
    a_count = required - shortage
    for _ in range(required * zone_count - shortage):
        detail = add_registration(api, detail)
    selected = [r["id"] for r in detail["registrations"][:a_count]]
    response = _assign_zones(api, "zones", detail, zone_a_registration_ids=selected)
    assert response.status_code == 200
    updated = response.json()
    assert updated["quotas"] == [
        {"zone_id": z["id"], "required": required, "registered": a_count if index == 0 else required,
         "sufficient": not shortage if index == 0 else True}
        for index, z in enumerate(updated["zones"])
    ]
    assert updated["can_generate"] is (not shortage)
    issues = updated["configuration_issues"]
    assert len(issues) == shortage
    if shortage:
        assert issues[0]["code"] == "insufficient_registrations"
        assert issues[0]["zone_id"] == updated["zones"][0]["id"] and issues[0]["registration_ids"] == []
    assert updated["total_rounds"] == 0 and updated["continuation"] == {"kind": "setup"}


def test_manual_zones_total_capacity_does_not_mask_one_undersized_zone(americano_api):
    api = americano_api
    detail = create_event(api, zone_count=2, start_stage="quarterfinal")
    for _ in range(8):
        detail = add_registration(api, detail)
    response = _assign_zones(api, "zones", detail, zone_a_registration_ids=[
        r["id"] for r in detail["registrations"][:3]
    ])
    assert response.status_code == 200
    updated = response.json()
    assert [q["registered"] for q in updated["quotas"]] == [3, 5]
    assert [q["sufficient"] for q in updated["quotas"]] == [False, True]
    assert updated["can_generate"] is False
    assert len(updated["configuration_issues"]) == 1
    assert updated["configuration_issues"][0]["zone_id"] == updated["zones"][0]["id"]


@pytest.mark.parametrize("size", [0, 1, 2, 6, 14, 17])
def test_random_zones_balance_empty_even_odd_and_singleton_inputs(americano_api, monkeypatch, size):
    from app.americanos import service

    api = americano_api
    detail = create_event(api, zone_count=2)
    for _ in range(size):
        detail = add_registration(api, detail)
    shuffled = []

    def reverse(registrations):
        shuffled.append(len(registrations))
        registrations.reverse()

    monkeypatch.setattr(service, "shuffle", reverse)
    response = _assign_zones(api, "randomize", detail)
    assert response.status_code == 200
    updated = response.json()
    assert [r["id"] for r in updated["registrations"]] == [r["id"] for r in detail["registrations"]]
    assert updated["registrations"] == [
        r | {"zone_id": updated["zones"][0 if index >= size // 2 else 1]["id"]}
        for index, r in enumerate(detail["registrations"])
    ]
    assert sorted(q["registered"] for q in updated["quotas"]) == [size // 2, (size + 1) // 2]
    assert updated["can_generate"] is (size >= 2)
    assert updated["revision"] == detail["revision"] + 1 and updated["groups_revision"] == 0
    assert api.client.get(f"{BASE}/{detail['id']}").json() == updated
    assert api.client.get(BASE).json()[0]["revision"] == updated["revision"]
    assert shuffled == [size]


@pytest.mark.parametrize("operation", ["zones", "randomize", "clear"])
@pytest.mark.parametrize("state", ["groups", "review", "playoffs", "completed"])
def test_zone_mutations_are_frozen_in_every_non_draft_state(americano_api, operation, state):
    api = americano_api
    detail = add_registration(api, create_event(api, zone_count=2))
    with Session(api.engine) as session:
        stored = session.get(AmericanoEvent, detail["id"])
        stored.state = AmericanoEventState(state)
        session.add(stored)
        if state == "groups":
            session.add(AmericanoRound(event_id=stored.id, number=1))
        session.commit()
    before = api.client.get(f"{BASE}/{detail['id']}").json()
    response = _assign_zones(api, operation, detail)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "state_conflict" and body["current_revision"] == detail["revision"]
    assert body["detail"] == body["message"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == before


@pytest.mark.parametrize("operation", ["zones", "randomize", "clear"])
@pytest.mark.parametrize("revision_offset", [-1, 1])
def test_zone_mutations_reject_stale_or_future_revisions(americano_api, operation, revision_offset):
    api = americano_api
    detail = add_registration(api, create_event(api, zone_count=2))
    response = _assign_zones(api, operation, detail, expected_revision=detail["revision"] + revision_offset)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "revision_conflict" and body["current_revision"] == detail["revision"]
    assert body["fields"][0]["path"] == ["expected_revision"] and body["detail"] == body["message"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


@pytest.mark.parametrize("operation", ["zones", "randomize", "clear"])
def test_zone_mutations_of_missing_event_are_flat_404(americano_api, operation):
    response = _assign_zones(americano_api, operation, {"id": 99999, "revision": 1,
                                                        "zone_count": 2, "registrations": []})
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found" and body["detail"] == body["message"]
    assert "current_revision" not in body


@pytest.mark.parametrize("payload", [
    {"zone_a_registration_ids": [1, 1]}, {"zone_a_registration_ids": [True]},
    {"zone_a_registration_ids": [1.0]}, {"zone_a_registration_ids": ["1"]},
    {"zone_a_registration_ids": [0]}, {"zone_a_registration_ids": [9007199254740992]},
    {"zone_count": True}, {"zone_count": 1.0}, {"zone_count": 3},
    {"zone_a_registration_ids": None}, {"zone_id": 1},
])
def test_manual_zones_validate_closed_strict_unique_payload_without_writes(americano_api, payload):
    api = americano_api
    detail = add_registration(api, create_event(api))
    response = _assign_zones(api, "zones", detail, **payload)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error" and body["detail"] == body["message"]
    assert body["fields"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


@pytest.mark.parametrize("operation", ["zones", "randomize"])
@pytest.mark.parametrize("payload", [
    {"expected_revision": True}, {"expected_revision": "2"}, {"expected_revision": 2.0},
    {"expected_revision": 0}, {"expected_revision": None}, {"extra": "ignored?"},
])
def test_zone_mutations_require_closed_strict_revision_payload(americano_api, operation, payload):
    api = americano_api
    detail = add_registration(api, create_event(api, zone_count=2))
    response = _assign_zones(api, operation, detail, **payload)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error" and body["fields"]
    assert body["detail"] == body["message"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


def test_generate_fixture_persists_one_pending_match_and_returns_first_round(americano_api):
    api = americano_api
    detail = add_registration(api, add_registration(api, create_event(api)))
    response = api.client.post(f"{BASE}/{detail['id']}/fixture", json={
        "expected_revision": detail["revision"],
    })
    assert response.status_code == 200, response.text
    generated = response.json()
    GenerateFixtureResponse.model_validate(generated)
    event, first = generated["event"], generated["first_round"]
    assert event == detail | {
        "state": "groups", "revision": detail["revision"] + 1,
        "total_rounds": 1, "max_unlocked_round": 1, "can_generate": False,
        "continuation": {"kind": "round", "round_number": 1},
    }
    assert first["event_id"] == detail["id"] and first["event_name"] == detail["name"]
    assert first["revision"] == event["revision"] and first["groups_revision"] == 0
    assert (first["number"], first["total_rounds"], first["max_unlocked_round"]) == (1, 1, 1)
    assert first["state"] == "groups"
    assert not first["saved"] and not first["locked"] and not first["read_only"]
    assert first["zones"] == event["zones"] and first["resting"] == []
    assert len(first["matches"]) == 1
    match = first["matches"][0]
    assert match["registration_a"] == detail["registrations"][0]
    assert match["registration_b"] == detail["registrations"][1]
    assert match["zone_id"] == detail["zones"][0]["id"] and match["display_order"] == 1
    assert match["games_a"] is None and match["games_b"] is None
    with Session(api.engine) as session:
        rounds = session.exec(select(AmericanoRound).where(AmericanoRound.event_id == detail["id"])).all()
        matches = session.exec(select(AmericanoGroupMatch).where(
            AmericanoGroupMatch.event_id == detail["id"],
        )).all()
        assert len(rounds) == len(matches) == 1
        assert rounds[0].number == 1 and rounds[0].saved_at is None
        assert matches[0].id == match["id"] and matches[0].round_id == rounds[0].id
        assert matches[0].games_a is None and matches[0].games_b is None
    assert api.client.get(f"{BASE}/{detail['id']}").json() == event
    assert api.client.get(BASE).json() == [{key: event[key] for key in detail if key not in {
        "zones", "registrations", "quotas", "can_generate", "configuration_issues",
        "confirmed_at", "champion_registration_id",
    }}]


def _fixture_draft(api, sizes, stage="final"):
    detail = create_event(api, zone_count=len(sizes), start_stage=stage)
    for index in range(sum(sizes)):
        detail = add_registration(api, detail, first=f"Jugador {index}", second=f"Compañero {index}")
    response = _assign_zones(api, "zones", detail, zone_a_registration_ids=[
        r["id"] for r in detail["registrations"][:sizes[0]]
    ])
    assert response.status_code == 200, response.text
    return response.json()


def _generate_fixture(api, detail, **changes):
    return api.client.post(f"{BASE}/{detail['id']}/fixture", json={
        "expected_revision": detail["revision"], **changes,
    })


def test_generate_fixture_two_singletons_enters_review_without_empty_rounds(americano_api):
    api = americano_api
    detail = _fixture_draft(api, (1, 1))
    response = _generate_fixture(api, detail)
    assert response.status_code == 200, response.text
    actual = response.json()
    GenerateFixtureResponse.model_validate(actual)
    assert actual["first_round"] is None
    assert actual["event"] == detail | {
        "state": "review", "revision": detail["revision"] + 1, "can_generate": False,
        "continuation": {"kind": "qualification"},
    }
    assert actual["event"]["total_rounds"] == actual["event"]["max_unlocked_round"] == 0
    assert actual["event"]["confirmed_at"] is None and actual["event"]["champion_registration_id"] is None
    with Session(api.engine) as session:
        assert session.exec(select(AmericanoRound)).all() == []
        assert session.exec(select(AmericanoGroupMatch)).all() == []
    assert api.client.get(f"{BASE}/{detail['id']}").json() == actual["event"]


@pytest.mark.parametrize("sizes,stage", [
    ((7,), "quarterfinal"), ((3, 5), "quarterfinal"),
    ((3,), "semifinal"), ((1, 3), "semifinal"),
    ((1,), "final"), ((0, 2), "final"), ((0,), "final"),
])
def test_generate_fixture_rejects_insufficient_per_zone_quotas_without_writes(americano_api, sizes, stage):
    api = americano_api
    detail = _fixture_draft(api, sizes, stage)
    assert detail["can_generate"] is False
    response = _generate_fixture(api, detail)
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "invalid_configuration" and body["detail"] == body["message"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail
    with Session(api.engine) as session:
        assert session.exec(select(AmericanoRound)).all() == []
        assert session.exec(select(AmericanoGroupMatch)).all() == []


@pytest.mark.parametrize("membership", ["unassigned", "foreign", "missing"])
def test_generate_fixture_checks_actual_zone_membership_not_only_quota_totals(americano_api, membership):
    api = americano_api
    detail = _fixture_draft(api, (2, 2))
    other = _fixture_draft(api, (2,))
    zone_id = {"unassigned": None, "foreign": other["zones"][0]["id"], "missing": 99999}[membership]
    # Simulate an invalid legacy row only in the fixture's private in-memory DB.
    # Valid production FKs already prohibit the foreign/missing cases.
    with api.engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.execute(AmericanoRegistration.__table__.update().where(
            AmericanoRegistration.id == detail["registrations"][0]["id"],
        ).values(zone_id=zone_id))
        connection.commit()
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()
    before = api.client.get(f"{BASE}/{detail['id']}").json()
    response = _generate_fixture(api, before)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "invalid_configuration"
    assert api.client.get(f"{BASE}/{detail['id']}").json() == before
    assert api.client.get(f"{BASE}/{other['id']}").json() == other
    with Session(api.engine) as session:
        assert session.exec(select(AmericanoRound)).all() == []
        assert session.exec(select(AmericanoGroupMatch)).all() == []


def test_generate_fixture_rejects_zone_count_inconsistent_with_stored_zones(americano_api):
    api = americano_api
    detail = _fixture_draft(api, (2,))
    with Session(api.engine) as session:
        event = session.get(AmericanoEvent, detail["id"])
        event.zone_count = 2
        session.add(event)
        session.commit()
    response = _generate_fixture(api, detail)
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_configuration"
    with Session(api.engine) as session:
        assert session.get(AmericanoEvent, detail["id"]).revision == detail["revision"]
        assert session.exec(select(AmericanoRound)).all() == []


@pytest.mark.parametrize("sizes,stage,match_count,round_sizes,rest_reasons", [
    ((8,), "quarterfinal", 28, [4] * 7, []),
    ((7, 7), "quarterfinal", 42, [6] * 7, ["bye", "bye"]),
    ((16,), "quarterfinal", 120, [6, 2] * 15, ["capacity"] * 4),
    ((8, 8), "quarterfinal", 56, [6, 2] * 7, ["capacity"] * 4),
    ((5, 4), "semifinal", 16, [4, 4, 4, 2, 2], ["bye"]),
    ((4,), "semifinal", 6, [2] * 3, []),
    ((4, 4), "quarterfinal", 12, [4] * 3, []),
    ((1, 3), "final", 3, [1] * 3, ["zone_finished", "bye"]),
    ((3, 1), "final", 3, [1] * 3, ["bye", "zone_finished"]),
])
def test_generate_fixture_persists_complete_intrazone_berger_schedule(
    americano_api, sizes, stage, match_count, round_sizes, rest_reasons,
):
    from app.americanos.fixture import ZoneInput, build_fixture

    api = americano_api
    detail = _fixture_draft(api, sizes, stage)
    response = _generate_fixture(api, detail)
    assert response.status_code == 200, response.text
    actual = response.json()
    GenerateFixtureResponse.model_validate(actual)
    event, first = actual["event"], actual["first_round"]
    assert event["registrations"] == detail["registrations"] and event["zones"] == detail["zones"]
    assert (event["state"], event["revision"], event["groups_revision"]) == ("groups", detail["revision"] + 1, 0)
    assert (event["total_rounds"], event["saved_rounds"], event["max_unlocked_round"]) == (len(round_sizes), 0, 1)
    assert event["continuation"] == {"kind": "round", "round_number": 1}
    assert first["total_rounds"] == len(round_sizes) and first["number"] == 1
    assert [rest["reason"] for rest in first["resting"]] == rest_reasons
    playing = {r[side]["id"] for r in first["matches"] for side in ("registration_a", "registration_b")}
    resting = [rest["registration"]["id"] for rest in first["resting"]]
    assert set(resting) == {r["id"] for r in detail["registrations"]} - playing
    assert len(resting) == len(set(resting)) and len(playing) == 2 * len(first["matches"])
    by_id = {r["id"]: r for r in detail["registrations"]}
    expected_pairs = {
        (zone["id"], a, b) for zone in detail["zones"]
        for a, b in combinations(sorted(r["id"] for r in detail["registrations"] if r["zone_id"] == zone["id"]), 2)
    }
    # The pure algorithm is the adapter's oracle, not a reimplementation of Berger.
    expected_fixture = build_fixture([
        ZoneInput(zone["id"], zone["label"], tuple(
            r["id"] for r in detail["registrations"] if r["zone_id"] == zone["id"]
        )) for zone in detail["zones"]
    ])
    assert [(rest["registration"]["id"], rest["reason"]) for rest in first["resting"]] == [
        (rest.registration_id, rest.reason) for rest in expected_fixture[0].resting
    ]
    with Session(api.engine) as session:
        rounds = session.exec(select(AmericanoRound).where(
            AmericanoRound.event_id == detail["id"],
        ).order_by(AmericanoRound.number)).all()
        matches = session.exec(select(AmericanoGroupMatch).where(
            AmericanoGroupMatch.event_id == detail["id"],
        )).all()
        assert [r.number for r in rounds] == list(range(1, len(round_sizes) + 1))
        assert all(r.saved_at is None for r in rounds)
        assert len(matches) == match_count == len(expected_pairs)
        assert {(m.zone_id, m.registration_a_id, m.registration_b_id) for m in matches} == expected_pairs
        for round_, expected_size, planned in zip(rounds, round_sizes, expected_fixture, strict=True):
            round_matches = sorted((m for m in matches if m.round_id == round_.id), key=lambda m: m.display_order)
            assert round_.number == planned.number
            assert [(m.zone_id, m.registration_a_id, m.registration_b_id, m.display_order) for m in round_matches] == [
                (m.zone_id, m.registration_a_id, m.registration_b_id, m.display_order) for m in planned.matches
            ]
            assert len(round_matches) == expected_size <= 6
            assert [m.display_order for m in round_matches] == list(range(1, expected_size + 1))
            assert len({i for m in round_matches for i in (m.registration_a_id, m.registration_b_id)}) == 2 * expected_size
            assert all(m.registration_a_id < m.registration_b_id and m.games_a is None and m.games_b is None
                       and by_id[m.registration_a_id]["zone_id"] == m.zone_id == by_id[m.registration_b_id]["zone_id"]
                       for m in round_matches)
            if round_.number == 1:
                assert [(m["id"], m["display_order"]) for m in first["matches"]] == [
                    (m.id, m.display_order) for m in round_matches
                ]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == event


@pytest.mark.parametrize("assignment", ["manual", "random"])
def test_generate_fixture_preserves_saved_distribution_without_any_shuffle(americano_api, monkeypatch, assignment):
    from app.americanos import service

    api = americano_api
    detail = _fixture_draft(api, (5, 4), "semifinal")
    if assignment == "random":
        response = _assign_zones(api, "randomize", detail)
        assert response.status_code == 200
        detail = response.json()

    def forbidden_shuffle(_registrations):
        raise AssertionError("Generation must not redistribute registrations")

    monkeypatch.setattr(service, "shuffle", forbidden_shuffle)
    response = _generate_fixture(api, detail)
    assert response.status_code == 200
    assert response.json()["event"]["registrations"] == detail["registrations"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == response.json()["event"]


@pytest.mark.parametrize("sizes", [(2,), (1, 1)])
@pytest.mark.parametrize("operation", ["update", "add", "rename", "delete", "zones", "randomize"])
def test_generate_fixture_freezes_all_existing_configuration_mutations(americano_api, sizes, operation):
    api = americano_api
    detail = _fixture_draft(api, sizes)
    response = _generate_fixture(api, detail)
    assert response.status_code == 200
    event = response.json()["event"]
    response = _mutate(api, operation, event)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "state_conflict" and body["current_revision"] == event["revision"]
    assert body["detail"] == body["message"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == event


@pytest.mark.parametrize("sizes", [(2,), (1, 1)])
def test_generate_fixture_retries_cannot_regenerate_or_advance_revision(americano_api, sizes):
    api = americano_api
    detail = _fixture_draft(api, sizes)
    response = _generate_fixture(api, detail)
    assert response.status_code == 200
    event = response.json()["event"]
    with Session(api.engine) as session:
        before = [m.model_dump() for m in session.exec(select(AmericanoGroupMatch)).all()]
    for revision, code in [(detail["revision"], "revision_conflict"), (event["revision"], "state_conflict")]:
        response = _generate_fixture(api, event, expected_revision=revision)
        assert response.status_code == 409 and response.json()["code"] == code
        assert response.json()["current_revision"] == event["revision"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == event
    with Session(api.engine) as session:
        assert [m.model_dump() for m in session.exec(select(AmericanoGroupMatch)).all()] == before


@pytest.mark.parametrize("revision_offset", [-1, 1])
def test_generate_fixture_rejects_stale_and_future_revisions_before_fixture_work(americano_api, monkeypatch, revision_offset):
    from app.americanos import service

    api = americano_api
    detail = _fixture_draft(api, (2,))

    def forbidden_build(_zones):
        raise AssertionError("A rejected request must not generate")

    monkeypatch.setattr(service, "build_fixture", forbidden_build)
    response = _generate_fixture(api, detail, expected_revision=detail["revision"] + revision_offset)
    assert response.status_code == 409 and response.json()["code"] == "revision_conflict"
    assert response.json()["fields"][0]["path"] == ["expected_revision"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


@pytest.mark.parametrize("payload", [{}, {"expected_revision": True}, {"expected_revision": "1"},
                                   {"expected_revision": 1.0}, {"expected_revision": 0},
                                   {"expected_revision": None}, {"expected_revision": 1, "zone_count": 2}])
def test_generate_fixture_requires_closed_strict_revision_input(americano_api, payload):
    api = americano_api
    detail = _fixture_draft(api, (2,))
    response = api.client.post(f"{BASE}/{detail['id']}/fixture", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error" and body["fields"]
    assert body["detail"] == body["message"]
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


def test_generate_fixture_missing_event_is_flat_404(americano_api):
    response = _generate_fixture(americano_api, {"id": 99999, "revision": 1})
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found" and body["detail"] == body["message"]
    assert "current_revision" not in body


@pytest.mark.parametrize("failure", ["round", "match", "commit"])
def test_generate_fixture_rolls_back_partial_rows_state_and_revision(americano_api, failure):
    api = americano_api
    detail = _fixture_draft(api, (4,))
    inserted = []

    def fail_insert(_connection, _cursor, statement, _parameters, _context, _many):
        target = "americano_rounds" if failure == "round" else "americano_group_matches"
        if statement.startswith(f"INSERT INTO {target}"):
            inserted.append(statement)
            if len(inserted) == 2:
                raise RuntimeError("injected generation insert failure")

    def fail_commit(session):
        if session.bind is api.engine:
            raise RuntimeError("injected generation commit failure")

    sql_event.listen(api.engine, "before_cursor_execute", fail_insert)
    if failure == "commit":
        sql_event.listen(Session, "before_commit", fail_commit)
        sql_event.remove(api.engine, "before_cursor_execute", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="injected generation"):
            _generate_fixture(api, detail)
    finally:
        if failure == "commit":
            sql_event.remove(Session, "before_commit", fail_commit)
        else:
            sql_event.remove(api.engine, "before_cursor_execute", fail_insert)
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail
    with Session(api.engine) as session:
        assert session.exec(select(AmericanoRound)).all() == []
        assert session.exec(select(AmericanoGroupMatch)).all() == []
    recovered = _generate_fixture(api, detail)
    assert recovered.status_code == 200
    assert recovered.json()["event"]["revision"] == detail["revision"] + 1
    with Session(api.engine) as session:
        assert len(session.exec(select(AmericanoRound)).all()) == 3
        assert len(session.exec(select(AmericanoGroupMatch)).all()) == 6


@pytest.mark.parametrize("sizes", [(2,), (1, 1)])
def test_generate_fixture_locks_event_first_and_commits_exactly_once(americano_api, sizes):
    from sqlalchemy.dialects import postgresql

    api = americano_api
    detail = _fixture_draft(api, sizes)
    statements, commits = [], []

    def executed(_connection, clause, _multiparams, _params, _options):
        statements.append(str(clause.compile(dialect=postgresql.dialect())))

    def committed(_connection):
        commits.append("commit")

    sql_event.listen(api.engine, "before_execute", executed)
    sql_event.listen(api.engine, "commit", committed)
    try:
        response = _generate_fixture(api, detail)
    finally:
        sql_event.remove(api.engine, "before_execute", executed)
        sql_event.remove(api.engine, "commit", committed)
    assert response.status_code == 200
    assert "FROM admin_users" in statements[0]
    assert "FROM americano_events" in statements[1] and "FOR UPDATE" in statements[1]
    assert commits == ["commit"]
    assert response.json()["event"]["revision"] == detail["revision"] + 1
    assert response.json()["event"]["groups_revision"] == 0


@pytest.mark.parametrize("sizes", [(2,), (1, 1)])
@pytest.mark.parametrize("use_current_revision", [False, True])
def test_generate_fixture_second_session_refreshes_cached_draft_before_rejecting_retry(
    americano_api, sizes, use_current_revision,
):
    from app.americanos import service
    from app.americanos.schemas import RevisionRequest

    api = americano_api
    detail = _fixture_draft(api, sizes)
    # Ordered transactions, NOT simultaneous writers or evidence of SQLite row locks.
    with Session(api.engine, expire_on_commit=False) as observer:
        cached = observer.get(AmericanoEvent, detail["id"])
        observer.commit()  # release the read transaction but retain its stale identity
        with Session(api.engine) as writer:
            generated = service.generate_fixture(writer, detail["id"], RevisionRequest(
                expected_revision=detail["revision"],
            ))
        assert cached.state == AmericanoEventState.DRAFT and cached.revision == detail["revision"]
        revision = generated.event.revision if use_current_revision else detail["revision"]
        with pytest.raises(service.AmericanoError) as error:
            service.generate_fixture(observer, detail["id"], RevisionRequest(expected_revision=revision))
        assert error.value.status == 409
        assert error.value.body.code == ("state_conflict" if use_current_revision else "revision_conflict")
        assert error.value.body.current_revision == generated.event.revision
    assert api.client.get(f"{BASE}/{detail['id']}").json() == generated.event.model_dump()
    with Session(api.engine) as session:
        assert len(session.exec(select(AmericanoRound)).all()) == (1 if sizes == (2,) else 0)
        assert len(session.exec(select(AmericanoGroupMatch)).all()) == (1 if sizes == (2,) else 0)


@pytest.mark.parametrize("changes", [{"name": "No cambiar"}, {"zone_count": 2}, {"start_stage": "quarterfinal"}])
@pytest.mark.parametrize("sizes", [(2,), (1, 1)])
def test_generate_fixture_freezes_each_event_configuration_field(americano_api, sizes, changes):
    api = americano_api
    detail = _fixture_draft(api, sizes)
    response = _generate_fixture(api, detail)
    assert response.status_code == 200
    generated = response.json()["event"]
    response = api.client.patch(f"{BASE}/{detail['id']}", json={"expected_revision": generated["revision"], **changes})
    assert response.status_code == 409 and response.json()["code"] == "state_conflict"
    assert api.client.get(f"{BASE}/{detail['id']}").json() == generated
