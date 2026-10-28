"""Pure fixture contracts; run with --noconftest (no application/database)."""

from collections import Counter
from itertools import combinations

import pytest

from app.americanos.fixture import AmericanoDomainError, Pairing, ZoneInput, build_fixture, zone_pairings


@pytest.mark.parametrize('courts', [[1, 2, 3], [3, 4, 5, 6], [1, 2, 3, 4, 5, 6]])
def test_seven_pairs_have_exactly_one_rest_each_and_play_every_rival(courts):
    ids = tuple(range(1, 8))
    fixture = build_fixture([ZoneInput(1, 'A', ids)], courts=courts)
    assert len(fixture) == 7
    matches = [match for round_ in fixture for match in round_.matches]
    assert len(matches) == 21
    assert Counter(rest.registration_id for round_ in fixture for rest in round_.resting) == Counter({id_: 1 for id_ in ids})
    assert all(rest.reason == 'bye' for round_ in fixture for rest in round_.resting)
    actual = [(match.registration_a_id, match.registration_b_id) for match in matches]
    assert Counter(actual) == Counter(combinations(ids, 2))
    assert Counter(id_ for pair in actual for id_ in pair) == Counter({id_: 6 for id_ in ids})


@pytest.mark.parametrize('size', range(2, 26))
def test_logical_rounds_never_repeat_a_bye_and_cover_every_pair(size):
    ids = tuple(range(1, size + 1))
    logical = zone_pairings(ids)
    byes = Counter(round_.bye_registration_id for round_ in logical if round_.bye_registration_id is not None)
    assert byes == (Counter({id_: 1 for id_ in ids}) if size % 2 else Counter())
    assert Counter((pair.registration_a_id, pair.registration_b_id) for round_ in logical for pair in round_.pairings) == Counter(combinations(ids, 2))


@pytest.mark.parametrize('courts', [[6], [3, 6]])
def test_seven_pairs_need_repeated_capacity_rests_when_courts_are_insufficient(courts):
    ids = tuple(range(1, 8))
    fixture = build_fixture([ZoneInput(1, 'A', ids)], courts=courts)
    appearances = Counter(id_ for round_ in fixture for match in round_.matches
                          for id_ in (match.registration_a_id, match.registration_b_id))
    assert appearances == Counter({id_: 6 for id_ in ids})
    rests = Counter(rest.registration_id for round_ in fixture for rest in round_.resting)
    assert all(rests[id_] == len(fixture) - 6 for id_ in ids)
    assert all(rests[id_] > 1 for id_ in ids)
    assert any(rest.reason == 'capacity' for round_ in fixture for rest in round_.resting)


def test_berger_keeps_registration_order_and_canonicalizes_sides():
    rounds = zone_pairings([40, 10, 30, 20])

    assert [r.number for r in rounds] == [1, 2, 3]
    assert [r.pairings for r in rounds] == [
        (Pairing(20, 40), Pairing(10, 30)),
        (Pairing(30, 40), Pairing(10, 20)),
        (Pairing(10, 40), Pairing(20, 30)),
    ]
    assert [r.bye_registration_id for r in rounds] == [None, None, None]


@pytest.mark.parametrize('size', [0, 1, 2, 5, 7, 8, 16, 17])
def test_berger_all_pairs_once_with_odd_byes_and_no_empty_rounds(size):
    ids = list(range(1, size + 1))
    rounds = zone_pairings(ids)
    assert len(rounds) == (0 if size < 2 else size - 1 + size % 2)
    pairs = [p for r in rounds for p in r.pairings]
    assert sorted((p.registration_a_id, p.registration_b_id) for p in pairs) == list(combinations(ids, 2))
    if size >= 2:
        for r in rounds:
            playing = [i for p in r.pairings for i in (p.registration_a_id, p.registration_b_id)]
            assert len(playing) == len(set(playing)) == size - size % 2
            assert set(ids) - set(playing) == ({r.bye_registration_id} if size % 2 else set())
        if size % 2:
            assert sorted(r.bye_registration_id for r in rounds) == ids


@pytest.mark.parametrize('ids', [[1, 1], [True, 2], [1.0, 2], [0, 2], [-1, 2], ['1', 2], [2**53, 2]])
def test_berger_rejects_invalid_ids(ids):
    with pytest.raises(AmericanoDomainError) as caught:
        zone_pairings(ids)
    assert caught.value.code == 'invalid_configuration'
    assert caught.value.message
    assert caught.value.path[0] == 'registration_ids'


def test_global_fixture_eight_pairs_has_seven_rounds_of_four():
    zone = ZoneInput(51, 'A', tuple(range(1, 9)))
    rounds = build_fixture([zone])
    assert [r.number for r in rounds] == list(range(1, 8))
    assert [len(r.matches) for r in rounds] == [4] * 7
    assert [m.display_order for m in rounds[0].matches] == [1, 2, 3, 4]
    assert all(r.resting == () for r in rounds)


@pytest.mark.parametrize('sizes,expected_counts', [
    ((7, 7), [6] * 7), ((16,), [6, 2] * 15),
    ((5, 4), [4, 4, 4, 2, 2]), ((8, 8), [6, 2] * 7),
    ((1, 4), [2] * 3), ((1, 1), []), ((0,), []), ((9, 9), [6, 2] * 9),
])
def test_global_coverage_capacity_and_explicit_rest_reasons(sizes, expected_counts):
    zones = []
    next_id = 1
    for index, size in enumerate(sizes):
        zones.append(ZoneInput(51 + index, 'AB'[index], tuple(range(next_id, next_id + size))))
        next_id += size
    original = list(zones)
    rounds = build_fixture(list(reversed(zones)))
    assert [len(r.matches) for r in rounds] == expected_counts
    assert build_fixture(zones) == rounds
    assert zones == original
    expected = {(z.zone_id, a, b) for z in zones for a, b in combinations(z.registration_ids, 2)}
    actual = [(m.zone_id, m.registration_a_id, m.registration_b_id) for r in rounds for m in r.matches]
    assert len(actual) == len(expected)
    assert set(actual) == expected
    logical = {z.zone_id: zone_pairings(z.registration_ids) for z in zones}
    actual_index = 0
    for index in range(max((len(rs) for rs in logical.values()), default=0)):
        block = [(z.zone_id, p.registration_a_id, p.registration_b_id)
                 for z in zones if index < len(logical[z.zone_id])
                 for p in logical[z.zone_id][index].pairings]
        for offset in range(0, len(block), 6):
            r = rounds[actual_index]
            actual_index += 1
            assert [(m.zone_id, m.registration_a_id, m.registration_b_id) for m in r.matches] == block[offset:offset + 6]
            assert [m.display_order for m in r.matches] == list(range(1, len(r.matches) + 1))
            playing = [i for m in r.matches for i in (m.registration_a_id, m.registration_b_id)]
            assert len(playing) == len(set(playing))
            rests = {(rest.zone_id, rest.registration_id): rest.reason for rest in r.resting}
            expected_rests = {}
            for z in zones:
                for registration_id in z.registration_ids:
                    if registration_id not in playing:
                        if index >= len(logical[z.zone_id]):
                            reason = 'zone_finished'
                        elif logical[z.zone_id][index].bye_registration_id == registration_id:
                            reason = 'bye'
                        else:
                            reason = 'capacity'
                        expected_rests[z.zone_id, registration_id] = reason
            assert rests == expected_rests
            assert len(r.resting) == len(expected_rests)


@pytest.mark.parametrize('capacity', [1, 2, 5])
def test_smaller_capacity_splits_without_combining_logical_blocks(capacity):
    rounds = build_fixture([ZoneInput(51, 'A', (9, 3, 7, 1))], capacity)
    assert [len(r.matches) for r in rounds] == ([1, 1] * 3 if capacity == 1 else [2] * 3)
    assert len({(m.registration_a_id, m.registration_b_id) for r in rounds for m in r.matches}) == 6


@pytest.mark.parametrize('capacity', [0, 7, True, 1.0, '6'])
def test_invalid_capacity_rejected(capacity):
    with pytest.raises(AmericanoDomainError, match='capacity'):
        build_fixture([ZoneInput(51, 'A', (1, 2))], capacity)


@pytest.mark.parametrize('zones', [
    [ZoneInput(51, 'A', (1, 2)), ZoneInput(51, 'B', (3, 4))],
    [ZoneInput(51, 'A', (1, 2)), ZoneInput(52, 'B', (2, 3))],
    [ZoneInput(51, 'A', (1, 2)), ZoneInput(52, 'A', (3, 4))],
    [ZoneInput(True, 'A', (1, 2))], [ZoneInput(51, 'C', (1, 2))],
    [ZoneInput(51, 'A', (1, 1))],
])
def test_invalid_zone_configuration_rejected(zones):
    with pytest.raises(AmericanoDomainError) as caught:
        build_fixture(zones)
    assert caught.value.code == 'invalid_configuration'
