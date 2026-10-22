"""Pure D8 complete-set validation and conservative bracket propagation."""

from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest

from app.americanos import bracket as domain
from app.americanos.fixture import AmericanoDomainError
from app.americanos.qualification import ResolvedSeed, SeedRef


@pytest.mark.parametrize('a,b,side', [(6, 0, 'a'), (0, 6, 'b')])
def test_complete_set_preserves_zero_and_derives_winner(a, b, side):
    score = domain.FullSetScore(a, b, True)
    result = domain.validate_full_set(score, domain.APPROVED_SET_CONVENTION)
    assert (result.games_a, result.games_b, result.winner_side) == (a, b, side)
    assert (score.games_a, score.games_b, score.set_complete) == (a, b, True)


@pytest.mark.parametrize('a,b', [(5, 3), (3, 5), (6, 5), (5, 6), (8, 6), (6, 8), (0, 0), (6, 6)])
def test_nonterminal_tied_and_long_sets_are_rejected(a, b):
    with pytest.raises(AmericanoDomainError) as caught:
        domain.validate_full_set(domain.FullSetScore(a, b, True), domain.APPROVED_SET_CONVENTION)
    assert caught.value.code == 'invalid_set'


@pytest.mark.parametrize('value', [None, -1, True, False, 6.0, Decimal('6'), '6', '', [], {}])
@pytest.mark.parametrize('side', ['a', 'b'])
def test_games_require_strict_nonnegative_integers(value, side):
    a, b = (value, 0) if side == 'a' else (6, value)
    with pytest.raises(AmericanoDomainError) as caught:
        domain.validate_full_set(domain.FullSetScore(a, b, True), domain.APPROVED_SET_CONVENTION)
    assert caught.value.code == 'invalid_set'
    assert caught.value.path == (f'games_{side}',)


@pytest.mark.parametrize('complete', [False, None, 0, 1, 'true', '', []])
def test_set_must_be_declared_complete_with_literal_true(complete):
    with pytest.raises(AmericanoDomainError) as caught:
        domain.validate_full_set(domain.FullSetScore(6, 4, complete), domain.APPROVED_SET_CONVENTION)
    assert caught.value.code == 'invalid_set'
    assert caught.value.path == ('set_complete',)


@pytest.mark.parametrize('a', range(11))
@pytest.mark.parametrize('b', range(11))
def test_exact_terminal_matrix(a, b):
    terminals = {(6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (7, 5), (7, 6),
                 (0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 7), (6, 7)}
    score = domain.FullSetScore(a, b, True)
    if (a, b) in terminals:
        assert domain.validate_full_set(score, domain.APPROVED_SET_CONVENTION) == domain.ValidatedSet(
            a, b, 'a' if a > b else 'b',
        )
    else:
        with pytest.raises(AmericanoDomainError) as caught:
            domain.validate_full_set(score, domain.APPROVED_SET_CONVENTION)
        assert caught.value.code == 'invalid_set'


@pytest.mark.parametrize('changes', [
    {'tiebreak_at': None, 'tiebreak_winner_games': None}, {'minimum_winner_games': 9},
    {'win_by': 1}, {'win_by': True}, {'minimum_winner_games': 6.0},
    {'tiebreak_at': 6.0}, {'tiebreak_winner_games': 8}, {'key': ''},
])
def test_only_approved_d8_convention_is_available(changes):
    convention = replace(domain.APPROVED_SET_CONVENTION, **changes)
    with pytest.raises(AmericanoDomainError) as caught:
        domain.validate_full_set(domain.FullSetScore(6, 4, True), convention)
    assert caught.value.code == 'invalid_configuration'
    assert caught.value.path == ('convention',)


def make_bracket(stage='semifinal', registration_ids=None):
    pairs = {
        'quarterfinal': ((1, 8), (4, 5), (2, 7), (3, 6)),
        'semifinal': ((1, 4), (2, 3)), 'final': ((1, 2),),
    }[stage]
    template = domain.SeedingTemplate('d6-test', 'approved', stage, 1, tuple(
        domain.OpeningPair(SeedRef(51, a), SeedRef(51, b)) for a, b in pairs
    ))
    if registration_ids is None:
        registration_ids = range(101, 101 + len(pairs) * 2)
    seeds = [ResolvedSeed(51, p, registration_id) for p, registration_id in enumerate(registration_ids, 1)]
    return domain.build_bracket(stage, seeds, template)


def save(nodes, index, a=6, b=0):
    node = nodes[index]
    change = domain.BracketChange(
        domain.NodeRef(node.stage, node.slot),
        domain.validate_full_set(domain.FullSetScore(a, b, True), domain.APPROVED_SET_CONVENTION),
        domain.APPROVED_CORRECTION_POLICY,
    )
    return domain.propagate_winner(nodes, change)


@pytest.mark.parametrize('index,a,b,finalists', [(0, 6, 0, (101, None)), (1, 0, 6, (None, 103))])
def test_semifinal_advances_winner_to_its_stable_side_without_mutating_input(index, a, b, finalists):
    nodes = make_bracket()
    before = tuple(nodes)
    result = save(nodes, index, a, b)
    assert (result.nodes[index].games_a, result.nodes[index].games_b, result.nodes[index].set_complete) == (a, b, True)
    assert (result.nodes[-1].registration_a_id, result.nodes[-1].registration_b_id) == finalists
    assert (result.nodes[-1].games_a, result.nodes[-1].games_b, result.nodes[-1].set_complete) == (None, None, False)
    assert result.champion_registration_id is None
    assert nodes == before
    assert (nodes[index].games_a, nodes[index].games_b) == (None, None)


@pytest.mark.parametrize('a,b', [(None, None), (101, None), (None, 102)])
def test_result_requires_both_participants_known(a, b):
    nodes = (replace(make_bracket('final')[0], registration_a_id=a, registration_b_id=b),)
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 0)
    assert caught.value.code == 'participants_pending'
    assert (nodes[0].games_a, nodes[0].games_b, nodes[0].set_complete) == (None, None, False)


@pytest.mark.parametrize('a,b,correct_a,correct_b,winner', [(6, 0, 0, 6, 102), (0, 6, 7, 5, 101)])
def test_completed_final_is_correctable_and_returns_replacement_champion(a, b, correct_a, correct_b, winner):
    nodes = make_bracket('final')
    completed = save(nodes, 0, a, b)
    assert completed.champion_registration_id == (101 if a > b else 102)
    corrected = save(completed.nodes, 0, correct_a, correct_b)
    assert corrected.champion_registration_id == winner
    assert (corrected.nodes[0].games_a, corrected.nodes[0].games_b, corrected.nodes[0].set_complete) == (correct_a, correct_b, True)
    assert corrected.nodes[0].next is None
    assert (completed.nodes[0].games_a, completed.nodes[0].games_b) == (a, b)
    assert (nodes[0].games_a, nodes[0].games_b) == (None, None)


@pytest.mark.parametrize('index', [0, 1])
@pytest.mark.parametrize('a,b', [(0, 6), (7, 6)])
def test_correction_without_played_descendants_preserves_other_finalist(index, a, b):
    nodes = save(save(make_bracket(), 0).nodes, 1).nodes
    old = nodes[index]
    expected = old.registration_a_id if a > b else old.registration_b_id
    result = save(nodes, index, a, b)
    final = result.nodes[-1]
    assert (final.registration_a_id, final.registration_b_id) == (
        expected if index == 0 else 101, expected if index == 1 else 102,
    )
    assert result.nodes[1 - index] == nodes[1 - index]
    assert (result.nodes[index].games_a, result.nodes[index].games_b) == (a, b)
    assert (nodes[index].games_a, nodes[index].games_b) == (6, 0)
    assert (nodes[-1].registration_a_id, nodes[-1].registration_b_id) == (101, 102)
    assert result.champion_registration_id is None


@pytest.mark.parametrize('index', [0, 1])
@pytest.mark.parametrize('a,b', [(6, 0), (7, 5), (0, 6)])
def test_any_correction_is_blocked_when_final_has_played_even_same_or_identical_winner(index, a, b):
    nodes = save(save(make_bracket(), 0).nodes, 1).nodes
    completed = save(nodes, 2, 0, 6)
    with pytest.raises(AmericanoDomainError) as caught:
        save(completed.nodes, index, a, b)
    assert caught.value.code == 'descendant_played'
    assert completed.champion_registration_id == 102
    assert (completed.nodes[2].games_a, completed.nodes[2].games_b) == (0, 6)
    assert (completed.nodes[index].games_a, completed.nodes[index].games_b) == (6, 0)


@pytest.mark.parametrize('index', [0, 2])
@pytest.mark.parametrize('a,b', [(7, 5), (0, 6)])
def test_deep_played_descendant_blocks_even_if_intermediate_node_is_pending(index, a, b):
    nodes = list(save(make_bracket('quarterfinal'), index).nodes)
    # Defensive snapshot: inspect the whole descendant chain, not only next.
    nodes[-1] = replace(nodes[-1], registration_a_id=201, registration_b_id=202,
                        games_a=0, games_b=6, set_complete=True)
    before = tuple(nodes)
    assert nodes[4 + index // 2].set_complete is False
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, index, a, b)
    assert caught.value.code == 'descendant_played'
    assert tuple(nodes) == before


@pytest.mark.parametrize('side,foreign_id', [('a', 999), ('b', 503)])
def test_final_cannot_crown_a_participant_other_than_its_source_winner(side, foreign_id):
    nodes = list(save(save(make_bracket(), 0).nodes, 1).nodes)
    nodes[-1] = replace(nodes[-1], **{f'registration_{side}_id': foreign_id})
    before = tuple(nodes)
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 2, 6, 0)
    assert caught.value.code == 'invalid_configuration'
    assert caught.value.path == ('nodes', 2, f'registration_{side}_id')
    assert tuple(nodes) == before
    assert (nodes[-1].games_a, nodes[-1].games_b, nodes[-1].set_complete) == (None, None, False)


@pytest.mark.parametrize('side,slot', [('a', 1), ('b', 2)])
@pytest.mark.parametrize('kind', ['missing', 'wrong_kind', 'wrong_type', 'bool_slot', 'float_slot', 'swapped_parent'])
def test_winner_sources_require_valid_reciprocal_parent_references_on_both_sides(side, slot, kind):
    nodes = list(save(save(make_bracket(), 0).nodes, 1).nodes)
    source = domain.WinnerSource('winner', 'semifinal', slot)
    changes = {}
    if kind == 'missing':
        source = domain.WinnerSource('winner', 'quarterfinal', 99)
    elif kind == 'wrong_kind':
        source = replace(source, kind='seed')
    elif kind == 'wrong_type':
        source = domain.NodeRef('semifinal', slot)
    elif kind == 'bool_slot':
        source = replace(source, slot=True)
    elif kind == 'float_slot':
        source = replace(source, slot=float(slot))
    else:
        source = replace(source, slot=3 - slot)
        changes[f'registration_{side}_id'] = 102 if side == 'a' else 101
    nodes[-1] = replace(nodes[-1], **{f'source_{side}': source, **changes})
    before = tuple(nodes)
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 2)
    assert caught.value.code == 'invalid_configuration'
    assert caught.value.path == ('nodes', 2, f'source_{side}')
    assert tuple(nodes) == before


@pytest.mark.parametrize('stage,first_remaining', [('semifinal', 2), ('quarterfinal', 4)])
def test_a_bracket_slice_cannot_retain_winner_sources_to_omitted_nodes(stage, first_remaining):
    nodes = make_bracket(stage)
    for index in range(first_remaining):
        nodes = save(nodes, index).nodes
    sliced = nodes[first_remaining:]
    with pytest.raises(AmericanoDomainError) as caught:
        save(sliced, 0)
    assert caught.value.code == 'invalid_configuration'
    assert caught.value.path == ('nodes', 0, 'source_a')
    assert sliced[0].set_complete is False


@pytest.mark.parametrize('side,quarter_slot', [('a', 1), ('b', 3)])
def test_a_deep_winner_source_cannot_skip_its_intermediate_stage(side, quarter_slot):
    nodes = make_bracket('quarterfinal')
    for index in range(6):
        nodes = save(nodes, index).nodes
    bad = nodes[:-1] + (replace(nodes[-1], **{f'source_{side}': domain.WinnerSource('winner', 'quarterfinal', quarter_slot)}),)
    with pytest.raises(AmericanoDomainError) as caught:
        save(bad, 6)
    assert caught.value.code == 'invalid_configuration'
    assert caught.value.path == ('nodes', 6, f'source_{side}')
    assert bad[-1].set_complete is False


@pytest.mark.parametrize('side', ['a', 'b'])
@pytest.mark.parametrize('source', [
    None, domain.SeedSource('winner', 51, 1), domain.SeedSource('seed', True, 1),
    domain.SeedSource('seed', 51, 0), domain.SeedSource('seed', 51, 1.0),
])
def test_seed_sources_validate_only_their_known_shape_and_identity(side, source):
    original = make_bracket('final')
    nodes = (replace(original[0], **{f'source_{side}': source}),)
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 0)
    assert caught.value.code == 'invalid_configuration'
    assert nodes[0].set_complete is False


@pytest.mark.parametrize('stage', ['final', 'semifinal'])
def test_opening_seed_source_references_must_be_unique(stage):
    nodes = list(make_bracket(stage))
    nodes[0] = replace(nodes[0], source_b=nodes[0].source_a)
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 0)
    assert caught.value.code == 'invalid_configuration'
    assert (nodes[0].games_a, nodes[0].games_b) == (None, None)


@pytest.mark.parametrize('side', ['a', 'b'])
@pytest.mark.parametrize('stage,target', [('semifinal', 2), ('quarterfinal', 4), ('quarterfinal', 6)])
def test_unresolved_sources_cannot_supply_participants_at_any_depth(stage, target, side):
    nodes = list(make_bracket(stage))
    nodes[target] = replace(nodes[target], **{f'registration_{side}_id': 999})
    before = tuple(nodes)
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 0)
    assert caught.value.code == 'invalid_configuration'
    assert caught.value.path == ('nodes', target, f'registration_{side}_id')
    assert tuple(nodes) == before


@pytest.mark.parametrize('side,index', [('a', 0), ('b', 1)])
def test_resolved_source_winner_cannot_be_silently_missing_from_destination(side, index):
    nodes = list(save(make_bracket(), index).nodes)
    nodes[-1] = replace(nodes[-1], **{f'registration_{side}_id': None})
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 1 - index)
    assert caught.value.code == 'invalid_configuration'
    assert caught.value.path == ('nodes', 2, f'registration_{side}_id')
    assert nodes[1 - index].set_complete is False


@pytest.mark.parametrize('side', ['a', 'b'])
def test_destination_cannot_replace_an_incoming_winner_source_with_a_seed(side):
    nodes = list(make_bracket())
    nodes[-1] = replace(nodes[-1], **{f'source_{side}': domain.SeedSource('seed', 777, 9)})
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 0)
    assert caught.value.code == 'invalid_configuration'
    assert caught.value.path == ('nodes', 2, f'source_{side}')


@pytest.mark.parametrize('stage,omitted', [('semifinal', 1), ('quarterfinal', 2)])
def test_missing_feeders_cannot_be_disguised_as_later_stage_seed_sources(stage, omitted):
    nodes = list(make_bracket(stage)[omitted:])
    target = next(i for i, node in enumerate(nodes) if node.stage != stage)
    changes = {'source_a': domain.SeedSource('seed', 777, 1), 'registration_a_id': 999}
    if omitted == 2:
        changes.update(source_b=domain.SeedSource('seed', 777, 2), registration_b_id=503)
    nodes[target] = replace(nodes[target], **changes)
    before = tuple(nodes)
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 0)
    assert caught.value.code == 'invalid_configuration'
    assert caught.value.path == ('nodes', target, 'source_a')
    assert tuple(nodes) == before


@pytest.mark.parametrize('side,index', [('a', 0), ('b', 1)])
@pytest.mark.parametrize('value', [101.0, True])
def test_derived_participant_identity_is_strict_even_when_numeric_equality_would_match(side, index, value):
    ids = (101, 1019, 77, 43) if value is not True else (1, 1019, 77, 43)
    if side == 'b':
        ids = (ids[1], ids[0], ids[2], ids[3])
    nodes = list(save(make_bracket(registration_ids=ids), index).nodes)
    nodes[-1] = replace(nodes[-1], **{f'registration_{side}_id': value})
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 1 - index)
    assert caught.value.code == 'invalid_configuration'
    assert caught.value.path == ('nodes', 2, f'registration_{side}_id')
    assert nodes[1 - index].set_complete is False


@pytest.mark.parametrize('index', [0, 1])
def test_a_played_source_with_missing_winning_participant_is_not_resolved_to_none(index):
    nodes = list(make_bracket())
    nodes[index] = replace(nodes[index], registration_a_id=None, games_a=6, games_b=0, set_complete=True)
    before = tuple(nodes)
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 1 - index)
    assert caught.value.code == 'invalid_configuration'
    assert tuple(nodes) == before


@pytest.mark.parametrize('target,side', [(4, 'a'), (5, 'b')])
def test_final_correction_checks_participant_consistency_in_deep_ancestors(target, side):
    nodes = make_bracket('quarterfinal')
    for index in range(7):
        nodes = save(nodes, index).nodes
    bad = list(nodes)
    bad[target] = replace(bad[target], **{f'registration_{side}_id': 999})
    before = tuple(bad)
    with pytest.raises(AmericanoDomainError) as caught:
        save(bad, 6, 0, 6)
    assert caught.value.code == 'invalid_configuration'
    assert caught.value.path == ('nodes', target, f'registration_{side}_id')
    assert tuple(bad) == before
    assert (bad[-1].games_a, bad[-1].games_b) == (6, 0)


@pytest.mark.parametrize('stage,size', [('quarterfinal', 8), ('semifinal', 4), ('final', 2)])
@pytest.mark.parametrize('ids', [(999, 503, 91, 7, 2**53 - 1, 47, 1, 32), (503, 999, 77, 12, 19, 2, 84, 3)])
def test_arbitrary_legitimate_seed_ids_progress_and_final_remains_correctable(stage, size, ids):
    nodes = make_bracket(stage, ids[:size])
    original = nodes
    for index in range(len(nodes)):
        result = save(nodes, index)
        nodes = result.nodes
    assert result.champion_registration_id == ids[0]
    corrected = save(nodes, len(nodes) - 1, 0, 6)
    assert corrected.champion_registration_id == ids[1]
    assert corrected.nodes[:-1] == nodes[:-1]
    assert all(n.games_a is None and n.games_b is None for n in original)


@pytest.mark.parametrize('stage,pairs,other_finalist', [
    ('quarterfinal', ((51, 1, 23, 4), (23, 2, 51, 3), (23, 1, 51, 4), (51, 2, 23, 3)), 77),
    ('semifinal', ((51, 1, 23, 2), (23, 1, 51, 2)), 91),
    ('final', ((51, 1, 23, 1),), 503),
])
def test_two_zone_qualifier_sources_remain_valid_through_final_correction(stage, pairs, other_finalist):
    template = domain.SeedingTemplate('two-zone-explicit', 'approved', stage, 2, tuple(
        domain.OpeningPair(SeedRef(a, p), SeedRef(b, q)) for a, p, b, q in pairs
    ))
    refs = [ref for pair in template.opening_pairs for ref in (pair.a, pair.b)]
    ids = (999, 503, 91, 7, 77, 12, 1, 44)
    seeds = [ResolvedSeed(ref.zone_id, ref.position, registration_id) for ref, registration_id in zip(refs, ids)]
    nodes = domain.build_bracket(stage, seeds, template)
    for index in range(len(nodes)):
        result = save(nodes, index)
        nodes = result.nodes
    assert result.champion_registration_id == 999
    corrected = save(nodes, len(nodes) - 1, 0, 6)
    assert corrected.champion_registration_id == other_finalist
    assert corrected.nodes[:-1] == nodes[:-1]


@pytest.mark.parametrize('stage,slot', [('final', 2), ('quarterfinal', 1), ('semi', 1), ('semifinal', True), ('semifinal', 1.0)])
def test_change_requires_an_existing_strict_node_reference(stage, slot):
    nodes = make_bracket()
    change = domain.BracketChange(domain.NodeRef(stage, slot), domain.ValidatedSet(6, 0, 'a'), domain.APPROVED_CORRECTION_POLICY)
    with pytest.raises(AmericanoDomainError) as caught:
        domain.propagate_winner(nodes, change)
    assert caught.value.code == 'invalid_reference'
    assert all(node.games_a is None and node.games_b is None for node in nodes)


@pytest.mark.parametrize('a,b,side', [(6, 4, 'b'), (4, 6, 'a'), (6, 0, 'winner'), (8, 6, 'a'), (True, 6, 'b'), (6.0, 0, 'a')])
def test_propagation_revalidates_forged_validated_score_and_winner(a, b, side):
    nodes = make_bracket()
    change = domain.BracketChange(domain.NodeRef('semifinal', 1), domain.ValidatedSet(a, b, side), domain.APPROVED_CORRECTION_POLICY)
    with pytest.raises(AmericanoDomainError) as caught:
        domain.propagate_winner(nodes, change)
    assert caught.value.code == 'invalid_set'
    assert (nodes[0].games_a, nodes[0].games_b, nodes[-1].registration_a_id) == (None, None, None)


@pytest.mark.parametrize('changes', [
    {'block_played_descendants': False}, {'allow_final_correction': False},
    {'block_played_descendants': 1}, {'allow_final_correction': 1}, {'key': ''},
])
def test_propagation_cannot_opt_out_of_approved_correction_policy(changes):
    nodes = make_bracket()
    policy = replace(domain.APPROVED_CORRECTION_POLICY, **changes)
    change = domain.BracketChange(domain.NodeRef('semifinal', 1), domain.ValidatedSet(6, 0, 'a'), policy)
    with pytest.raises(AmericanoDomainError) as caught:
        domain.propagate_winner(nodes, change)
    assert caught.value.code == 'invalid_configuration'
    assert caught.value.path == ('correction_policy',)


@pytest.mark.parametrize('a,b', [(True, 102), (101, 0), (101.0, 102), (101, 101)])
def test_known_participants_must_be_distinct_positive_strict_ids(a, b):
    nodes = (replace(make_bracket('final')[0], registration_a_id=a, registration_b_id=b),)
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 0)
    assert caught.value.code == 'invalid_configuration'
    assert nodes[0].set_complete is False


@pytest.mark.parametrize('stage,a,b,champion,corrected_champion', [
    ('quarterfinal', 6, 0, 101, 102), ('quarterfinal', 0, 6, 106, 105),
    ('semifinal', 6, 0, 101, 102), ('semifinal', 0, 6, 103, 104),
    ('final', 6, 0, 101, 102), ('final', 0, 6, 102, 101),
])
def test_entire_bracket_to_champion_and_final_correction_preserves_all_earlier_nodes(stage, a, b, champion, corrected_champion):
    original = make_bracket(stage)
    nodes = original
    for index in range(len(nodes)):
        result = save(nodes, index, a, b)
        nodes = result.nodes
    assert result.champion_registration_id == champion
    assert [(n.games_a, n.games_b, n.set_complete) for n in nodes] == [(a, b, True)] * len(nodes)
    corrected = save(nodes, len(nodes) - 1, b, a)
    assert corrected.champion_registration_id == corrected_champion
    assert corrected.nodes[:-1] == nodes[:-1]
    assert [(n.source_a, n.source_b, n.next) for n in corrected.nodes] == [(n.source_a, n.source_b, n.next) for n in original]
    assert all(n.games_a is None and n.games_b is None for n in original)


@pytest.mark.parametrize('index,expected_semifinalists', [(0, (108, None)), (1, (None, 105))])
def test_played_unrelated_branch_does_not_block_or_change_on_quarterfinal_correction(index, expected_semifinalists):
    nodes = make_bracket('quarterfinal')
    for played in (index, 2, 3, 5):
        nodes = save(nodes, played).nodes
    result = save(nodes, index, 0, 6)
    assert (result.nodes[4].registration_a_id, result.nodes[4].registration_b_id) == expected_semifinalists
    assert result.nodes[5:] == nodes[5:]
    assert (result.nodes[-1].registration_a_id, result.nodes[-1].registration_b_id) == (None, 102)


@pytest.mark.parametrize('index', [0, 1])
def test_result_is_frozen_and_detached_from_mutable_input_collection(index):
    nodes = list(make_bracket())
    original = tuple(nodes)
    result = save(nodes, index)
    assert isinstance(result.nodes, tuple)
    assert all(new is not old for new, old in zip(result.nodes, original))
    with pytest.raises(FrozenInstanceError):
        result.nodes[index].games_a = 0
    with pytest.raises(FrozenInstanceError):
        result.champion_registration_id = 999
    nodes.clear()
    assert len(result.nodes) == 3
    assert (result.nodes[index].games_a, result.nodes[index].games_b) == (6, 0)


@pytest.mark.parametrize('games_a,games_b', [(0, None), (None, 0)])
def test_partial_descendant_zero_is_conservatively_blocking(games_a, games_b):
    nodes = list(save(make_bracket(), 0).nodes)
    nodes[-1] = replace(nodes[-1], games_a=games_a, games_b=games_b)
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 0, 7, 5)
    assert caught.value.code == 'descendant_played'
    assert (nodes[-1].games_a, nodes[-1].games_b) == (games_a, games_b)


@pytest.mark.parametrize('kind', ['missing_target', 'duplicate_ref', 'missing_destination', 'wrong_side', 'bool_slot', 'self_cycle'])
def test_malformed_bracket_references_are_domain_errors_without_advancing(kind):
    nodes = list(save(make_bracket(), 0).nodes)
    if kind == 'missing_target':
        nodes.pop()
    elif kind == 'duplicate_ref':
        nodes.append(nodes[-1])
    elif kind == 'missing_destination':
        nodes[0] = replace(nodes[0], next=None)
    elif kind == 'wrong_side':
        nodes[0] = replace(nodes[0], next=domain.BracketDestination('final', 1, 'b'))
    elif kind == 'bool_slot':
        nodes[0] = replace(nodes[0], next=domain.BracketDestination('final', True, 'a'))
    else:
        nodes[0] = replace(nodes[0], next=domain.BracketDestination('semifinal', 1, 'a'))
    before = tuple(nodes)
    with pytest.raises(AmericanoDomainError) as caught:
        save(nodes, 0, 0, 6)
    assert caught.value.code == 'invalid_configuration'
    assert tuple(nodes) == before
