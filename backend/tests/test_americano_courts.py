"""Court selection, scheduling and operational reassignment on private memory DBs."""

from itertools import combinations

import pytest

from app.americanos.fixture import AmericanoDomainError, ZoneInput, build_fixture

from .americano_fixtures import BASE, add_registration, americano_api  # noqa: F401
from .test_americano_confirmation import _confirm, _playoffs
from .test_americano_qualification_api import _preview, _put


@pytest.mark.parametrize("mask", range(1, 64))
def test_every_court_subset_limits_global_rounds_and_keeps_all_pairs(mask):
    courts = [court for court in range(1, 7) if mask & (1 << (court - 1))]
    zones = [ZoneInput(1, "A", tuple(range(1, 8))), ZoneInput(2, "B", tuple(range(8, 16)))]
    fixture = build_fixture(zones, courts=list(reversed(courts)))
    assert fixture == build_fixture(zones, courts=courts)
    actual = []
    for round_ in fixture:
        assert 1 <= len(round_.matches) <= len(courts)
        assert [match.court_number for match in round_.matches] == courts[:len(round_.matches)]
        playing = [id_ for match in round_.matches for id_ in (match.registration_a_id, match.registration_b_id)]
        assert len(playing) == len(set(playing))
        resting = [rest.registration_id for rest in round_.resting]
        assert len(resting) == len(set(resting))
        assert set(playing).isdisjoint(resting)
        assert set(playing) | set(resting) == set(range(1, 16))
        actual.extend((match.zone_id, match.registration_a_id, match.registration_b_id) for match in round_.matches)
    expected = {(zone.zone_id, a, b) for zone in zones for a, b in combinations(zone.registration_ids, 2)}
    assert len(actual) == len(expected) and set(actual) == expected


@pytest.mark.parametrize("courts", [[], [0], [7], [True], [1.0], ["1"], [3, 3], list(range(1, 8))])
def test_domain_rejects_invalid_courts(courts):
    with pytest.raises(AmericanoDomainError):
        build_fixture([ZoneInput(1, "A", (1, 2))], courts=courts)


def test_reduced_capacity_shares_courts_between_zones():
    zones = [ZoneInput(1, "A", (1, 2, 3, 4)), ZoneInput(2, "B", (5, 6, 7, 8))]
    fixture = build_fixture(zones, courts=[3, 6])
    assert len(fixture) == 6
    assert all([match.zone_id for match in round_.matches] == [1, 2] for round_ in fixture)
    assert all({rest.zone_id for rest in round_.resting} == {1, 2} for round_ in fixture)
    assert build_fixture(zones, courts=[1, 2, 3, 4, 5, 6]) == build_fixture(zones)


def _draft(api, courts=(3, 6), sizes=(4, 4), stage="semifinal"):
    response = api.client.post(BASE, json={
        "name": "Canchas reales", "zone_count": len(sizes), "start_stage": stage, "courts": list(courts),
    })
    assert response.status_code == 201, response.text
    detail = response.json()
    for index in range(sum(sizes)):
        detail = add_registration(api, detail, first=f"A{index}", second=f"B{index}")
    response = api.client.put(f"{BASE}/{detail['id']}/zones", json={
        "expected_revision": detail["revision"], "zone_count": len(sizes),
        "zone_a_registration_ids": [r["id"] for r in detail["registrations"][:sizes[0]]],
    })
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("courts", [[], [0], [7], [True], [1.0], ["1"], [3, 3], None])
def test_request_rejects_invalid_selection_atomically(americano_api, courts):
    api = americano_api
    response = api.client.post(BASE, json={"name": "Invalid", "zone_count": 1, "start_stage": "final", "courts": courts})
    assert response.status_code == 422
    assert api.client.get(BASE).json() == []
    detail = _draft(api, sizes=(2,), stage="final")
    response = api.client.patch(f"{BASE}/{detail['id']}", json={"expected_revision": detail["revision"], "courts": courts})
    assert response.status_code == 422
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


def test_real_courts_persist_split_rounds_keep_rests_and_survive_confirmation(americano_api):
    api = americano_api
    detail = _draft(api, courts=(6, 3))
    assert detail["courts"] == [3, 6]
    response = api.client.patch(f"{BASE}/{detail['id']}", json={"expected_revision": detail["revision"], "courts": [5]})
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["courts"] == [5]
    stale = api.client.patch(f"{BASE}/{detail['id']}", json={"expected_revision": detail["revision"], "courts": [1]})
    assert stale.status_code == 409
    response = api.client.post(f"{BASE}/{detail['id']}/fixture", json={"expected_revision": updated["revision"]})
    assert response.status_code == 200, response.text
    generated = response.json()["event"]
    assert generated["total_rounds"] == 12
    assert response.json()["first_round"]["matches"][0]["court_number"] == 5
    all_pairs = []
    for number in range(1, 13):
        round_ = api.client.get(f"{BASE}/{detail['id']}/rounds/{number}").json()
        assert len(round_["matches"]) == 1
        assert round_["matches"][0]["court_number"] == 5
        assert len(round_["resting"]) == 6
        all_pairs.extend((m["registration_a"]["id"], m["registration_b"]["id"]) for m in round_["matches"])
        response = api.client.put(f"{BASE}/{detail['id']}/rounds/{number}/results", json={
            "expected_revision": round_["revision"],
            "results": [{"match_id": m["id"], "games_a": 1, "games_b": 0} for m in round_["matches"]],
        })
        assert response.status_code == 200, response.text
    assert len(all_pairs) == len(set(all_pairs)) == 12
    canonical = api.client.get(f"{BASE}/{detail['id']}").json()
    frozen = api.client.patch(f"{BASE}/{detail['id']}", json={"expected_revision": canonical["revision"], "courts": [3]})
    assert frozen.status_code == 409
    preview = _preview(api, canonical)
    if preview["missing_slots"]:
        preview = _put(api, preview).json()
    confirmed = _confirm(api, preview)
    assert confirmed.status_code == 200, confirmed.text
    playoffs = confirmed.json()["playoffs"]
    assert playoffs["courts"] == [5]
    assert all(node["court_number"] == 5 for node in playoffs["nodes"])
    node = playoffs["nodes"][0]
    unavailable = api.client.put(f"{BASE}/{detail['id']}/playoffs/{node['id']}/court", json={
        "expected_revision": playoffs["revision"], "court_number": 3,
    })
    assert unavailable.status_code == 422
    assert _playoffs(api, detail["id"]) == playoffs
    # Same court is a suggestion for different turns, not simultaneous bookings.
    assert len([node for node in playoffs["nodes"] if node["stage"] == "semifinal"]) == 2


def test_knockout_reassignment_is_revisioned_scoped_and_does_not_touch_results(americano_api):
    from .test_americano_knockouts import _closed, _save

    api = americano_api
    bracket = _closed(api, sizes=(4,), stage="semifinal")
    pending = next(node for node in bracket["nodes"] if node["stage"] == "final")
    url = f"{BASE}/{bracket['event_id']}/playoffs/{pending['id']}/court"
    response = api.client.put(url, json={"expected_revision": bracket["revision"], "court_number": 6})
    assert response.status_code == 200, response.text
    changed = response.json()
    expected = {**bracket, "revision": bracket["revision"] + 1, "nodes": [
        {**node, "court_number": 6} if node["id"] == pending["id"] else node for node in bracket["nodes"]
    ]}
    assert changed == expected
    assert _playoffs(api, bracket["event_id"]) == changed
    assert api.client.put(url, json={"expected_revision": bracket["revision"], "court_number": 2}).status_code == 409
    assert api.client.put(url, json={"expected_revision": changed["revision"], "court_number": True}).status_code == 422
    other = _closed(api)
    foreign_url = f"{BASE}/{changed['event_id']}/playoffs/{other['nodes'][0]['id']}/court"
    assert api.client.put(foreign_url, json={"expected_revision": changed["revision"], "court_number": 2}).status_code == 404
    opening = next(node for node in changed["nodes"] if node["stage"] == "semifinal")
    scored_response = _save(api, changed, opening)
    assert scored_response.status_code == 200, scored_response.text
    scored = scored_response.json()
    played_url = f"{BASE}/{scored['event_id']}/playoffs/{opening['id']}/court"
    assert api.client.put(played_url, json={"expected_revision": scored["revision"], "court_number": 2}).status_code == 409
    assert _playoffs(api, scored["event_id"]) == scored


@pytest.mark.parametrize("mode", ["anonymous", "inactive", "expired"])
def test_court_assignment_is_private(americano_api, mode):
    americano_api.authenticate(mode)
    response = americano_api.client.put(f"{BASE}/1/playoffs/1/court", json={"expected_revision": 1, "court_number": 6})
    assert response.status_code == 401


def test_court_assignment_requires_csrf_protection(americano_api):
    americano_api.client.headers.pop("X-Requested-With")
    response = americano_api.client.put(f"{BASE}/1/playoffs/1/court", json={"expected_revision": 1, "court_number": 6})
    assert response.status_code == 403
