"""Public voting on who wins a pending match.

The vote is anonymous: a device sends a key it made up and keeps, which is
enough to stop one person voting fifty times in a row without asking anyone to
register. Someone determined can clear it and vote again, and that is accepted.
"""

import pytest

from .conftest import STRAIGHT_WIN_A, ZONE_A, make_match, make_team

DEVICE = "device-key-aaaaaaaaaaaa"
OTHER_DEVICE = "device-key-bbbbbbbbbbbb"


@pytest.fixture
def teams(admin):
    return make_team(admin, ZONE_A, "Ana"), make_team(admin, ZONE_A, "Beto")


@pytest.fixture
def match(admin, teams):
    return make_match(admin, *teams)


def vote(client, match_id: int, team_id: int, device: str = DEVICE):
    return client.post(
        f"/public/matches/{match_id}/votes",
        json={"team_id": team_id, "voter_key": device},
    )


def tally(client, *match_ids: int, device: str | None = None):
    ids = ",".join(str(match_id) for match_id in match_ids)
    url = f"/public/matches/votes?ids={ids}"
    if device:
        url += f"&voter_key={device}"
    response = client.get(url)
    assert response.status_code == 200
    return {row["match_id"]: row for row in response.json()}


def test_a_vote_is_counted(client, match, teams):
    response = vote(client, match, teams[0])

    assert response.status_code == 200
    body = response.json()
    assert body["team_a_votes"] == 1
    assert body["team_b_votes"] == 0
    assert body["total"] == 1


def test_two_devices_voting_different_teams_are_both_counted(client, match, teams):
    vote(client, match, teams[0], DEVICE)
    body = vote(client, match, teams[1], OTHER_DEVICE).json()

    assert (body["team_a_votes"], body["team_b_votes"], body["total"]) == (1, 1, 2)


def test_the_same_device_voting_again_changes_its_vote(client, match, teams):
    vote(client, match, teams[0])
    body = vote(client, match, teams[1]).json()

    # Not two votes: one device holds one vote, and it may move it.
    assert (body["team_a_votes"], body["team_b_votes"], body["total"]) == (0, 1, 1)


def test_voting_the_same_team_twice_does_not_add_up(client, match, teams):
    vote(client, match, teams[0])
    body = vote(client, match, teams[0]).json()

    assert body["total"] == 1


def test_a_played_match_cannot_be_voted(admin, client, match, teams):
    admin.post(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_A)

    assert vote(client, match, teams[0]).status_code == 409


def test_votes_cast_before_the_result_survive_it(admin, client, match, teams):
    vote(client, match, teams[0])
    admin.post(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_A)

    # The payoff of the whole feature is showing afterwards whether the public
    # got it right, so loading the result must not wipe what was voted.
    assert tally(client, match)[match]["total"] == 1


def test_a_team_outside_the_match_is_rejected(admin, client, match):
    outsider = make_team(admin, ZONE_A, "Caro")

    assert vote(client, match, outsider).status_code == 400


def test_voting_a_match_that_does_not_exist_is_404(client, teams):
    assert vote(client, 9999, teams[0]).status_code == 404


def test_the_tally_of_an_unvoted_match_is_zero(client, match):
    row = tally(client, match)[match]

    assert (row["team_a_votes"], row["team_b_votes"], row["total"]) == (0, 0, 0)


def test_several_matches_are_tallied_in_one_call(admin, client, teams):
    third = make_team(admin, ZONE_A, "Caro")
    first_match = make_match(admin, *teams)
    second_match = make_match(admin, teams[0], third)

    vote(client, first_match, teams[0], DEVICE)
    vote(client, second_match, third, DEVICE)
    rows = tally(client, first_match, second_match)

    assert rows[first_match]["total"] == 1
    assert rows[second_match]["total"] == 1


def test_the_tally_says_what_this_device_voted(client, match, teams):
    vote(client, match, teams[1])

    mine = tally(client, match, device=DEVICE)[match]
    stranger = tally(client, match, device=OTHER_DEVICE)[match]

    # Without this the page cannot show "you picked them" after a reload.
    assert mine["voted_team_id"] == teams[1]
    assert stranger["voted_team_id"] is None


def test_an_unknown_match_id_is_left_out_of_the_tally(client, match):
    rows = tally(client, match, 9999)

    assert set(rows) == {match}
