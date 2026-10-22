"""Saved-score calculations, isolated from the application's conftest."""

from dataclasses import replace

import pytest

from app.americanos.fixture import AmericanoDomainError
from app.americanos.standings import SavedScore, StandingRegistration, calculate_standings


def registration(id, order=None, zone=51):
    return StandingRegistration(id, zone, f'P{id}', f'Q{id}', id if order is None else order)


def test_win_then_zero_zero_draw_uses_exact_half_units():
    registrations = [registration(i) for i in (1, 2, 3)]
    scores = [SavedScore(11, 51, 1, 2, 5, 3), SavedScore(12, 51, 1, 3, 0, 0)]
    zones = calculate_standings(registrations, scores)
    assert len(zones) == 1
    assert zones[0].zone_id == 51
    rows = [row for block in zones[0].blocks for row in block.rows]
    assert [r.registration.id for r in rows] == [1, 3, 2]
    assert [(r.played, r.won, r.drawn, r.lost, r.games_for, r.games_against,
             r.games_diff, r.points_half_units) for r in rows] == [
        (2, 1, 1, 0, 5, 3, 2, 3), (1, 0, 1, 0, 0, 0, 0, 1),
        (1, 0, 0, 1, 3, 5, -2, 0),
    ]


def test_tied_block_ignores_head_to_head_and_id_but_keeps_registration_order():
    registrations = [registration(9, 1), registration(2, 2), registration(5, 3)]
    scores = [SavedScore(11, 51, 9, 2, 1, 0), SavedScore(12, 51, 2, 5, 1, 0),
              SavedScore(13, 51, 5, 9, 1, 0)]
    blocks = calculate_standings(registrations, scores)[0].blocks
    assert len(blocks) == 1
    assert (blocks[0].position_from, blocks[0].position_to, blocks[0].points_half_units, blocks[0].games_diff) == (1, 3, 2, 0)
    assert [r.registration.id for r in blocks[0].rows] == [9, 2, 5]


def test_difference_is_second_criterion_and_zero_rows_remain_in_separate_zones():
    registrations = [registration(i) for i in (1, 2, 3, 4, 5)] + [registration(6, zone=23)]
    zones = calculate_standings(registrations, [SavedScore(1, 51, 1, 3, 2, 0), SavedScore(2, 51, 2, 4, 9, 0)])
    assert [z.zone_id for z in zones] == [23, 51]
    assert [b.rows[0].registration.id for b in zones[1].blocks] == [2, 1, 5, 3, 4]
    zero = zones[0].blocks[0].rows[0]
    assert (zero.played, zero.points_half_units, zero.games_diff) == (0, 0, 0)
    assert calculate_standings([], []) == ()


def test_replacing_saved_score_recalculates_instead_of_accumulating():
    registrations = [registration(1), registration(2)]
    original = [SavedScore(1, 51, 1, 2, 5, 3)]
    before = calculate_standings(registrations, original)
    corrected = calculate_standings(registrations, [replace(original[0], games_a=0, games_b=0)])
    assert before[0].blocks[0].rows[0].points_half_units == 2
    assert len(corrected[0].blocks) == 1
    assert [(r.played, r.drawn, r.points_half_units, r.games_diff) for r in corrected[0].blocks[0].rows] == [(1, 1, 1, 0)] * 2
    assert calculate_standings(registrations, original) == before


@pytest.mark.parametrize('score', [
    SavedScore(1, 51, 1, 2, None, 0), SavedScore(1, 51, 1, 2, 0, None),
    SavedScore(1, 51, 1, 2, True, 0), SavedScore(1, 51, 1, 2, 0, 1.0),
    SavedScore(1, 51, 1, 2, -1, 0), SavedScore(1, 51, 1, 2, 0, 10),
    SavedScore(1, 51, 1, 2, '0', 0), SavedScore(True, 51, 1, 2, 0, 0),
    SavedScore(1, 51, 1, 1, 0, 0), SavedScore(1, 51, 1, 99, 0, 0),
    SavedScore(1, 99, 1, 2, 0, 0), SavedScore(1, True, 1, 2, 0, 0),
    SavedScore(1, 51, True, 2, 0, 0),
])
def test_invalid_or_incomplete_saved_score_is_rejected(score):
    with pytest.raises(AmericanoDomainError) as caught:
        calculate_standings([registration(1), registration(2)], [score])
    assert caught.value.code == 'invalid_configuration'


@pytest.mark.parametrize('scores', [
    [SavedScore(1, 51, 1, 2, 0, 0), SavedScore(1, 51, 1, 3, 1, 0)],
    [SavedScore(1, 51, 1, 2, 0, 0), SavedScore(2, 51, 2, 1, 1, 0)],
])
def test_duplicate_match_or_unordered_pair_is_rejected(scores):
    with pytest.raises(AmericanoDomainError):
        calculate_standings([registration(1), registration(2), registration(3)], scores)


@pytest.mark.parametrize('registrations', [
    [registration(1), registration(1)], [registration(1), registration(2, order=1)],
    [registration(True)], [registration(1, order=0)], [registration(1, order=True)],
    [registration(1, zone=0)], [registration(1, zone=1.0)],
])
def test_invalid_registration_identity_or_order_is_rejected(registrations):
    with pytest.raises(AmericanoDomainError):
        calculate_standings(registrations, [])


def test_cross_zone_score_is_rejected():
    with pytest.raises(AmericanoDomainError):
        calculate_standings([registration(1), registration(2, zone=23)], [SavedScore(1, 51, 1, 2, 1, 0)])


def test_points_precede_difference_even_when_a_loser_has_better_difference():
    zones = calculate_standings([registration(i) for i in range(1, 5)], [
        SavedScore(1, 51, 1, 3, 1, 0), SavedScore(2, 51, 1, 4, 1, 0), SavedScore(3, 51, 1, 2, 0, 9),
    ])
    rows = [row for block in zones[0].blocks for row in block.rows]
    assert [(r.registration.id, r.points_half_units, r.games_diff) for r in rows] == [
        (1, 4, -7), (2, 2, 9), (3, 0, -1), (4, 0, -1),
    ]


@pytest.mark.parametrize('games,expected', [((5, 3), (2, 0)), ((3, 5), (0, 2)), ((0, 0), (1, 1)), ((9, 9), (1, 1))])
def test_scoring_is_symmetric_and_draw_half_units_are_integers(games, expected):
    zones = calculate_standings([registration(1), registration(2)], [SavedScore(1, 51, 1, 2, *games)])
    units = {r.registration.id: r.points_half_units for block in zones[0].blocks for r in block.rows}
    assert (units[1], units[2]) == expected
    assert all(type(value) is int for value in units.values())
