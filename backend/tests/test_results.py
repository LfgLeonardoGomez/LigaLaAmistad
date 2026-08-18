import pytest
from sqlmodel import Session

from app.database.session import engine
from app.matches.models import COMMENT_MAX_LENGTH, Match

from .conftest import STRAIGHT_WIN_A, STRAIGHT_WIN_B, make_match, make_team, sets_payload

PHOTO = "https://res.cloudinary.com/demo/image/upload/match.jpg"


@pytest.fixture
def match(admin):
    a, b = make_team(admin, name="Ana"), make_team(admin, name="Bea")
    return make_match(admin, a, b)


def store_photo(match_id: int, url: str = PHOTO) -> None:
    """Write the photo URL straight to the row.

    Going through the endpoint would need a live Cloudinary, and what these
    tests are about is what happens to the URL afterwards, not how it got there.
    """
    with Session(engine) as session:
        stored = session.get(Match, match_id)
        stored.photo_url = url
        session.add(stored)
        session.commit()


def with_comment(payload: dict, comment) -> dict:
    return {**payload, "comment": comment}


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


# --- Photo and comment --------------------------------------------------------


def test_a_result_can_be_loaded_with_a_comment(admin, match):
    response = admin.post(
        f"/admin/matches/{match}/result",
        json=with_comment(STRAIGHT_WIN_A, "Les dimos una clase de drive"),
    )

    assert response.status_code == 200
    assert response.json()["comment"] == "Les dimos una clase de drive"


def test_a_result_without_a_comment_reads_back_as_null(admin, match):
    body = admin.post(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_A).json()

    assert body["comment"] is None
    assert body["photo_url"] is None


def test_a_comment_longer_than_the_limit_is_rejected(admin, match):
    payload = with_comment(STRAIGHT_WIN_A, "a" * (COMMENT_MAX_LENGTH + 1))

    assert admin.post(f"/admin/matches/{match}/result", json=payload).status_code == 422


def test_a_comment_of_exactly_the_limit_is_accepted(admin, match):
    payload = with_comment(STRAIGHT_WIN_A, "a" * COMMENT_MAX_LENGTH)

    response = admin.post(f"/admin/matches/{match}/result", json=payload)

    assert response.status_code == 200
    assert len(response.json()["comment"]) == COMMENT_MAX_LENGTH


def test_correcting_the_marker_keeps_the_photo_and_the_comment(admin, match):
    """The point of the whole feature: a typo in the score costs nothing else."""
    admin.post(f"/admin/matches/{match}/result", json=with_comment(STRAIGHT_WIN_A, "Cargada"))
    store_photo(match)

    response = admin.put(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_B)

    body = response.json()
    assert body["winner_team_id"] == 2
    assert body["comment"] == "Cargada"
    assert body["photo_url"] == PHOTO


def test_correcting_the_marker_with_a_comment_replaces_the_old_one(admin, match):
    admin.post(f"/admin/matches/{match}/result", json=with_comment(STRAIGHT_WIN_A, "Cargada"))

    body = admin.put(
        f"/admin/matches/{match}/result", json=with_comment(STRAIGHT_WIN_B, "Se dieron vuelta")
    ).json()

    assert body["comment"] == "Se dieron vuelta"


def test_the_comment_can_be_edited_on_its_own(admin, match):
    admin.post(f"/admin/matches/{match}/result", json=with_comment(STRAIGHT_WIN_A, "Cargada"))
    store_photo(match)

    response = admin.patch(f"/admin/matches/{match}/result", json={"comment": "Mejor redactada"})

    body = response.json()
    assert body["comment"] == "Mejor redactada"
    # The sets and the photo are none of this endpoint's business.
    assert len(body["sets"]) == 2
    assert body["winner_team_id"] == 1
    assert body["photo_url"] == PHOTO


def test_the_comment_can_be_erased_without_touching_the_result(admin, match):
    admin.post(f"/admin/matches/{match}/result", json=with_comment(STRAIGHT_WIN_A, "Cargada"))

    body = admin.patch(f"/admin/matches/{match}/result", json={"comment": None}).json()

    assert body["comment"] is None
    assert body["status"] == "played"
    assert len(body["sets"]) == 2


def test_editing_the_comment_respects_the_limit(admin, match):
    admin.post(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_A)

    response = admin.patch(
        f"/admin/matches/{match}/result", json={"comment": "a" * (COMMENT_MAX_LENGTH + 1)}
    )

    assert response.status_code == 422


def test_a_pending_match_cannot_be_commented(admin, match):
    assert admin.patch(f"/admin/matches/{match}/result", json={"comment": "Hola"}).status_code == 400


def test_undoing_the_result_drops_the_photo_and_the_comment(admin, match):
    """A pending match can change teams, and the jab would end up on strangers."""
    admin.post(f"/admin/matches/{match}/result", json=with_comment(STRAIGHT_WIN_A, "Cargada"))
    store_photo(match)

    body = admin.delete(f"/admin/matches/{match}/result").json()

    assert body["status"] == "pending"
    assert body["comment"] is None
    assert body["photo_url"] is None


def test_the_public_result_carries_the_photo_and_the_comment(admin, client, match):
    admin.post(f"/admin/matches/{match}/result", json=with_comment(STRAIGHT_WIN_A, "Cargada"))
    store_photo(match)

    body = client.get("/public/matches").json()

    assert body[0]["comment"] == "Cargada"
    assert body[0]["photo_url"] == PHOTO
