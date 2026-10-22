"""Human tie selections are IDs, never a hidden sporting tiebreak."""

import pytest

from app.americanos.fixture import AmericanoDomainError
from app.americanos.qualification import (
    ResolvedSeed, SeedRef, TieResolution, qualification_preview, qualification_quotas,
)


def test_quarterfinal_quotas_use_real_zone_ids():
    assert qualification_quotas('quarterfinal', [51, 23]) == {51: 4, 23: 4}


@pytest.mark.parametrize('stage,total', [('quarterfinal', 8), ('semifinal', 4), ('final', 2)])
@pytest.mark.parametrize('zones', [[51], [51, 23]])
def test_all_six_stage_zone_configurations(stage, total, zones):
    assert qualification_quotas(stage, zones) == {z: total // len(zones) for z in zones}


@pytest.mark.parametrize('stage,zones', [
    ('semi', [51]), ('final', []), ('final', [51, 23, 18]), ('final', [51, 51]),
    ('final', [True]), ('final', [1.0]), ('final', [0]), ('final', ['51']),
])
def test_invalid_quota_configuration_rejected(stage, zones):
    with pytest.raises(AmericanoDomainError) as caught:
        qualification_quotas(stage, zones)
    assert caught.value.code == 'invalid_configuration'


def zone_blocks(groups, zone=51):
    from app.americanos.standings import StandingBlock, StandingRegistration, StandingRow, ZoneStanding

    blocks = []
    position = 1
    for index, group in enumerate(groups):
        units = 2 * (len(groups) - index)
        rows = tuple(StandingRow(StandingRegistration(id, zone, f'P{id}', f'Q{id}', position + offset),
                                 0, 0, 0, 0, 0, 0, 0, units)
                     for offset, id in enumerate(group))
        blocks.append(StandingBlock(position, position + len(rows) - 1, units, 0, rows))
        position += len(rows)
    return ZoneStanding(zone, tuple(blocks))


def test_three_tied_for_two_slots_do_not_resolve_eliminated_position():
    blocks = [zone_blocks([(1,), (2,), (3, 4, 5)])]
    preview = qualification_preview(blocks, {51: 4}, [TieResolution(51, 3, 4), TieResolution(51, 4, 3)])
    assert [(s.position, s.candidate_registration_ids, s.registration_id, s.requires_resolution) for s in preview.slots] == [
        (1, (1,), 1, False), (2, (2,), 2, False),
        (3, (3, 4, 5), 4, True), (4, (3, 4, 5), 3, True),
    ]
    assert preview.missing_slots == ()
    assert preview.resolved_seeds == tuple(ResolvedSeed(51, pos, id) for pos, id in enumerate((1, 2, 4, 3), 1))


@pytest.mark.parametrize('groups,quota,missing', [
    ([(9, 2), (3,), (4,)], 4, [1, 2]),
    ([(1,), (9, 2)], 2, [2]),
    ([(9, 2, 3)], 2, [1, 2]),
    ([(1,), (2,), (3,), (4,), (5,), (6, 7, 8)], 4, []),
])
def test_only_relevant_ties_need_selection_without_visual_seeding(groups, quota, missing):
    preview = qualification_preview([zone_blocks(groups)], {51: quota}, [])
    assert [s.position for s in preview.slots] == list(range(1, quota + 1))
    assert preview.missing_slots == tuple(SeedRef(51, p) for p in missing)
    assert [s.position for s in preview.resolved_seeds] == [p for p in range(1, quota + 1) if p not in missing]
    assert all(s.registration_id is None for s in preview.slots if s.position in missing)


def test_partial_resolution_retains_full_candidate_block_and_reports_remaining():
    preview = qualification_preview([zone_blocks([(9, 2, 3)])], {51: 2}, [TieResolution(51, 1, 3)])
    assert preview.missing_slots == (SeedRef(51, 2),)
    assert preview.resolved_seeds == (ResolvedSeed(51, 1, 3),)
    assert [s.candidate_registration_ids for s in preview.slots] == [(9, 2, 3)] * 2
    assert [s.requires_resolution for s in preview.slots] == [True, True]
    # Recomputed current blocks no longer contain that tie: stale selections cannot survive.
    with pytest.raises(AmericanoDomainError) as caught:
        qualification_preview([zone_blocks([(9,), (2,), (3,)])], {51: 2}, [TieResolution(51, 1, 3)])
    assert caught.value.code == 'invalid_tie_resolution'


def test_two_single_person_zones_resolve_without_games_in_zone_id_order():
    preview = qualification_preview([zone_blocks([(9,)], 51), zone_blocks([(2,)], 23)], {51: 1, 23: 1}, [])
    assert preview.resolved_seeds == (ResolvedSeed(23, 1, 2), ResolvedSeed(51, 1, 9))
    assert preview.missing_slots == ()


@pytest.mark.parametrize('resolutions', [
    [TieResolution(51, 3, 3), TieResolution(51, 4, 3)],
    [TieResolution(51, 3, 3), TieResolution(51, 3, 4)],
    [TieResolution(51, 3, 99)], [TieResolution(51, 3, 1)],
    [TieResolution(51, 5, 5)], [TieResolution(51, 1, 1)],
    [TieResolution(23, 3, 3)], [TieResolution(51, True, 3)],
    [TieResolution(51, 3, True)], [TieResolution(51.0, 3, 3)],
    [TieResolution(51, 3.0, 3)], [TieResolution(51, 3, 3.0)], [TieResolution(51, 3, 2**53)],
])
def test_duplicate_outside_irrelevant_or_noninteger_resolution_rejected(resolutions):
    with pytest.raises(AmericanoDomainError) as caught:
        qualification_preview([zone_blocks([(1,), (2,), (3, 4, 5)])], {51: 4}, resolutions)
    assert caught.value.code == 'invalid_tie_resolution'
    assert caught.value.path[0] == 'resolutions'


@pytest.mark.parametrize('blocks,quotas', [
    ([zone_blocks([(1,), (2,), (3,)])], {51: 4}),
    ([zone_blocks([(1,), (2,), (3,)], 51), zone_blocks([(4,), (5,), (6,), (7,), (8,)], 23)], {51: 4, 23: 4}),
    ([zone_blocks([(1,), (2,)])], {23: 2}),
    ([zone_blocks([(1,), (2,)])], {51: True}),
    ([zone_blocks([(1,), (2,)])], {51: 0}),
    ([zone_blocks([(1,), (2,)])], {51: 2.0}),
    ([zone_blocks([(1,), (2,)])], {51.0: 2}),
    ([zone_blocks([(1,), (2,)]), zone_blocks([(3,), (4,)])], {51: 2}),
    ([zone_blocks([(1,), (1,)])], {51: 2}),
])
def test_insufficient_or_invalid_preview_configuration_rejected(blocks, quotas):
    with pytest.raises(AmericanoDomainError) as caught:
        qualification_preview(blocks, quotas, [])
    assert caught.value.code == 'invalid_configuration'


@pytest.mark.parametrize('change', [
    {'position_from': 2}, {'position_to': 3}, {'position_from': True},
    {'position_to': 2.0}, {'rows': ()},
])
def test_inconsistent_block_position_ranges_are_rejected(change):
    from dataclasses import replace

    zone = zone_blocks([(9, 2)])
    broken = replace(zone, blocks=(replace(zone.blocks[0], **change),))
    with pytest.raises(AmericanoDomainError) as caught:
        qualification_preview([broken], {51: 2}, [])
    assert caught.value.code == 'invalid_configuration'


def test_inconsistent_row_zone_is_rejected_even_when_numeric_equality_matches():
    from dataclasses import replace

    zone = zone_blocks([(9, 2)])
    row = zone.blocks[0].rows[0]
    row = replace(row, registration=replace(row.registration, zone_id=51.0))
    broken = replace(zone, blocks=(replace(zone.blocks[0], rows=(row, zone.blocks[0].rows[1])),))
    with pytest.raises(AmericanoDomainError):
        qualification_preview([broken], {51: 2}, [])


@pytest.mark.parametrize('kind', ['row_points', 'row_difference', 'split_tie', 'inverted_order', 'fractional_points'])
def test_malformed_sporting_blocks_cannot_silently_create_firm_seeds(kind):
    from dataclasses import replace

    zone = zone_blocks([(9, 2)])
    block = zone.blocks[0]
    first, second = block.rows
    if kind == 'row_points':
        blocks = (replace(block, rows=(replace(first, points_half_units=3), second)),)
    elif kind == 'row_difference':
        blocks = (replace(block, rows=(replace(first, games_diff=1), second)),)
    elif kind == 'fractional_points':
        blocks = (replace(block, points_half_units=2.0),)
    else:
        a = replace(block, position_to=1, rows=(first,))
        b = replace(block, position_from=2, rows=(second,))
        if kind == 'inverted_order':
            b = replace(b, points_half_units=3, rows=(replace(second, points_half_units=3),))
        blocks = (a, b)
    with pytest.raises(AmericanoDomainError) as caught:
        qualification_preview([replace(zone, blocks=blocks)], {51: 2}, [])
    assert caught.value.code == 'invalid_configuration'
