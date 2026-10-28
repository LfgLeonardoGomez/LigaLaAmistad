"""Deterministic intra-zone Berger rounds and global court-capacity splitting."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

StartStage = Literal['quarterfinal', 'semifinal', 'final']
ZoneLabel = Literal['A', 'B']
Side = Literal['a', 'b']
RestReason = Literal['bye', 'capacity', 'zone_finished']


class AmericanoDomainError(ValueError):
    def __init__(self, code: str, message: str, path: tuple[str | int, ...] = ()):
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path


def _positive_integer(value: object, path: tuple[str | int, ...]) -> None:
    if type(value) is not int or not 1 <= value <= 2**53 - 1:
        raise AmericanoDomainError('invalid_configuration', 'Expected a positive JSON-safe integer.', path)


@dataclass(frozen=True)
class Pairing:
    registration_a_id: int
    registration_b_id: int


@dataclass(frozen=True)
class LogicalRound:
    number: int
    pairings: tuple[Pairing, ...]
    bye_registration_id: int | None


@dataclass(frozen=True)
class ZoneInput:
    zone_id: int
    label: ZoneLabel
    registration_ids: tuple[int, ...]


@dataclass(frozen=True)
class FixtureMatch:
    zone_id: int
    registration_a_id: int
    registration_b_id: int
    display_order: int
    court_number: int


@dataclass(frozen=True)
class Rest:
    zone_id: int
    registration_id: int
    reason: RestReason


@dataclass(frozen=True)
class FixtureRound:
    number: int
    matches: tuple[FixtureMatch, ...]
    resting: tuple[Rest, ...]


def zone_pairings(registration_ids: Sequence[int]) -> tuple[LogicalRound, ...]:
    """Keep the first registration fixed and rotate others right, including odd byes."""
    for index, registration_id in enumerate(registration_ids):
        _positive_integer(registration_id, ('registration_ids', index))
    if len(set(registration_ids)) != len(registration_ids):
        raise AmericanoDomainError(
            'invalid_configuration', 'Registration IDs must be unique.', ('registration_ids',),
        )
    if len(registration_ids) < 2:
        return ()
    rotation: list[int | None] = list(registration_ids)
    if len(rotation) % 2:
        rotation.append(None)
    rounds = []
    for number in range(1, len(rotation)):
        pairs = []
        bye = None
        for a, b in zip(rotation[:len(rotation) // 2], reversed(rotation)):
            if a is None or b is None:
                bye = b if a is None else a
            else:
                pairs.append(Pairing(min(a, b), max(a, b)))
        rounds.append(LogicalRound(number, tuple(pairs), bye))
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    return tuple(rounds)


def _validate_zones(zones: Sequence[ZoneInput]) -> None:
    seen_zones = set()
    seen_labels = set()
    seen_registrations = set()
    for index, zone in enumerate(zones):
        _positive_integer(zone.zone_id, ('zones', index, 'zone_id'))
        if (zone.label not in ('A', 'B') or zone.label in seen_labels
                or zone.zone_id in seen_zones):
            raise AmericanoDomainError(
                'invalid_configuration', 'Zones and labels must be unique A/B.', ('zones', index),
            )
        for registration_id in zone.registration_ids:
            _positive_integer(registration_id, ('zones', index, 'registration_ids'))
            if registration_id in seen_registrations:
                raise AmericanoDomainError(
                    'invalid_configuration', 'Registration belongs to more than one slot.',
                    ('zones', index, 'registration_ids'),
                )
            seen_registrations.add(registration_id)
        seen_zones.add(zone.zone_id)
        seen_labels.add(zone.label)


def build_fixture(
    zones: Sequence[ZoneInput], capacity: int = 6, *, courts: Sequence[int] | None = None,
) -> tuple[FixtureRound, ...]:
    """Merge equal Berger indices before splitting; never pack across logical blocks."""
    if type(capacity) is not int or not 1 <= capacity <= 6:
        raise AmericanoDomainError(
            'invalid_configuration', 'Court capacity must be an integer from 1 to 6.', ('capacity',),
        )
    available = tuple(range(1, capacity + 1)) if courts is None else tuple(courts)
    if (not 1 <= len(available) <= 6 or any(type(c) is not int or not 1 <= c <= 6 for c in available)
            or len(set(available)) != len(available)):
        raise AmericanoDomainError(
            'invalid_configuration', 'Select unique courts from 1 to 6.', ('courts',),
        )
    available = tuple(sorted(available))
    capacity = len(available)
    _validate_zones(zones)
    ordered_zones = sorted(zones, key=lambda z: z.label)
    schedules = {z.zone_id: zone_pairings(z.registration_ids) for z in ordered_zones}
    rounds = []
    for index in range(max((len(rs) for rs in schedules.values()), default=0)):
        block = [
            (z.zone_id, p)
            for z in ordered_zones if index < len(schedules[z.zone_id])
            for p in schedules[z.zone_id][index].pairings
        ]
        if courts is not None and capacity < 6:
            # Share reduced capacity between zones instead of leaving all of B
            # idle while scheduling all of A. Keep the historical six-court
            # ordering so deployed fixtures can still be reconstructed exactly.
            active = [(z.zone_id, schedules[z.zone_id][index].pairings)
                      for z in ordered_zones if index < len(schedules[z.zone_id])]
            block = [(zone_id, pairings[slot])
                     for slot in range(max((len(pairings) for _, pairings in active), default=0))
                     for zone_id, pairings in active if slot < len(pairings)]
        for offset in range(0, len(block), capacity):
            matches = tuple(
                FixtureMatch(zone_id, p.registration_a_id, p.registration_b_id, order, available[order - 1])
                for order, (zone_id, p) in enumerate(block[offset:offset + capacity], 1)
            )
            playing = {i for m in matches for i in (m.registration_a_id, m.registration_b_id)}
            resting = []
            for zone in ordered_zones:
                schedule = schedules[zone.zone_id]
                logical = schedule[index] if index < len(schedule) else None
                for registration_id in zone.registration_ids:
                    if registration_id not in playing:
                        reason = 'zone_finished' if logical is None else (
                            'bye' if registration_id == logical.bye_registration_id else 'capacity'
                        )
                        resting.append(Rest(zone.zone_id, registration_id, reason))
            rounds.append(FixtureRound(len(rounds) + 1, matches, tuple(resting)))
    return tuple(rounds)
