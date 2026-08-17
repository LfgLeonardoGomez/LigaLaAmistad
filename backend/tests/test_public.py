from .conftest import STRAIGHT_WIN_A, ZONE_A, ZONE_B, make_match, make_team, sets_payload

PUBLIC_PATHS = [
    "/public/zones",
    "/public/teams",
    "/public/matches",
    "/public/sponsors",
    f"/public/standings?zone_id={ZONE_A}",
]


def test_every_public_endpoint_is_open(client):
    for path in PUBLIC_PATHS:
        assert client.get(path).status_code == 200, path


def test_zones_come_from_the_seed(client):
    names = [zone["name"] for zone in client.get("/public/zones").json()]

    assert names == ["Zona A", "Zona B"]


def test_public_teams_can_be_filtered_by_zone(admin):
    make_team(admin, ZONE_A, "Ana")
    make_team(admin, ZONE_B, "Eva")

    assert len(admin.get("/public/teams").json()) == 2
    assert len(admin.get(f"/public/teams?zone_id={ZONE_B}").json()) == 1


def test_the_public_site_never_shows_pending_matches(admin):
    a, b, c = (make_team(admin, name=n) for n in ("Ana", "Bea", "Cid"))
    played = make_match(admin, a, b)
    make_match(admin, a, c)
    admin.post(f"/admin/matches/{played}/result", json=STRAIGHT_WIN_A)

    public = admin.get("/public/matches").json()

    assert len(public) == 1
    assert public[0]["status"] == "played"
    assert len(admin.get("/admin/matches").json()) == 2


def test_undoing_a_result_hides_the_match_from_the_public_site(admin):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")
    match_id = make_match(admin, a, b)
    admin.post(f"/admin/matches/{match_id}/result", json=STRAIGHT_WIN_A)
    assert len(admin.get("/public/matches").json()) == 1

    admin.delete(f"/admin/matches/{match_id}/result")

    assert len(admin.get("/public/matches").json()) == 0


def test_standings_are_recomputed_after_a_correction(admin):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")
    match_id = make_match(admin, a, b)
    admin.post(f"/admin/matches/{match_id}/result", json=STRAIGHT_WIN_A)

    before = admin.get(f"/public/standings?zone_id={ZONE_A}").json()
    assert before[0]["team_id"] == a
    assert before[0]["points"] == 3

    admin.put(f"/admin/matches/{match_id}/result", json=sets_payload((4, 6), (4, 6)))

    after = admin.get(f"/public/standings?zone_id={ZONE_A}").json()
    assert after[0]["team_id"] == b
    assert after[0]["points"] == 3


def test_standings_of_a_zone_with_no_matches(admin):
    make_team(admin, ZONE_A, "Ana")

    table = admin.get(f"/public/standings?zone_id={ZONE_A}").json()

    assert len(table) == 1
    assert table[0]["played"] == 0
    assert table[0]["points_average"] == 0


def test_standings_require_a_zone(client):
    assert client.get("/public/standings").status_code == 422


def test_the_public_site_only_shows_active_sponsors(admin):
    admin.post("/admin/sponsors", json={"name": "Uno", "logo_url": "http://x/1.png"})
    admin.post(
        "/admin/sponsors",
        json={"name": "Dos", "logo_url": "http://x/2.png", "is_active": False},
    )

    assert len(admin.get("/admin/sponsors").json()) == 2
    assert len(admin.get("/public/sponsors").json()) == 1


def test_sponsors_can_be_deleted(admin):
    created = admin.post(
        "/admin/sponsors", json={"name": "Uno", "logo_url": "http://x/1.png"}
    ).json()

    assert admin.delete(f"/admin/sponsors/{created['id']}").status_code == 204
    assert admin.get("/admin/sponsors").json() == []


def test_sponsor_admin_routes_need_a_session(client):
    assert client.get("/admin/sponsors").status_code == 401
