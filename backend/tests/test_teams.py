from .conftest import ZONE_A, ZONE_B, make_team

NEW_TEAM = {"zone_id": ZONE_A, "player_one_name": "Ana", "player_two_name": "Bea"}


def test_admin_routes_are_closed_without_a_session(client):
    assert client.get("/admin/teams").status_code == 401
    assert client.post("/admin/teams", json=NEW_TEAM).status_code == 401


def test_create_team(admin):
    response = admin.post("/admin/teams", json=NEW_TEAM)

    assert response.status_code == 201
    body = response.json()
    assert body["player_one_name"] == "Ana"
    assert body["status"] == "active"
    assert body["photo_url"] is None


def test_create_team_in_an_unknown_zone(admin):
    response = admin.post("/admin/teams", json={**NEW_TEAM, "zone_id": 99})

    assert response.status_code == 404


def test_player_names_cannot_be_empty(admin):
    response = admin.post("/admin/teams", json={**NEW_TEAM, "player_one_name": ""})

    assert response.status_code == 422


def test_list_teams_filtered_by_zone(admin):
    make_team(admin, ZONE_A, "Ana")
    make_team(admin, ZONE_B, "Eva")

    assert len(admin.get("/admin/teams").json()) == 2
    assert len(admin.get(f"/admin/teams?zone_id={ZONE_A}").json()) == 1
    assert len(admin.get("/admin/teams?zone_id=99").json()) == 0


def test_get_unknown_team(admin):
    assert admin.get("/admin/teams/999").status_code == 404


def test_withdrawing_a_team_is_a_status_change(admin):
    team_id = make_team(admin)

    response = admin.patch(f"/admin/teams/{team_id}", json={"status": "withdrawn"})

    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"


def test_teams_have_no_delete_endpoint(admin):
    team_id = make_team(admin)

    assert admin.delete(f"/admin/teams/{team_id}").status_code == 405


def test_zone_id_is_immutable(admin):
    team_id = make_team(admin, ZONE_A)

    response = admin.patch(f"/admin/teams/{team_id}", json={"zone_id": ZONE_B})

    assert response.status_code == 400
    assert "immutable" in response.json()["detail"]
    assert admin.get(f"/admin/teams/{team_id}").json()["zone_id"] == ZONE_A


def test_an_unknown_field_is_rejected_instead_of_ignored(admin):
    team_id = make_team(admin)

    response = admin.patch(f"/admin/teams/{team_id}", json={"player_one_nme": "typo"})

    assert response.status_code == 422


def test_a_partial_update_leaves_the_other_fields_alone(admin):
    team_id = make_team(admin, ZONE_A, "Ana")

    admin.patch(f"/admin/teams/{team_id}", json={"player_two_name": "Carla"})

    body = admin.get(f"/admin/teams/{team_id}").json()
    assert body["player_one_name"] == "Ana"
    assert body["player_two_name"] == "Carla"
