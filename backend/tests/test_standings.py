"""The twelve minimum scenarios from docs/04.

Every one of them targets `calculate_standings`, the pure function. No database,
no FastAPI, no migrations: the scenarios are built by hand in memory.
"""

from app.standings.service import PlayedMatch, calculate_standings
from app.teams.models import Team, TeamStatus

STRAIGHT_WIN = [(6, 4), (6, 4)]  # 2-0, +4 games for the winner
STRAIGHT_LOSS = [(4, 6), (4, 6)]  # the same match seen from the other side


def team(team_id: int, zone_id: int = 1) -> Team:
    return Team(
        id=team_id,
        zone_id=zone_id,
        player_one_name=f"P{team_id}A",
        player_two_name=f"P{team_id}B",
    )


def order(rows) -> list[int]:
    """Team ids in table order."""
    return [row.team_id for row in rows]


def row_for(rows, team_id: int):
    return next(row for row in rows if row.team_id == team_id)


def test_zone_with_no_played_matches_is_all_zeros():
    rows = calculate_standings([team(1), team(2), team(3)], [])

    assert order(rows) == [1, 2, 3]
    assert [row.position for row in rows] == [1, 2, 3]
    for row in rows:
        assert (row.played, row.won, row.lost, row.points) == (0, 0, 0, 0)
        assert (row.sets_diff, row.games_diff) == (0, 0)


def test_straight_win_gives_three_points_and_zero():
    rows = calculate_standings([team(1), team(2)], [PlayedMatch(1, 2, STRAIGHT_WIN)])

    assert (row_for(rows, 1).points, row_for(rows, 2).points) == (3, 0)
    assert (row_for(rows, 1).won, row_for(rows, 1).lost) == (1, 0)
    assert (row_for(rows, 2).won, row_for(rows, 2).lost) == (0, 1)


def test_tight_win_gives_two_points_and_one():
    rows = calculate_standings(
        [team(1), team(2)],
        [PlayedMatch(1, 2, [(6, 3), (2, 6), (7, 6)])],
    )

    assert (row_for(rows, 1).points, row_for(rows, 2).points) == (2, 1)
    assert (row_for(rows, 1).sets_won, row_for(rows, 1).sets_lost) == (2, 1)


def test_order_resolved_by_points():
    matches = [
        PlayedMatch(1, 3, STRAIGHT_WIN),  # team 1 wins 2-0 -> 3 points
        PlayedMatch(2, 4, [(6, 4), (4, 6), (6, 4)]),  # team 2 wins 2-1 -> 2 points
    ]
    rows = calculate_standings([team(1), team(2), team(3), team(4)], matches)

    assert row_for(rows, 1).points > row_for(rows, 2).points
    assert order(rows).index(1) < order(rows).index(2)


def test_order_resolved_by_set_difference_when_points_are_equal():
    matches = [
        PlayedMatch(1, 3, STRAIGHT_WIN),  # 3 points, sets 2-0
        PlayedMatch(2, 4, [(6, 4), (4, 6), (6, 4)]),  # 2 points, sets 2-1
        PlayedMatch(2, 5, [(6, 4), (4, 6), (4, 6)]),  # 1 point, sets 1-2
    ]
    teams = [team(1), team(2), team(3), team(4), team(5)]
    rows = calculate_standings(teams, matches)

    one, two = row_for(rows, 1), row_for(rows, 2)
    assert one.points == two.points == 3  # points do NOT separate them
    assert (one.sets_diff, two.sets_diff) == (2, 0)  # set difference does
    assert order(rows).index(1) < order(rows).index(2)


def test_order_resolved_by_game_difference_when_points_and_sets_are_equal():
    matches = [
        PlayedMatch(1, 3, [(6, 0), (6, 0)]),  # +12 games
        PlayedMatch(2, 4, [(6, 4), (6, 4)]),  # +4 games
    ]
    rows = calculate_standings([team(1), team(2), team(3), team(4)], matches)

    one, two = row_for(rows, 1), row_for(rows, 2)
    assert one.points == two.points  # points do NOT separate them
    assert one.sets_diff == two.sets_diff  # set difference does NOT either
    assert one.games_diff > two.games_diff  # game difference does
    assert order(rows).index(1) < order(rows).index(2)


def test_two_teams_tied_in_everything_use_the_head_to_head_winner():
    """Teams 1 and 2 end identical in points, set diff and game diff.

    Team 2 beat team 1, so team 2 goes first. Note both won exactly 2 sets, so
    criterion 2 cannot separate them and criterion 3 would put team 1 first:
    the only thing that flips the order here is the head-to-head.
    """
    matches = [
        PlayedMatch(1, 2, STRAIGHT_LOSS),  # team 2 wins the head-to-head
        PlayedMatch(1, 3, STRAIGHT_WIN),
        PlayedMatch(4, 2, STRAIGHT_WIN),
    ]
    teams = [team(1), team(2), team(3), team(4)]
    rows = calculate_standings(teams, matches)

    one, two = row_for(rows, 1), row_for(rows, 2)
    assert (one.points, one.sets_diff, one.games_diff) == (3, 0, 0)
    assert (two.points, two.sets_diff, two.games_diff) == (3, 0, 0)
    assert one.sets_won == two.sets_won == 2  # criterion 2 is powerless here
    assert order(rows) == [4, 2, 1, 3]


def test_two_teams_tied_without_head_to_head_fall_through_the_cascade():
    """Same perfect tie, but teams 1 and 2 never played each other.

    Criterion 1 does not apply, criterion 2 cannot separate them either, so the
    order falls to team id ascending — and team 1 goes first, the opposite of
    the head-to-head case above.
    """
    matches = [
        PlayedMatch(1, 3, STRAIGHT_WIN),
        PlayedMatch(1, 5, STRAIGHT_LOSS),
        PlayedMatch(2, 4, STRAIGHT_WIN),
        PlayedMatch(2, 6, STRAIGHT_LOSS),
    ]
    teams = [team(i) for i in range(1, 7)]
    rows = calculate_standings(teams, matches)

    one, two = row_for(rows, 1), row_for(rows, 2)
    assert (one.points, one.sets_diff, one.games_diff) == (3, 0, 0)
    assert (two.points, two.sets_diff, two.games_diff) == (3, 0, 0)
    assert order(rows).index(1) < order(rows).index(2)
    assert order(rows) == [5, 6, 1, 2, 3, 4]


def test_three_tied_teams_never_try_head_to_head():
    """A group of three skips criterion 1 entirely and resolves by the rest."""
    rows = calculate_standings([team(3), team(1), team(2)], [])

    assert order(rows) == [1, 2, 3]


def test_perfect_tie_is_deterministic_across_runs():
    teams = [team(5), team(2), team(9), team(1)]

    first = order(calculate_standings(teams, []))
    second = order(calculate_standings(list(reversed(teams)), []))

    assert first == second == [1, 2, 5, 9]


def test_points_average_with_zero_played_matches_does_not_divide_by_zero():
    rows = calculate_standings([team(1)], [])

    assert rows[0].points_average == 0.0
    assert rows[0].played == 0


def test_withdrawn_team_stays_in_the_table_with_its_real_points():
    withdrawn = team(2)
    withdrawn.status = TeamStatus.WITHDRAWN

    rows = calculate_standings(
        [team(1), withdrawn],
        [PlayedMatch(2, 1, STRAIGHT_WIN)],
    )

    assert row_for(rows, 2).points == 3
    assert order(rows)[0] == 2
