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
             "/public/matches?status=pending", f"/public/standings?zone_id={zone_id}"]

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
        assert api.client.post(f"{BASE}/{detail['id']}/zones/randomize", json={
            "expected_revision": 6,
        }).status_code == 200
    finally:
        sql_event.remove(api.engine, "before_cursor_execute", executed)
    assert statements and all("americano_" in sql or "admin_users" in sql for sql in statements)
    assert league_rows() == league_before
    assert public_snapshot() == public_before


def test_only_the_nine_authorized_operations_are_published(americano_api):
    from app.main import app

    paths = app.openapi()["paths"]
    published = {(method.upper(), path) for path, methods in paths.items()
                 if path.startswith(BASE) for method in methods}
    assert published == {
        ("GET", BASE), ("POST", BASE),
        ("GET", BASE + "/{event_id}"), ("PATCH", BASE + "/{event_id}"),
        ("POST", BASE + "/{event_id}/registrations"),
        ("PATCH", BASE + "/{event_id}/registrations/{registration_id}"),
        ("DELETE", BASE + "/{event_id}/registrations/{registration_id}"),
        ("PUT", BASE + "/{event_id}/zones"),
        ("POST", BASE + "/{event_id}/zones/randomize"),
    }


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
