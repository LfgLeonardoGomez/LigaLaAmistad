"""Qualification HTTP contract using a private SQLite engine, without conftest."""

import pytest
from sqlalchemy import event as sql_event
from sqlmodel import Session, select

from app.americanos.models import (
    AmericanoEvent, AmericanoEventState, AmericanoQualifierSnapshot, AmericanoTieResolution,
)
from app.americanos.schemas import QualificationResponse

from .americano_fixtures import BASE, add_registration, americano_api, create_event  # noqa: F401


def _preview(api, event):
    response = api.client.get(f"{BASE}/{event['id']}/qualification")
    assert response.status_code == 200, response.text
    QualificationResponse.model_validate(response.json())
    return response.json()


def _generated(api, sizes=(3,), stage="final"):
    detail = create_event(api, zone_count=len(sizes), start_stage=stage)
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
    return response.json()["event"]


def _finish(api, event, tiers=None):
    tiers = tiers or [0] * len(event["registrations"])
    ranks = {registration["id"]: tier for registration, tier in zip(event["registrations"], tiers, strict=True)}
    for number in range(1, event["total_rounds"] + 1):
        round_ = api.client.get(f"{BASE}/{event['id']}/rounds/{number}").json()
        results = []
        for match in round_["matches"]:
            a, b = ranks[match["registration_a"]["id"]], ranks[match["registration_b"]["id"]]
            results.append({"match_id": match["id"], "games_a": int(a > b), "games_b": int(b > a)})
        response = api.client.put(f"{BASE}/{event['id']}/rounds/{number}/results", json={
            "expected_revision": round_["revision"], "results": results,
        })
        assert response.status_code == 200, response.text
    return api.client.get(f"{BASE}/{event['id']}").json()


def _selections(preview, *, reverse=False):
    selected = set()
    resolutions = []
    for slot in preview["slots"]:
        if not slot["requires_resolution"]:
            continue
        candidates = slot["candidate_registration_ids"][::(-1 if reverse else 1)]
        registration_id = next(candidate for candidate in candidates if candidate not in selected)
        selected.add(registration_id)
        resolutions.append({"zone_id": slot["zone_id"], "position": slot["position"], "registration_id": registration_id})
    return resolutions


def _put(api, preview, resolutions=None, **overrides):
    payload = {
        "expected_revision": preview["revision"], "source_groups_revision": preview["source_groups_revision"],
        "resolutions": _selections(preview) if resolutions is None else resolutions,
        **overrides,
    }
    return api.client.put(f"{BASE}/{preview['event_id']}/tie-resolutions", json=payload)


def _stored(api, event_id):
    with Session(api.engine) as session:
        return sorted((row.zone_id, row.position, row.registration_id, row.source_groups_revision)
                      for row in session.exec(select(AmericanoTieResolution).where(
                          AmericanoTieResolution.event_id == event_id,
                      )).all())


def test_preview_draft_empty_and_groups_are_read_only_with_blockers(americano_api):
    api = americano_api
    event = create_event(api)
    preview = _preview(api, event)
    assert {blocker["code"] for blocker in preview["blockers"]} == {"configuration_invalid", "groups_incomplete"}
    assert preview["slots"] == preview["resolved_seeds"] == preview["missing_slots"] == []
    assert preview["can_confirm"] is False and preview["frozen"] is False
    assert preview["seeding_template"]["status"] == "approved"
    assert len(preview["bracket"]) == 1
    assert api.client.get(f"{BASE}/{event['id']}").json() == event

    event = _generated(api)
    preview = _preview(api, event)
    assert {blocker["code"] for blocker in preview["blockers"]} == {"groups_incomplete", "unresolved_ties"}
    assert len(preview["slots"]) == 2 and len(preview["missing_slots"]) == 2
    assert api.client.get(f"{BASE}/{event['id']}").json() == event


@pytest.mark.parametrize("tiers,expected_candidates", [([1, 1, 0], 2), ([0, 0, 0], 3)])
def test_tied_seeding_and_cutoff_require_real_complete_human_selections(americano_api, tiers, expected_candidates):
    api = americano_api
    event = _finish(api, _generated(api), tiers)
    preview = _preview(api, event)
    assert preview["state"] == "review" and preview["source_groups_revision"] == event["groups_revision"]
    assert preview["can_confirm"] is False
    assert [blocker["code"] for blocker in preview["blockers"]] == ["unresolved_ties"]
    assert all(slot["registration_id"] is None and slot["requires_resolution"] for slot in preview["slots"])
    assert all(len(slot["candidate_registration_ids"]) == expected_candidates for slot in preview["slots"])
    assert preview["resolved_seeds"] == []
    response = _put(api, preview, _selections(preview, reverse=True))
    assert response.status_code == 200, response.text
    saved = response.json()
    QualificationResponse.model_validate(saved)
    assert saved["revision"] == preview["revision"] + 1
    assert saved["source_groups_revision"] == preview["source_groups_revision"]
    assert saved["can_confirm"] is True and saved["blockers"] == saved["missing_slots"] == []
    assert saved["state"] == "review" and saved["frozen"] is False
    assert all(slot["requires_resolution"] for slot in saved["slots"])
    assert [s["candidate_registration_ids"] for s in saved["slots"]] == [s["candidate_registration_ids"] for s in preview["slots"]]
    assert saved["resolved_seeds"] == _selections(preview, reverse=True)
    assert saved["bracket"][0]["registration_a_id"] == saved["resolved_seeds"][0]["registration_id"]
    assert _preview(api, event) == saved


def test_three_tied_for_last_two_places_do_not_require_nonqualifier_order(americano_api):
    api = americano_api
    event = _finish(api, _generated(api, (5,), "semifinal"), [2, 1, 0, 0, 0])
    preview = _preview(api, event)
    assert [slot["position"] for slot in preview["slots"] if slot["requires_resolution"]] == [3, 4]
    assert len(preview["missing_slots"]) == 2 and len(preview["resolved_seeds"]) == 2
    assert all(len(slot["candidate_registration_ids"]) == 3 for slot in preview["slots"][2:])
    response = _put(api, preview)
    assert response.status_code == 200, response.text
    assert response.json()["can_confirm"] is True
    assert len(response.json()["resolved_seeds"]) == 4


def test_irrelevant_tie_is_not_requested_and_empty_replacement_is_valid(americano_api):
    api = americano_api
    event = _finish(api, _generated(api, (5,)), [3, 2, 1, 0, 0])
    preview = _preview(api, event)
    assert preview["can_confirm"] is True and preview["missing_slots"] == []
    assert all(not slot["requires_resolution"] for slot in preview["slots"])
    response = _put(api, preview, [])
    assert response.status_code == 200, response.text
    assert response.json()["revision"] == preview["revision"] + 1
    assert _stored(api, event["id"]) == []


@pytest.mark.parametrize("invalid", ["missing", "foreign", "foreign_zone", "irrelevant", "firm", "duplicate_pair", "duplicate_slot", "huge_id"])
def test_invalid_resolution_replacement_is_atomic(americano_api, invalid):
    api = americano_api
    event = _finish(api, _generated(api, (5,), "semifinal"), [2, 1, 0, 0, 0])
    preview = _preview(api, event)
    saved_response = _put(api, preview)
    assert saved_response.status_code == 200, saved_response.text
    saved = saved_response.json()
    before = _stored(api, event["id"])
    resolutions = _selections(saved, reverse=True)
    if invalid == "missing":
        resolutions.pop()
    elif invalid == "foreign":
        foreign = add_registration(api, create_event(api))
        resolutions[0]["registration_id"] = foreign["registrations"][0]["id"]
    elif invalid == "foreign_zone":
        foreign = create_event(api)
        resolutions[0]["zone_id"] = foreign["zones"][0]["id"]
    elif invalid == "irrelevant":
        resolutions[0]["position"] = 5
    elif invalid == "firm":
        resolutions[0]["registration_id"] = event["registrations"][0]["id"]
    elif invalid == "duplicate_pair":
        resolutions[1]["registration_id"] = resolutions[0]["registration_id"]
    elif invalid == "duplicate_slot":
        resolutions[1]["position"] = resolutions[0]["position"]
    else:
        resolutions[0]["registration_id"] = 9_007_199_254_740_991
    response = _put(api, saved, resolutions)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == ("validation_error" if invalid.startswith("duplicate") else "invalid_tie_resolution")
    assert response.json()["detail"] == response.json()["message"]
    assert _stored(api, event["id"]) == before
    assert _preview(api, event) == saved


def test_full_replacement_can_swap_existing_unique_slots_and_identical_put_advances_only_revision(americano_api):
    api = americano_api
    event = _finish(api, _generated(api))
    preview = _preview(api, event)
    for reverse in [False, True, True]:
        response = _put(api, preview, _selections(preview, reverse=reverse))
        assert response.status_code == 200, response.text
        saved = response.json()
        assert saved["revision"] == preview["revision"] + 1
        assert saved["source_groups_revision"] == preview["source_groups_revision"]
        assert len(_stored(api, event["id"])) == 2
        preview = saved


@pytest.mark.parametrize("field,code", [("expected_revision", "revision_conflict"), ("source_groups_revision", "groups_revision_conflict")])
def test_stale_revisions_return_409_without_changing_resolutions(americano_api, field, code):
    api = americano_api
    event = _finish(api, _generated(api))
    preview = _put(api, _preview(api, event)).json()
    before = _stored(api, event["id"])
    response = _put(api, preview, **{field: preview["revision" if field == "expected_revision" else field] - 1})
    assert response.status_code == 409, response.text
    assert response.json()["code"] == code and response.json()["current_revision"] == preview["revision"]
    assert response.json()["fields"][0]["path"] == [field]
    assert _stored(api, event["id"]) == before and _preview(api, event) == preview


def test_identical_round_keeps_resolutions_effective_correction_invalidates_all_and_old_previews(americano_api):
    api = americano_api
    event = _finish(api, _generated(api, (3, 3)))
    preview = _put(api, _preview(api, event)).json()
    before = _stored(api, event["id"])
    round_ = api.client.get(f"{BASE}/{event['id']}/rounds/1").json()
    results = [{"match_id": match["id"], "games_a": match["games_a"], "games_b": match["games_b"]} for match in round_["matches"]]
    url = f"{BASE}/{event['id']}/rounds/1/results"
    response = api.client.put(url, json={"expected_revision": round_["revision"], "results": results})
    assert response.status_code == 200, response.text
    identical = _preview(api, event)
    assert identical["revision"] == preview["revision"] + 1
    assert identical["source_groups_revision"] == preview["source_groups_revision"]
    assert _stored(api, event["id"]) == before
    results[0]["games_a"] = 1
    response = api.client.put(url, json={"expected_revision": identical["revision"], "results": results})
    assert response.status_code == 200, response.text
    changed = _preview(api, event)
    assert changed["source_groups_revision"] == identical["source_groups_revision"] + 1
    assert _stored(api, event["id"]) == []
    assert changed["missing_slots"] and changed["can_confirm"] is False
    assert _put(api, identical).status_code == 409
    assert _put(api, changed, source_groups_revision=identical["source_groups_revision"]).json()["code"] == "groups_revision_conflict"


@pytest.mark.parametrize("state", ["draft", "groups", "playoffs", "completed"])
def test_resolution_writes_only_allowed_in_review(americano_api, state):
    api = americano_api
    event = _finish(api, _generated(api))
    preview = _preview(api, event)
    with Session(api.engine) as session:
        stored = session.get(AmericanoEvent, event["id"])
        stored.state = AmericanoEventState(state)
        session.add(stored)
        session.commit()
    response = _put(api, preview)
    assert response.status_code == 409 and response.json()["code"] == "state_conflict"
    assert response.json()["current_revision"] == preview["revision"]
    assert _stored(api, event["id"]) == []


@pytest.mark.parametrize("stage,sizes,pairs", [
    ("final", (2,), [(0, 1, 0, 2)]), ("final", (1, 1), [(0, 1, 1, 1)]),
    ("semifinal", (4,), [(0, 1, 0, 4), (0, 2, 0, 3)]),
    ("semifinal", (2, 2), [(0, 1, 1, 2), (1, 1, 0, 2)]),
    ("quarterfinal", (8,), [(0, 1, 0, 8), (0, 4, 0, 5), (0, 2, 0, 7), (0, 3, 0, 6)]),
    ("quarterfinal", (4, 4), [(0, 1, 1, 4), (1, 2, 0, 3), (1, 1, 0, 4), (0, 2, 1, 3)]),
])
def test_preview_uses_six_approved_templates_real_zone_ids_and_destinations(americano_api, stage, sizes, pairs):
    api = americano_api
    event = _generated(api, sizes, stage)
    preview = _preview(api, event)
    zones = event["zones"]
    template = preview["seeding_template"]
    assert template["key"] == f"{stage}-{'one-zone' if len(sizes) == 1 else 'two-zones'}-v1"
    assert template["opening_pairs"] == [{"a": {"zone_id": zones[a]["id"], "position": p}, "b": {"zone_id": zones[b]["id"], "position": q}} for a, p, b, q in pairs]
    assert template["status"] == "approved"
    assert len(preview["bracket"]) == len(pairs) * 2 - 1
    assert preview["bracket"][-1]["next"] is None
    assert preview["bracket"][-1]["stage"] == "final"
    if stage != "final":
        assert preview["bracket"][0]["next"] == {"stage": "semifinal" if stage == "quarterfinal" else "final", "slot": 1, "side": "a"}
        assert preview["bracket"][1]["next"]["side"] == "b"
    if sizes == (1, 1):
        assert event["state"] == "review" and preview["can_confirm"] is True
        assert len(preview["resolved_seeds"]) == 2


@pytest.mark.parametrize("state", ["playoffs", "completed"])
def test_closed_preview_uses_canonical_snapshots_not_manual_resolutions(americano_api, state):
    api = americano_api
    event = _finish(api, _generated(api))
    preview = _preview(api, event)
    resolutions = _selections(preview, reverse=True)
    with Session(api.engine) as session:
        stored = session.get(AmericanoEvent, event["id"])
        stored.state = AmericanoEventState(state)
        stored.confirmed_source_revision = event["groups_revision"]
        session.add(stored)
        for resolution in resolutions:
            registration = next(r for r in event["registrations"] if r["id"] == resolution["registration_id"])
            session.add(AmericanoQualifierSnapshot(
                event_id=event["id"], **resolution, player1_name=registration["player1_name"],
                player2_name=registration["player2_name"], points_half_units=2, games_diff=0,
                source_groups_revision=event["groups_revision"],
            ))
        session.commit()
    frozen = _preview(api, event)
    assert frozen["frozen"] is True and frozen["can_confirm"] is False
    assert frozen["resolved_seeds"] == resolutions and frozen["missing_slots"] == []
    assert frozen["blockers"] == [] and frozen["state"] == state


@pytest.mark.parametrize("mode", ["anonymous", "expired", "inactive"])
@pytest.mark.parametrize("method,path", [("get", "qualification"), ("put", "tie-resolutions")])
def test_qualification_routes_use_existing_admin_guard(americano_api, mode, method, path):
    api = americano_api
    api.authenticate(mode)
    response = getattr(api.client, method)(f"{BASE}/1/{path}", **({"json": {"expected_revision": 1, "source_groups_revision": 0, "resolutions": []}} if method == "put" else {}))
    assert response.status_code == 401 and response.json() == {"detail": "Not authenticated"}


@pytest.mark.parametrize("method,path", [("get", "qualification"), ("put", "tie-resolutions")])
@pytest.mark.parametrize("event_id", [9999, 2_147_483_648, 9_007_199_254_740_991])
def test_missing_and_out_of_db_integer_ids_are_404(americano_api, method, path, event_id):
    api = americano_api
    response = getattr(api.client, method)(f"{BASE}/{event_id}/{path}", **({"json": {"expected_revision": 1, "source_groups_revision": 0, "resolutions": []}} if method == "put" else {}))
    assert response.status_code == 404 and response.json()["code"] == "not_found"


def test_failure_during_replacement_rolls_back_old_resolutions_and_revision(americano_api):
    api = americano_api
    event = _finish(api, _generated(api))
    preview = _put(api, _preview(api, event)).json()
    before = _stored(api, event["id"])

    def fail_insert(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("INSERT INTO AMERICANO_TIE_RESOLUTIONS"):
            raise RuntimeError("injected resolution insert failure")

    sql_event.listen(api.engine, "before_cursor_execute", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="injected resolution insert failure"):
            _put(api, preview, _selections(preview, reverse=True))
    finally:
        sql_event.remove(api.engine, "before_cursor_execute", fail_insert)
    assert _stored(api, event["id"]) == before and _preview(api, event) == preview


@pytest.mark.parametrize("field,value", [
    ("expected_revision", True), ("expected_revision", "1"), ("expected_revision", 1.0),
    ("source_groups_revision", False), ("source_groups_revision", None),
    ("source_groups_revision", 1.0), ("source_groups_revision", -1),
    ("resolutions", None), ("extra", "forbidden"),
])
def test_strict_transport_rejects_invalid_payloads_without_mutation(americano_api, field, value):
    api = americano_api
    event = _finish(api, _generated(api))
    preview = _preview(api, event)
    response = api.client.put(f"{BASE}/{event['id']}/tie-resolutions", json={
        "expected_revision": preview["revision"], "source_groups_revision": preview["source_groups_revision"],
        "resolutions": _selections(preview), field: value,
    })
    assert response.status_code == 422 and response.json()["code"] == "validation_error"
    assert response.json()["fields"]
    assert _preview(api, event) == preview and _stored(api, event["id"]) == []


@pytest.mark.parametrize("field,value", [
    ("zone_id", True), ("registration_id", "1"), ("position", 1.0),
    ("registration_id", 0), ("position", None),
])
def test_strict_resolution_fields_reject_coercion(americano_api, field, value):
    api = americano_api
    event = _finish(api, _generated(api))
    preview = _preview(api, event)
    resolutions = _selections(preview)
    resolutions[0][field] = value
    response = _put(api, preview, resolutions)
    assert response.status_code == 422 and response.json()["code"] == "validation_error"
    assert _preview(api, event) == preview and _stored(api, event["id"]) == []


def test_preview_ignores_stale_stored_resolution_without_deleting_it_and_write_replaces_it(americano_api):
    api = americano_api
    event = _finish(api, _generated(api))
    preview = _preview(api, event)
    resolution = _selections(preview)[0]
    with Session(api.engine) as session:
        session.add(AmericanoTieResolution(
            event_id=event["id"], source_groups_revision=event["groups_revision"] - 1, **resolution,
        ))
        session.commit()
    assert _preview(api, event) == preview and len(_stored(api, event["id"])) == 1
    response = _put(api, preview)
    assert response.status_code == 200, response.text
    assert len(_stored(api, event["id"])) == 2
    assert all(row[-1] == event["groups_revision"] for row in _stored(api, event["id"]))


def test_two_events_keep_previews_scores_and_resolution_replacement_isolated(americano_api):
    api = americano_api
    first = _finish(api, _generated(api))
    second = _finish(api, _generated(api))
    first_preview = _put(api, _preview(api, first)).json()
    second_preview = _preview(api, second)
    first_ids = {registration["id"] for registration in first["registrations"]}
    assert all(not first_ids.intersection(slot["candidate_registration_ids"]) for slot in second_preview["slots"])
    response = _put(api, second_preview, _selections(second_preview, reverse=True))
    assert response.status_code == 200, response.text
    assert _preview(api, first) == first_preview
    assert len(_stored(api, first["id"])) == len(_stored(api, second["id"])) == 2
