"""Zone quotas and explicit resolutions of relevant standing blocks."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.americanos.fixture import AmericanoDomainError, StartStage, _positive_integer
from app.americanos.standings import ZoneStanding


@dataclass(frozen=True)
class SeedRef:
    zone_id: int
    position: int


@dataclass(frozen=True)
class TieResolution:
    zone_id: int
    position: int
    registration_id: int


@dataclass(frozen=True)
class QualificationSlot:
    zone_id: int
    position: int
    candidate_registration_ids: tuple[int, ...]
    registration_id: int | None
    requires_resolution: bool


@dataclass(frozen=True)
class ResolvedSeed:
    zone_id: int
    position: int
    registration_id: int


@dataclass(frozen=True)
class QualificationPreview:
    slots: tuple[QualificationSlot, ...]
    missing_slots: tuple[SeedRef, ...]
    resolved_seeds: tuple[ResolvedSeed, ...]


def qualification_quotas(start_stage: StartStage, zone_ids: Sequence[int]) -> dict[int, int]:
    if start_stage not in ('quarterfinal', 'semifinal', 'final'):
        raise AmericanoDomainError('invalid_configuration', 'Unknown start stage.', ('start_stage',))
    if len(zone_ids) not in (1, 2):
        raise AmericanoDomainError('invalid_configuration', 'Exactly one or two zones are required.', ('zone_ids',))
    for index, zone_id in enumerate(zone_ids):
        _positive_integer(zone_id, ('zone_ids', index))
    if len(set(zone_ids)) != len(zone_ids):
        raise AmericanoDomainError('invalid_configuration', 'Zone IDs must be unique.', ('zone_ids',))
    total = {'quarterfinal': 8, 'semifinal': 4, 'final': 2}[start_stage]
    return {zone_id: total // len(zone_ids) for zone_id in zone_ids}


def _validate_blocks(blocks: Sequence[ZoneStanding], quotas: Mapping[int, int]) -> None:
    if len(quotas) not in (1, 2):
        raise AmericanoDomainError('invalid_configuration', 'Exactly one or two quotas are required.', ('quotas',))
    for zone_id, quota in quotas.items():
        _positive_integer(zone_id, ('quotas', 'zone_id'))
        if type(quota) is not int or quota not in (1, 2, 4, 8):
            raise AmericanoDomainError('invalid_configuration', 'Invalid zone quota.', ('quotas', zone_id))
    seen_zones = set()
    seen_registrations = set()
    for zone in blocks:
        _positive_integer(zone.zone_id, ('blocks', 'zone_id'))
        if zone.zone_id in seen_zones or zone.zone_id not in quotas:
            raise AmericanoDomainError('invalid_configuration', 'Standing zones must match quotas uniquely.', ('blocks',))
        seen_zones.add(zone.zone_id)
        count = 0
        previous_metric = None
        for block in zone.blocks:
            _positive_integer(block.position_from, ('blocks', 'position_from'))
            _positive_integer(block.position_to, ('blocks', 'position_to'))
            if block.position_from != count + 1 or block.position_to != count + len(block.rows) or not block.rows:
                raise AmericanoDomainError('invalid_configuration', 'Standing blocks require contiguous inclusive position ranges.', ('blocks',))
            metric = (block.points_half_units, block.games_diff)
            if (type(block.points_half_units) is not int or block.points_half_units < 0
                    or type(block.games_diff) is not int
                    or (previous_metric is not None and previous_metric <= metric)):
                raise AmericanoDomainError(
                    'invalid_configuration', 'Blocks must be distinct and ordered by integer points/difference.',
                    ('blocks',),
                )
            previous_metric = metric
            for row in block.rows:
                registration_id = row.registration.id
                _positive_integer(registration_id, ('blocks', 'registration_id'))
                _positive_integer(row.registration.zone_id, ('blocks', 'registration', 'zone_id'))
                if registration_id in seen_registrations or row.registration.zone_id != zone.zone_id:
                    raise AmericanoDomainError('invalid_configuration', 'Standing registrations must belong to one zone.', ('blocks',))
                if (type(row.points_half_units) is not int or type(row.games_diff) is not int
                        or (row.points_half_units, row.games_diff) != metric):
                    raise AmericanoDomainError(
                        'invalid_configuration', 'Each row must have its block sporting metrics.', ('blocks',),
                    )
                seen_registrations.add(registration_id)
                count += 1
        if count < quotas[zone.zone_id]:
            raise AmericanoDomainError('invalid_configuration', 'Insufficient registrations for zone quota.', ('quotas', zone.zone_id))
    if seen_zones != set(quotas):
        raise AmericanoDomainError('invalid_configuration', 'Standing zones must match quotas.', ('blocks',))


def _manual_selections(
    blocks: Sequence[ZoneStanding], quotas: Mapping[int, int], resolutions: Sequence[TieResolution],
) -> dict[tuple[int, int], int]:
    manual_slots = {
        (zone.zone_id, position): tuple(row.registration.id for row in block.rows)
        for zone in blocks for block in zone.blocks if len(block.rows) > 1
        for position in range(block.position_from, min(block.position_to, quotas[zone.zone_id]) + 1)
    }
    selections = {}
    selected_ids = set()
    for index, resolution in enumerate(resolutions):
        key = (resolution.zone_id, resolution.position)
        if any(type(value) is not int or value < 1 for value in (*key, resolution.registration_id)):
            raise AmericanoDomainError('invalid_tie_resolution', 'Resolution IDs and positions must be positive integers.', ('resolutions', index))
        if key not in manual_slots or resolution.registration_id not in manual_slots[key]:
            raise AmericanoDomainError('invalid_tie_resolution', 'Select a candidate for a relevant tied slot.', ('resolutions', index))
        if key in selections or resolution.registration_id in selected_ids:
            raise AmericanoDomainError('invalid_tie_resolution', 'Duplicate resolution slot or registration.', ('resolutions', index))
        selections[key] = resolution.registration_id
        selected_ids.add(resolution.registration_id)
    return selections


def qualification_preview(
    blocks: Sequence[ZoneStanding], quotas: Mapping[int, int], resolutions: Sequence[TieResolution],
) -> QualificationPreview:
    """Accept partial manual selections; expose missing slots without filling ties."""
    _validate_blocks(blocks, quotas)
    selections = _manual_selections(blocks, quotas, resolutions)
    slots = []
    missing = []
    seeds = []
    for zone in sorted(blocks, key=lambda z: z.zone_id):
        for block in zone.blocks:
            candidates = tuple(r.registration.id for r in block.rows)
            for position in range(block.position_from, min(block.position_to, quotas[zone.zone_id]) + 1):
                manual = len(candidates) > 1
                selected = selections.get((zone.zone_id, position)) if manual else candidates[0]
                slots.append(QualificationSlot(zone.zone_id, position, candidates, selected, manual))
                if selected is None:
                    missing.append(SeedRef(zone.zone_id, position))
                else:
                    seeds.append(ResolvedSeed(zone.zone_id, position, selected))
    return QualificationPreview(tuple(slots), tuple(missing), tuple(seeds))
