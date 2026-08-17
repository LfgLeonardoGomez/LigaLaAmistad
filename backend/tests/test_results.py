import pytest

from .conftest import STRAIGHT_WIN_A, STRAIGHT_WIN_B, make_match, make_team, sets_payload


@pytest.fixture
def match(admin):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")
    return make_match(admin, a, b)


@pytest.mark.parametrize(
    "label, payload",
    [
        ("one set only", sets_payload((6, 4))),
        ("four sets", sets_payload((6, 4), (6, 4), (6, 4), (6, 4))),
        ("a tied set", sets_payload((6, 6), (6, 4))),
        ("nobody wins two sets", sets_payload((6, 4), (4, 6))),
    ],
)
def test_invalid_results_are_rejected(admin, match, label, payload):
    assert admin.post(f"/admin/matches/{match}/result", json=payload).status_code == 400


def test_set_numbers_must_be_consecutive_from_one(admin, match):
    payload = {
        "sets": [
            {"set_number": 1, "team_a_games": 6, "team_b_games": 4},
            {"set_number": 3, "team_a_games": 6, "team_b_games": 4},
        ]
    }

    assert admin.post(f"/admin/matches/{match}/result", json=payload).status_code == 400


def test_a_rejected_result_leaves_the_match_untouched(admin, match):
    admin.post(f"/admin/matches/{match}/result", json=sets_payload((6, 4)))

    body = admin.get(f"/admin/matches/{match}").json()
    assert body["status"] == "pending"
    assert body["sets"] == []


def test_loading_a_result_computes_the_winner(admin, match):
    response = admin.post(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_A)

    body = response.json()
    assert body["status"] == "played"
    assert body["winner_team_id"] == 1
    assert len(body["sets"]) == 2


def test_a_three_set_match_is_valid(admin, match):
    response = admin.post(
        f"/admin/matches/{match}/result", json=sets_payload((6, 4), (4, 6), (6, 4))
    )

    assert response.status_code == 200
    assert response.json()["winner_team_id"] == 1


def test_a_result_cannot_be_loaded_twice(admin, match):
    admin.post(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_A)

    assert admin.post(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_A).status_code == 400


def test_replacing_a_result_flips_the_winner_without_duplicating_sets(admin, match):
    admin.post(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_A)

    response = admin.put(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_B)

    body = response.json()
    assert body["winner_team_id"] == 2
    assert len(body["sets"]) == 2
    assert body["status"] == "played"


def test_a_pending_match_has_no_result_to_replace(admin, match):
    assert admin.put(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_A).status_code == 400


def test_undoing_a_result_returns_the_match_to_pending(admin, match):
    admin.post(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_A)

    response = admin.delete(f"/admin/matches/{match}/result")

    body = response.json()
    assert body["status"] == "pending"
    assert body["sets"] == []
    assert body["winner_team_id"] is None


def test_a_pending_match_has_no_result_to_undo(admin, match):
    assert admin.delete(f"/admin/matches/{match}/result").status_code == 400


def test_replacing_a_result_with_an_invalid_one_keeps_the_old_one(admin, match):
    admin.post(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_A)

    admin.put(f"/admin/matches/{match}/result", json=sets_payload((6, 4)))

    body = admin.get(f"/admin/matches/{match}").json()
    assert body["winner_team_id"] == 1
    assert len(body["sets"]) == 2
