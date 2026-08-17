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
