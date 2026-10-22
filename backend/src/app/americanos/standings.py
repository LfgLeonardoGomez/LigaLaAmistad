"""Recompute exact half-unit standings from complete saved group scores."""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import groupby

from app.americanos.fixture import AmericanoDomainError, _positive_integer


@dataclass(frozen=True)
class StandingRegistration:
    id: int
    zone_id: int
    player1_name: str
    player2_name: str
    registration_order: int


@dataclass(frozen=True)
class SavedScore:
    match_id: int
    zone_id: int
    registration_a_id: int
    registration_b_id: int
    games_a: int
    games_b: int


@dataclass(frozen=True)
class StandingRow:
    registration: StandingRegistration
    played: int
    won: int
    drawn: int
    lost: int
    games_for: int
    games_against: int
    games_diff: int
    points_half_units: int


@dataclass(frozen=True)
class StandingBlock:
    position_from: int
    position_to: int
    points_half_units: int
    games_diff: int
    rows: tuple[StandingRow, ...]


@dataclass(frozen=True)
class ZoneStanding:
    zone_id: int
    blocks: tuple[StandingBlock, ...]


class _Metrics:
    """Private per-call accumulators; none escape into immutable output rows."""

    def __init__(self) -> None:
        self.won = 0
        self.drawn = 0
        self.lost = 0
        self.games_for = 0
        self.games_against = 0


def _validate_inputs(
    registrations: Sequence[StandingRegistration], saved_scores: Sequence[SavedScore],
) -> None:
    by_id = {}
    orders = set()
    for index, registration in enumerate(registrations):
        for field in ('id', 'zone_id', 'registration_order'):
            _positive_integer(getattr(registration, field), ('registrations', index, field))
        if registration.id in by_id or registration.registration_order in orders:
            raise AmericanoDomainError(
                'invalid_configuration', 'Registration IDs and orders must be unique.',
                ('registrations', index),
            )
        by_id[registration.id] = registration
        orders.add(registration.registration_order)
    seen_matches = set()
    seen_pairs = set()
    for index, score in enumerate(saved_scores):
        for field in ('match_id', 'zone_id', 'registration_a_id', 'registration_b_id'):
            _positive_integer(getattr(score, field), ('saved_scores', index, field))
        for field in ('games_a', 'games_b'):
            value = getattr(score, field)
            if type(value) is not int or not 0 <= value <= 9:
                raise AmericanoDomainError(
                    'invalid_configuration', 'Saved games must be complete integers from 0 to 9.',
                    ('saved_scores', index, field),
                )
        a, b = score.registration_a_id, score.registration_b_id
        pair = tuple(sorted((a, b)))
        if score.match_id in seen_matches or pair in seen_pairs:
            raise AmericanoDomainError(
                'invalid_configuration', 'Duplicate saved match or pairing.', ('saved_scores', index),
            )
        if a == b or any(i not in by_id or by_id[i].zone_id != score.zone_id for i in (a, b)):
            raise AmericanoDomainError(
                'invalid_configuration', 'Saved match must reference two registrations in its zone.',
                ('saved_scores', index),
            )
        seen_matches.add(score.match_id)
        seen_pairs.add(pair)


def calculate_standings(
    registrations: Sequence[StandingRegistration], saved_scores: Sequence[SavedScore],
) -> tuple[ZoneStanding, ...]:
    """Use current saved scores only; visual row order never breaks a sporting tie."""
    _validate_inputs(registrations, saved_scores)
    metrics = {r.id: _Metrics() for r in registrations}
    for score in saved_scores:
        for own_id, own, other in (
            (score.registration_a_id, score.games_a, score.games_b),
            (score.registration_b_id, score.games_b, score.games_a),
        ):
            values = metrics[own_id]
            values.won += own > other
            values.drawn += own == other
            values.lost += own < other
            values.games_for += own
            values.games_against += other
    zones = []
    for zone_id in sorted({r.zone_id for r in registrations}):
        rows = []
        for r in registrations:
            if r.zone_id == zone_id:
                m = metrics[r.id]
                rows.append(StandingRow(
                    r, m.won + m.drawn + m.lost, m.won, m.drawn, m.lost,
                    m.games_for, m.games_against, m.games_for - m.games_against,
                    2 * m.won + m.drawn,
                ))
        rows.sort(key=lambda r: (-r.points_half_units, -r.games_diff, r.registration.registration_order))
        blocks = []
        position = 1
        for (units, diff), tied_rows in groupby(rows, key=lambda r: (r.points_half_units, r.games_diff)):
            tied = tuple(tied_rows)
            blocks.append(StandingBlock(position, position + len(tied) - 1, units, diff, tied))
            position += len(tied)
        zones.append(ZoneStanding(zone_id, tuple(blocks)))
    return tuple(zones)
