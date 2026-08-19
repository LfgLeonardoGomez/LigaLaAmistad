import pytest

from .conftest import (
    STRAIGHT_WIN_A,
    ZONE_A,
    ZONE_B,
    make_match,
    make_team,
    sets_payload,
)


def test_create_match(admin):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")

    response = admin.post(
        "/admin/matches", json={"team_a_id": a, "team_b_id": b, "date": "2026-09-01"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["winner_team_id"] is None
    assert body["sets"] == []


def test_a_team_cannot_play_itself(admin):
    a = make_team(admin)

    response = admin.post(
        "/admin/matches", json={"team_a_id": a, "team_b_id": a, "date": "2026-09-01"}
    )

    assert response.status_code == 400


def test_both_teams_must_share_a_zone(admin):
    a = make_team(admin, ZONE_A, "Ana")
    b = make_team(admin, ZONE_B, "Eva")

    response = admin.post(
        "/admin/matches", json={"team_a_id": a, "team_b_id": b, "date": "2026-09-01"}
    )

    assert response.status_code == 400


def test_the_date_is_required(admin):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")

    response = admin.post("/admin/matches", json={"team_a_id": a, "team_b_id": b})

    assert response.status_code == 422


def test_a_match_never_carries_a_zone(admin):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")
    match_id = make_match(admin, a, b)

    assert "zone_id" not in admin.get(f"/admin/matches/{match_id}").json()


def test_list_matches_by_status(admin):
    a, b, c = (make_team(admin, name=n) for n in ("Ana", "Bea", "Cid"))
    played = make_match(admin, a, b)
    make_match(admin, a, c)
    admin.post(f"/admin/matches/{played}/result", json=STRAIGHT_WIN_A)

    assert len(admin.get("/admin/matches").json()) == 2
    assert len(admin.get("/admin/matches?status=pending").json()) == 1
    assert len(admin.get("/admin/matches?status=played").json()) == 1


def test_list_matches_by_zone_resolves_through_the_teams(admin):
    a, b = make_team(admin, ZONE_A, "Ana"), make_team(admin, ZONE_A, "Bea")
    c, d = make_team(admin, ZONE_B, "Cid"), make_team(admin, ZONE_B, "Dan")
    make_match(admin, a, b)
    make_match(admin, c, d)

    assert len(admin.get(f"/admin/matches?zone_id={ZONE_A}").json()) == 1
    assert len(admin.get(f"/admin/matches?zone_id={ZONE_B}").json()) == 1


def test_a_pending_match_can_be_corrected(admin):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")
    match_id = make_match(admin, a, b)

    response = admin.patch(f"/admin/matches/{match_id}", json={"date": "2026-09-15"})

    assert response.status_code == 200
    assert response.json()["date"] == "2026-09-15"


def test_correcting_the_teams_revalidates_the_zone(admin):
    a, b = make_team(admin, ZONE_A, "Ana"), make_team(admin, ZONE_A, "Bea")
    outsider = make_team(admin, ZONE_B, "Eva")
    match_id = make_match(admin, a, b)

    response = admin.patch(f"/admin/matches/{match_id}", json={"team_b_id": outsider})

    assert response.status_code == 400


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_a_played_match_is_frozen_until_its_result_is_undone(admin, method):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")
    match_id = make_match(admin, a, b)
    admin.post(f"/admin/matches/{match_id}/result", json=STRAIGHT_WIN_A)

    if method == "patch":
        response = admin.patch(f"/admin/matches/{match_id}", json={"date": "2026-10-01"})
    else:
        response = admin.delete(f"/admin/matches/{match_id}")
    assert response.status_code == 400

    admin.delete(f"/admin/matches/{match_id}/result")
    if method == "patch":
        assert admin.patch(f"/admin/matches/{match_id}", json={"date": "2026-10-01"}).status_code == 200
    else:
        assert admin.delete(f"/admin/matches/{match_id}").status_code == 204


def test_deleting_a_match_removes_it(admin):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")
    match_id = make_match(admin, a, b)

    assert admin.delete(f"/admin/matches/{match_id}").status_code == 204
    assert admin.get(f"/admin/matches/{match_id}").status_code == 404


def test_sets_of_a_deleted_match_do_not_survive(admin):
    """A new match must not inherit the sets of a deleted one."""
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")
    match_id = make_match(admin, a, b)
    admin.post(f"/admin/matches/{match_id}/result", json=sets_payload((6, 1), (6, 1)))
    admin.delete(f"/admin/matches/{match_id}/result")
    admin.delete(f"/admin/matches/{match_id}")

    fresh = make_match(admin, a, b)
    assert admin.get(f"/admin/matches/{fresh}").json()["sets"] == []


# --- Time and venue -----------------------------------------------------------


def test_a_match_can_be_created_with_a_time_and_a_venue(admin):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")

    response = admin.post(
        "/admin/matches",
        json={
            "team_a_id": a,
            "team_b_id": b,
            "date": "2026-09-01",
            "time": "20:30",
            "venue": "boss_padel",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["time"] == "20:30:00"
    assert body["venue"] == "boss_padel"


def test_a_match_without_a_time_or_a_venue_keeps_both_empty(admin):
    """The matches already loaded have neither, so neither can be required."""
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")
    match_id = make_match(admin, a, b)

    body = admin.get(f"/admin/matches/{match_id}").json()

    assert body["time"] is None
    assert body["venue"] is None


def test_the_venue_is_a_closed_list(admin):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")

    response = admin.post(
        "/admin/matches",
        json={
            "team_a_id": a,
            "team_b_id": b,
            "date": "2026-09-01",
            "venue": "el club de la esquina",
        },
    )

    assert response.status_code == 422


def test_a_pending_match_can_get_its_time_and_venue_later(admin):
    """Where and when are agreed after the match is already scheduled."""
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")
    match_id = make_match(admin, a, b)

    response = admin.patch(
        f"/admin/matches/{match_id}", json={"time": "19:00", "venue": "punto_de_oro"}
    )

    assert response.status_code == 200
    assert response.json()["time"] == "19:00:00"
    assert response.json()["venue"] == "punto_de_oro"


def test_the_time_and_the_venue_can_be_erased(admin):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")
    match_id = make_match(admin, a, b)
    admin.patch(f"/admin/matches/{match_id}", json={"time": "19:00", "venue": "arena"})

    response = admin.patch(
        f"/admin/matches/{match_id}", json={"time": None, "venue": None}
    )

    assert response.status_code == 200
    assert response.json()["time"] is None
    assert response.json()["venue"] is None


def test_matches_of_the_same_day_run_by_time_with_the_undecided_ones_last(admin):
    a, b, c, d = (make_team(admin, name=n) for n in ("Ana", "Bea", "Cid", "Dan"))
    late = make_match(admin, a, b)
    early = make_match(admin, c, d)
    undecided = make_match(admin, a, c)
    admin.patch(f"/admin/matches/{late}", json={"time": "21:00"})
    admin.patch(f"/admin/matches/{early}", json={"time": "09:00"})

    order = [match["id"] for match in admin.get("/admin/matches").json()]

    assert order == [early, late, undecided]


def test_the_public_fixture_carries_the_time_and_the_venue(admin):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")
    match_id = make_match(admin, a, b)
    admin.patch(f"/admin/matches/{match_id}", json={"time": "18:00", "venue": "cofam"})

    pending = admin.get("/public/matches?status=pending").json()

    assert pending[0]["time"] == "18:00:00"
    assert pending[0]["venue"] == "cofam"
