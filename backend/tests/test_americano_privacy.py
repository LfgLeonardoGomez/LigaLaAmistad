"""AE-01/02: exercise the real cookie guard against an isolated database."""

import pytest
from sqlalchemy import event as sql_event
from sqlmodel import SQLModel, Session, select

from app.americanos.models import AmericanoEvent

from .americano_fixtures import BASE, add_registration, americano_api, create_event  # noqa: F401


@pytest.mark.parametrize("mode", ["anonymous", "expired", "inactive"])
@pytest.mark.parametrize("method,path,payload", [
    ("GET", "", None),
    ("POST", "", {"name": "Privado", "zone_count": 1, "start_stage": "final"}),
    ("GET", "/123", None),
])
def test_collection_and_read_require_active_cookie(americano_api, mode, method, path, payload):
    api = americano_api
    api.authenticate(mode)
    response = api.client.request(method, BASE + path, json=payload)
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    with Session(api.engine) as session:
        assert session.exec(select(AmericanoEvent)).all() == []


@pytest.mark.parametrize("mode", ["anonymous", "expired", "inactive"])
def test_patch_requires_active_cookie_even_for_invalid_input(americano_api, mode):
    api = americano_api
    api.authenticate(mode)
    response = api.client.patch(f"{BASE}/999", json={"expected_revision": True, "name": "Privado"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.parametrize("mode", ["anonymous", "expired", "inactive"])
def test_add_registration_is_protected_without_revision_or_identity_leaks(americano_api, mode):
    api = americano_api
    detail = create_event(api)
    api.authenticate(mode)
    response = api.client.post(f"{BASE}/{detail['id']}/registrations", json={
        "expected_revision": 999, "player1_name": "Privado", "player2_name": "Oculto",
    })
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    api.authenticate()
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


@pytest.mark.parametrize("mode", ["anonymous", "expired", "inactive"])
@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_registration_edit_and_delete_use_real_admin_guard(americano_api, mode, method):
    api = americano_api
    detail = add_registration(api, create_event(api))
    api.authenticate(mode)
    path = f"{BASE}/{detail['id']}/registrations/{detail['registrations'][0]['id']}"
    response = api.client.request(method, path + "?expected_revision=999", json={
        "expected_revision": 999, "player1_name": "Oculto",
    })
    assert response.status_code == 401 and response.json() == {"detail": "Not authenticated"}
    api.authenticate()
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
@pytest.mark.parametrize("phase,revision", [("draft", 2), ("review", 999)])
def test_foreign_child_is_404_before_phase_or_revision_details(americano_api, method, phase, revision):
    api = americano_api
    first = add_registration(api, create_event(api))
    second = add_registration(api, create_event(api))
    with Session(api.engine) as session:
        stored = session.get(AmericanoEvent, first["id"])
        stored.state = phase
        session.add(stored)
        session.commit()
    for registration_id in [second["registrations"][0]["id"], 99999]:
        path = f"{BASE}/{first['id']}/registrations/{registration_id}"
        if method == "DELETE":
            response = api.client.delete(path + f"?expected_revision={revision}")
        else:
            response = api.client.patch(path, json={"expected_revision": revision, "player1_name": "No"})
        assert response.status_code == 404
        body = response.json()
        assert body["code"] == "not_found" and body["detail"] == body["message"]
        assert "current_revision" not in body
    assert api.client.get(f"{BASE}/{second['id']}").json() == second
    with Session(api.engine) as session:
        assert session.get(AmericanoEvent, first["id"]).revision == 2


@pytest.mark.parametrize("zone_count", [1, 2])
def test_draft_operations_leave_nonempty_league_and_public_responses_unchanged(americano_api, zone_count):
    from app.zones.models import Zone

    api = americano_api
    with Session(api.engine) as session:
        zone = Zone(name="Zona Liga")
        session.add(zone)
        session.commit()
        zone_id = zone.id
    teams = []
    for name in ["Liga Ana", "Liga Eva"]:
        response = api.client.post("/admin/teams", json={
            "zone_id": zone_id, "player_one_name": name, "player_two_name": "Liga Sol",
        })
        assert response.status_code == 201
        teams.append(response.json()["id"])
    response = api.client.post("/admin/matches", json={
        "team_a_id": teams[0], "team_b_id": teams[1], "date": "2026-10-21",
    })
    assert response.status_code == 201
    match_id = response.json()["id"]
    assert api.client.post(f"/admin/matches/{match_id}/result", json={"sets": [
        {"set_number": number, "team_a_games": 6, "team_b_games": 4} for number in [1, 2]
    ]}).status_code == 200
    paths = ["/public/zones", "/public/teams", "/public/matches",
             "/public/matches?status=pending", f"/public/standings?zone_id={zone_id}",
             f"/public/teams?zone_id={zone_id}", f"/public/matches?zone_id={zone_id}",
             f"/public/matches/votes?ids={match_id}"]

    def public_snapshot():
        api.authenticate("anonymous")
        responses = [api.client.get(path) for path in paths]
        assert all(response.status_code == 200 for response in responses)
        api.authenticate()
        return [response.json() for response in responses]

    tables = [table for table in SQLModel.metadata.sorted_tables if not table.name.startswith("americano_")]

    def league_rows():
        with api.engine.connect() as connection:
            return {table.name: connection.execute(select(table)).all() for table in tables}

    public_before, league_before = public_snapshot(), league_rows()
    assert len(public_before[1]) == 2 and len(public_before[2]) == 1
    statements = []

    def executed(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    sql_event.listen(api.engine, "before_cursor_execute", executed)
    try:
        detail = add_registration(api, create_event(api, name="Americano privado", zone_count=zone_count))
        assert api.client.get(BASE).status_code == 200
        assert api.client.get(f"{BASE}/{detail['id']}").status_code == 200
        response = api.client.patch(f"{BASE}/{detail['id']}", json={"expected_revision": 2, "name": "Privado editado"})
        assert response.status_code == 200
        registration_id = detail["registrations"][0]["id"]
        path = f"{BASE}/{detail['id']}/registrations/{registration_id}"
        assert api.client.patch(path, json={"expected_revision": 3, "player1_name": "Privada"}).status_code == 200
        assert api.client.delete(path + "?expected_revision=4").status_code == 200
        response = api.client.put(f"{BASE}/{detail['id']}/zones", json={
            "expected_revision": 5, "zone_count": 2, "zone_a_registration_ids": [],
        })
        assert response.status_code == 200
        response = api.client.post(f"{BASE}/{detail['id']}/zones/randomize", json={
            "expected_revision": 6,
        })
        assert response.status_code == 200
        draft = response.json()
        response = api.client.delete(f"{BASE}/{draft['id']}/zones?expected_revision={draft['revision']}")
        assert response.status_code == 200
        draft = response.json()
        response = api.client.post(f"{BASE}/{draft['id']}/registrations/bulk", json={
            "expected_revision": draft["revision"], "registrations": [
                {"player1_name": f"Pareja {index}", "player2_name": "Integridad"} for index in range(4)
            ],
        })
        assert response.status_code == 201
        draft = response.json()
        response = api.client.put(f"{BASE}/{draft['id']}/zones", json={
            "expected_revision": draft["revision"], "zone_count": 2,
            "zone_a_registration_ids": [r["id"] for r in draft["registrations"][:2]],
        })
        assert response.status_code == 200
        response = api.client.post(f"{BASE}/{draft['id']}/fixture", json={
            "expected_revision": response.json()["revision"],
        })
        assert response.status_code == 200 and response.json()["event"]["state"] == "groups"
        round_response = api.client.get(f"{BASE}/{draft['id']}/rounds/1")
        assert round_response.status_code == 200
        assert api.client.get(f"{BASE}/{draft['id']}/standings").status_code == 200
        round_ = round_response.json()
        response = api.client.put(f"{BASE}/{draft['id']}/rounds/1/results", json={
            "expected_revision": round_["revision"],
            "results": [{"match_id": match["id"], "games_a": 0, "games_b": 0} for match in round_["matches"]],
        })
        assert response.status_code == 200 and response.json()["round"]["state"] == "review"
        event_path = f"{BASE}/{draft['id']}"
        response = api.client.get(event_path + "/qualification")
        assert response.status_code == 200
        preview = response.json()
        assert preview["state"] == "review" and preview["missing_slots"]
        # Explicit choices from the real tied candidates, standing in for the
        # organizer's human draw; never manufacture identities or seed by name.
        selected = set()
        resolutions = []
        for slot in preview["slots"]:
            if not slot["requires_resolution"]:
                continue
            registration_id = next(candidate for candidate in reversed(slot["candidate_registration_ids"])
                                   if candidate not in selected)
            selected.add(registration_id)
            resolutions.append({"zone_id": slot["zone_id"], "position": slot["position"],
                                "registration_id": registration_id})
        response = api.client.put(event_path + "/tie-resolutions", json={
            "expected_revision": preview["revision"], "source_groups_revision": preview["source_groups_revision"],
            "resolutions": resolutions,
        })
        assert response.status_code == 200 and response.json()["can_confirm"] is True
        resolved = response.json()
        confirmation = {
            "expected_revision": resolved["revision"], "source_groups_revision": resolved["source_groups_revision"],
            "confirmation_key": "6c764a9e-ad96-4c73-a468-f89261f3fa08",
        }
        response = api.client.post(event_path + "/confirm-qualifiers", json=confirmation)
        assert response.status_code == 200 and response.json()["event"]["state"] == "playoffs"
        confirmed = response.json()["playoffs"]
        response = api.client.get(event_path + "/playoffs")
        assert response.status_code == 200 and response.json() == confirmed
        assert len(confirmed["nodes"]) == 1
        final = confirmed["nodes"][0]
        result_path = event_path + f"/playoffs/{final['id']}/result"
        response = api.client.put(result_path, json={
            "expected_revision": confirmed["revision"], "games_a": 6, "games_b": 0, "set_complete": True,
        })
        assert response.status_code == 200
        completed = response.json()
        assert completed["state"] == "completed" and completed["champion"]["id"] == final["registration_a"]["id"]
        response = api.client.put(result_path, json={
            "expected_revision": completed["revision"], "games_a": 0, "games_b": 6, "set_complete": True,
        })
        assert response.status_code == 200
        corrected = response.json()
        assert corrected["state"] == "completed" and corrected["champion"]["id"] == final["registration_b"]["id"]
        assert corrected["snapshots"] == confirmed["snapshots"]
        assert api.client.get(event_path + "/playoffs").json() == corrected
        for path in ["/qualification", "/standings"]:
            response = api.client.get(event_path + path)
            assert response.status_code == 200 and response.json()["frozen"] is True
        response = api.client.post(event_path + "/confirm-qualifiers", json=confirmation)
        assert response.status_code == 200 and response.json()["playoffs"] == corrected
    finally:
        sql_event.remove(api.engine, "before_cursor_execute", executed)
    assert statements and all("americano_" in sql or "admin_users" in sql for sql in statements)
    assert league_rows() == league_before
    assert public_snapshot() == public_before


def test_only_the_twenty_authorized_operations_are_published(americano_api):
    from app.main import app

    paths = app.openapi()["paths"]
    published = {(method.upper(), path) for path, methods in paths.items()
                 if path.startswith(BASE) for method in methods}
    assert published == {
        ("GET", BASE), ("POST", BASE),
        ("GET", BASE + "/{event_id}"), ("PATCH", BASE + "/{event_id}"),
        ("POST", BASE + "/{event_id}/registrations"),
        ("POST", BASE + "/{event_id}/registrations/bulk"),
        ("PATCH", BASE + "/{event_id}/registrations/{registration_id}"),
        ("DELETE", BASE + "/{event_id}/registrations/{registration_id}"),
        ("PUT", BASE + "/{event_id}/zones"),
        ("DELETE", BASE + "/{event_id}/zones"),
        ("POST", BASE + "/{event_id}/zones/randomize"),
        ("POST", BASE + "/{event_id}/fixture"),
        ("GET", BASE + "/{event_id}/rounds/{number}"),
        ("GET", BASE + "/{event_id}/standings"),
        ("PUT", BASE + "/{event_id}/rounds/{number}/results"),
        ("GET", BASE + "/{event_id}/qualification"),
        ("PUT", BASE + "/{event_id}/tie-resolutions"),
        ("POST", BASE + "/{event_id}/confirm-qualifiers"),
        ("GET", BASE + "/{event_id}/playoffs"),
        ("PUT", BASE + "/{event_id}/playoffs/{node_id}/result"),
    }


@pytest.mark.parametrize("mode", ["anonymous", "expired", "inactive"])
@pytest.mark.parametrize("method,path,payload", [
    ("GET", "", None),
    ("POST", "", {"name": "Privado", "zone_count": 1, "start_stage": "final"}),
    ("GET", "/1", None),
    ("PATCH", "/1", {"expected_revision": 1, "name": "Privado"}),
    ("POST", "/1/registrations", {"expected_revision": 1, "player1_name": "A", "player2_name": "B"}),
    ("POST", "/1/registrations/bulk", {"expected_revision": 1, "registrations": [
        {"player1_name": "A", "player2_name": "B"}, {"player1_name": "C", "player2_name": "D"},
    ]}),
    ("PATCH", "/1/registrations/1", {"expected_revision": 1, "player1_name": "A"}),
    ("DELETE", "/1/registrations/1?expected_revision=1", None),
    ("PUT", "/1/zones", {"expected_revision": 1, "zone_count": 1, "zone_a_registration_ids": []}),
    ("DELETE", "/1/zones?expected_revision=1", None),
    ("POST", "/1/zones/randomize", {"expected_revision": 1}),
    ("POST", "/1/fixture", {"expected_revision": 1}),
    ("GET", "/1/rounds/1", None),
    ("PUT", "/1/rounds/1/results", {"expected_revision": 1, "results": []}),
    ("GET", "/1/standings", None),
    ("GET", "/1/qualification", None),
    ("PUT", "/1/tie-resolutions", {"expected_revision": 1, "source_groups_revision": 0, "resolutions": []}),
    ("POST", "/1/confirm-qualifiers", {"expected_revision": 1, "source_groups_revision": 0,
                                      "confirmation_key": "6c764a9e-ad96-4c73-a468-f89261f3fa08"}),
    ("GET", "/1/playoffs", None),
    ("PUT", "/1/playoffs/1/result", {"expected_revision": 1, "games_a": 6, "games_b": 0, "set_complete": True}),
])
def test_all_twenty_operations_keep_real_admin_cookie_guard(americano_api, mode, method, path, payload):
    api = americano_api
    api.authenticate(mode)
    response = api.client.request(method, BASE + path, json=payload)
    assert response.status_code == 401 and response.json() == {"detail": "Not authenticated"}
    with Session(api.engine) as session:
        assert session.exec(select(AmericanoEvent)).all() == []


@pytest.mark.parametrize("mode", ["anonymous", "expired", "inactive"])
@pytest.mark.parametrize("operation", ["manual", "random"])
def test_zone_mutations_require_real_admin_guard_and_reveal_no_event_data(americano_api, mode, operation):
    api = americano_api
    detail = add_registration(api, create_event(api, zone_count=2))
    api.authenticate(mode)
    path = f"{BASE}/{detail['id']}/zones"
    if operation == "manual":
        response = api.client.put(path, json={
            "expected_revision": True, "zone_count": 1, "zone_a_registration_ids": [99999],
        })
    else:
        response = api.client.post(path + "/randomize", json={"expected_revision": True})
    assert response.status_code == 401 and response.json() == {"detail": "Not authenticated"}
    api.authenticate()
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail


def test_zone_mutations_and_foreign_payload_never_change_another_event(americano_api):
    api = americano_api
    first = add_registration(api, add_registration(api, create_event(api, zone_count=2)))
    second = add_registration(api, create_event(api, zone_count=2))
    path = f"{BASE}/{first['id']}/zones"
    response = api.client.put(path, json={
        "expected_revision": first["revision"], "zone_count": 2,
        "zone_a_registration_ids": [second["registrations"][0]["id"]],
    })
    assert response.status_code == 422 and response.json()["code"] == "invalid_reference"
    assert api.client.get(f"{BASE}/{first['id']}").json() == first
    assert api.client.get(f"{BASE}/{second['id']}").json() == second
    response = api.client.post(path + "/randomize", json={"expected_revision": first["revision"]})
    assert response.status_code == 200
    randomized = response.json()
    assert api.client.get(f"{BASE}/{second['id']}").json() == second
    response = api.client.put(path, json={
        "expected_revision": randomized["revision"], "zone_count": 1,
        "zone_a_registration_ids": [r["id"] for r in first["registrations"]],
    })
    assert response.status_code == 200 and response.json()["zone_count"] == 1
    assert api.client.get(f"{BASE}/{second['id']}").json() == second


@pytest.mark.parametrize("mode", ["anonymous", "expired", "inactive"])
def test_fixture_generation_requires_real_admin_guard_without_mutation(americano_api, mode):
    from app.americanos.models import AmericanoGroupMatch, AmericanoRound

    api = americano_api
    detail = add_registration(api, add_registration(api, create_event(api)))
    api.authenticate(mode)
    response = api.client.post(f"{BASE}/{detail['id']}/fixture", json={"expected_revision": True})
    assert response.status_code == 401 and response.json() == {"detail": "Not authenticated"}
    api.authenticate()
    assert api.client.get(f"{BASE}/{detail['id']}").json() == detail
    with Session(api.engine) as session:
        assert session.exec(select(AmericanoRound)).all() == []
        assert session.exec(select(AmericanoGroupMatch)).all() == []


def test_fixture_generation_only_persists_children_for_its_own_event(americano_api):
    from app.americanos.models import AmericanoGroupMatch, AmericanoRound

    api = americano_api
    first = add_registration(api, add_registration(api, create_event(api)))
    other = add_registration(api, add_registration(api, create_event(api)))
    response = api.client.post(f"{BASE}/{first['id']}/fixture", json={"expected_revision": first["revision"]})
    assert response.status_code == 200
    assert api.client.get(f"{BASE}/{other['id']}").json() == other
    with Session(api.engine) as session:
        rounds = session.exec(select(AmericanoRound)).all()
        matches = session.exec(select(AmericanoGroupMatch)).all()
        assert len(rounds) == len(matches) == 1
        assert rounds[0].event_id == matches[0].event_id == first["id"]
        assert {matches[0].registration_a_id, matches[0].registration_b_id} == {
            r["id"] for r in first["registrations"]
        }


@pytest.mark.parametrize("mode", ["anonymous", "expired", "inactive"])
@pytest.mark.parametrize("suffix", ["rounds/1", "standings"])
def test_round_and_standings_reads_require_real_admin_guard(americano_api, mode, suffix):
    api = americano_api
    event = add_registration(api, add_registration(api, create_event(api)))
    response = api.client.post(f"{BASE}/{event['id']}/fixture", json={"expected_revision": event["revision"]})
    assert response.status_code == 200
    event = response.json()["event"]
    api.authenticate(mode)
    response = api.client.get(f"{BASE}/{event['id']}/{suffix}")
    assert response.status_code == 401 and response.json() == {"detail": "Not authenticated"}
    api.authenticate()
    assert api.client.get(f"{BASE}/{event['id']}").json() == event


@pytest.mark.parametrize("mode", ["anonymous", "expired", "inactive"])
def test_round_results_require_real_admin_guard_even_for_invalid_body(americano_api, mode):
    api = americano_api
    event = add_registration(api, add_registration(api, create_event(api)))
    response = api.client.post(f"{BASE}/{event['id']}/fixture", json={"expected_revision": event["revision"]})
    assert response.status_code == 200
    event = response.json()["event"]
    api.authenticate(mode)
    response = api.client.put(f"{BASE}/{event['id']}/rounds/1/results", json={
        "expected_revision": True, "results": [],
    })
    assert response.status_code == 401 and response.json() == {"detail": "Not authenticated"}
    api.authenticate()
    assert api.client.get(f"{BASE}/{event['id']}").json() == event
    assert api.client.get(f"{BASE}/{event['id']}/rounds/1").json()["saved"] is False
