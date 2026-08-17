"""Standings are never stored. They are recomputed from played matches on every read.

The module is split in two on purpose:

- `get_standings` is the only half that knows about the database.
- `calculate_standings` is a pure function: same input, same output, always.
  Every tournament rule lives there, and it is tested without a database.
"""

from collections import defaultdict
from typing import NamedTuple

from sqlmodel import Session, select

from app.matches.models import Match, MatchSet, MatchStatus
from app.teams.models import Team

WIN_POINTS_STRAIGHT = 3  # won 2-0
WIN_POINTS_TIGHT = 2  # won 2-1
LOSS_POINTS_TIGHT = 1  # lost 1-2
LOSS_POINTS_STRAIGHT = 0  # lost 0-2

SETS_TO_WIN_MATCH = 2


class PlayedMatch(NamedTuple):
    """The only thing `calculate_standings` needs to know about a match.

    Deliberately poor: no date, no status, no zone. The fewer inputs it takes,
    the easier it is to build a test scenario by hand.
    """

    team_a_id: int
    team_b_id: int
    sets: list[tuple[int, int]]  # (team_a_games, team_b_games) per set, in order


class StandingRow(NamedTuple):
    position: int
    team_id: int
    played: int
    won: int
    lost: int
    points: int
    sets_won: int
    sets_lost: int
    sets_diff: int
    games_won: int
    games_lost: int
    games_diff: int
    points_average: float


class _Metrics:
    """Mutable accumulator used while walking the matches. Not part of the output."""

    def __init__(self, team_id: int) -> None:
        self.team_id = team_id
        self.played = 0
        self.won = 0
        self.lost = 0
        self.points = 0
        self.sets_won = 0
        self.sets_lost = 0
        self.games_won = 0
        self.games_lost = 0

    @property
    def sets_diff(self) -> int:
        return self.sets_won - self.sets_lost

    @property
    def games_diff(self) -> int:
        return self.games_won - self.games_lost

    @property
    def points_average(self) -> float:
        if self.played == 0:
            return 0.0
        return round(self.points / self.played, 2)


def calculate_standings(
    teams: list[Team], matches: list[PlayedMatch]
) -> list[StandingRow]:
    """Build the ordered standings table for one zone.

    Pure: no database, no configuration, no clock. Withdrawn teams are included,
    they keep the points they actually earned.
    """
    metrics = {team.id: _Metrics(team.id) for team in teams}

    for match in matches:
        if match.team_a_id not in metrics or match.team_b_id not in metrics:
            continue

        team_a = metrics[match.team_a_id]
        team_b = metrics[match.team_b_id]
        sets_a = 0
        sets_b = 0

        for games_a, games_b in match.sets:
            team_a.games_won += games_a
            team_a.games_lost += games_b
            team_b.games_won += games_b
            team_b.games_lost += games_a
            if games_a > games_b:
                sets_a += 1
            elif games_b > games_a:
                sets_b += 1

        team_a.sets_won += sets_a
        team_a.sets_lost += sets_b
        team_b.sets_won += sets_b
        team_b.sets_lost += sets_a

        team_a.played += 1
        team_b.played += 1

        winner, loser = (team_a, team_b) if sets_a > sets_b else (team_b, team_a)
        loser_sets = min(sets_a, sets_b)

        winner.won += 1
        loser.lost += 1
        if loser_sets == 0:
            winner.points += WIN_POINTS_STRAIGHT
            loser.points += LOSS_POINTS_STRAIGHT
        else:
            winner.points += WIN_POINTS_TIGHT
            loser.points += LOSS_POINTS_TIGHT

    ordered = sorted(
        metrics.values(),
        key=lambda m: (m.points, m.sets_diff, m.games_diff),
        reverse=True,
    )
    ordered = _break_ties(ordered, matches)

    return [
        StandingRow(
            position=index,
            team_id=m.team_id,
            played=m.played,
            won=m.won,
            lost=m.lost,
            points=m.points,
            sets_won=m.sets_won,
            sets_lost=m.sets_lost,
            sets_diff=m.sets_diff,
            games_won=m.games_won,
            games_lost=m.games_lost,
            games_diff=m.games_diff,
            points_average=m.points_average,
        )
        for index, m in enumerate(ordered, start=1)
    ]


def _break_ties(ordered: list[_Metrics], matches: list[PlayedMatch]) -> list[_Metrics]:
    """Resolve every group left with identical points, set diff and game diff.

    Each group is resolved by a cascade that stops at the first criterion that
    separates: head-to-head (only for a group of exactly two whose match was
    played), then total sets won, then team id ascending.
    """
    result: list[_Metrics] = []
    group: list[_Metrics] = []

    def flush(current: list[_Metrics]) -> None:
        if len(current) == 1:
            result.extend(current)
            return
        if len(current) == 2:
            winner_id = _head_to_head_winner(current[0].team_id, current[1].team_id, matches)
            if winner_id is not None:
                first, second = current if current[0].team_id == winner_id else current[::-1]
                result.extend([first, second])
                return
        result.extend(sorted(current, key=lambda m: (-m.sets_won, m.team_id)))

    for metric in ordered:
        key = (metric.points, metric.sets_diff, metric.games_diff)
        if group and key != (group[0].points, group[0].sets_diff, group[0].games_diff):
            flush(group)
            group = []
        group.append(metric)

    if group:
        flush(group)

    return result


def _head_to_head_winner(
    team_one_id: int, team_two_id: int, matches: list[PlayedMatch]
) -> int | None:
    """Winner of the match between these two teams, or None if they never played."""
    for match in matches:
        pair = {match.team_a_id, match.team_b_id}
        if pair != {team_one_id, team_two_id}:
            continue
        sets_a = sum(1 for games_a, games_b in match.sets if games_a > games_b)
        sets_b = sum(1 for games_a, games_b in match.sets if games_b > games_a)
        if sets_a == sets_b:
            continue
        return match.team_a_id if sets_a > sets_b else match.team_b_id
    return None


def get_standings(session: Session, zone_id: int) -> list[StandingRow]:
    """Load one zone's teams and played matches, then delegate the calculation."""
    teams = list(session.exec(select(Team).where(Team.zone_id == zone_id)).all())
    team_ids = {team.id for team in teams}
    if not team_ids:
        return []

    matches = session.exec(
        select(Match).where(
            Match.status == MatchStatus.PLAYED,
            Match.team_a_id.in_(team_ids),
        )
    ).all()

    # One query for every set, instead of one query per match.
    all_sets = session.exec(
        select(MatchSet)
        .where(MatchSet.match_id.in_([match.id for match in matches]))
        .order_by(MatchSet.set_number)
    ).all()

    sets_by_match: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for match_set in all_sets:
        sets_by_match[match_set.match_id].append(
            (match_set.team_a_games, match_set.team_b_games)
        )

    played = [
        PlayedMatch(
            team_a_id=match.team_a_id,
            team_b_id=match.team_b_id,
            sets=sets_by_match[match.id],
        )
        for match in matches
    ]

    return calculate_standings(teams, played)
