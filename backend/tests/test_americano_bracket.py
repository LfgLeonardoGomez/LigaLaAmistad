"""D6-approved explicit seeding templates and independent bracket topology."""

from dataclasses import replace

import pytest

from app.americanos.fixture import AmericanoDomainError
from app.americanos.bracket import (
    BracketDestination, OpeningPair, SeedSource, SeedingTemplate, WinnerSource, bracket_layout, build_bracket,
)
from app.americanos.qualification import ResolvedSeed, SeedRef


def explicit_template(stage, zone_count):
    # D6-approved pairings supplied explicitly; no production default selector.
    pairs = {
        ('quarterfinal', 1): [(51, 1, 51, 8), (51, 4, 51, 5), (51, 2, 51, 7), (51, 3, 51, 6)],
        ('quarterfinal', 2): [(51, 1, 23, 4), (23, 2, 51, 3), (23, 1, 51, 4), (51, 2, 23, 3)],
        ('semifinal', 1): [(51, 1, 51, 4), (51, 2, 51, 3)],
        ('semifinal', 2): [(51, 1, 23, 2), (23, 1, 51, 2)],
        ('final', 1): [(51, 1, 51, 2)],
        ('final', 2): [(51, 1, 23, 1)],
    }[stage, zone_count]
    suffix = 'one-zone' if zone_count == 1 else 'two-zones'
    return SeedingTemplate(f'{stage}-{suffix}-v1', 'approved',
                           stage, zone_count, tuple(OpeningPair(SeedRef(a, p), SeedRef(b, q)) for a, p, b, q in pairs))


def test_approved_one_zone_semifinal_layout_is_stable_and_has_no_byes():
    template = SeedingTemplate('semifinal-one-zone-v1', 'approved', 'semifinal', 1, (
        OpeningPair(SeedRef(51, 1), SeedRef(51, 4)),
        OpeningPair(SeedRef(51, 2), SeedRef(51, 3)),
    ))
    nodes = bracket_layout('semifinal', template)
    assert [(n.stage, n.slot) for n in nodes] == [('semifinal', 1), ('semifinal', 2), ('final', 1)]
    assert [(n.source_a, n.source_b, n.next) for n in nodes] == [
        (SeedSource('seed', 51, 1), SeedSource('seed', 51, 4), BracketDestination('final', 1, 'a')),
        (SeedSource('seed', 51, 2), SeedSource('seed', 51, 3), BracketDestination('final', 1, 'b')),
        (WinnerSource('winner', 'semifinal', 1), WinnerSource('winner', 'semifinal', 2), None),
    ]


@pytest.mark.parametrize('stage,count', [('quarterfinal', 7), ('semifinal', 3), ('final', 1)])
@pytest.mark.parametrize('zone_count', [1, 2])
def test_layout_all_sizes_preserves_explicit_openings_and_acyclic_unique_destinations(stage, count, zone_count):
    template = explicit_template(stage, zone_count)
    nodes = bracket_layout(stage, template)
    assert len(nodes) == count
    openings = [n for n in nodes if n.stage == stage]
    assert [(n.source_a, n.source_b) for n in openings] == [
        (SeedSource('seed', p.a.zone_id, p.a.position), SeedSource('seed', p.b.zone_id, p.b.position))
        for p in template.opening_pairs
    ]
    indices = {(n.stage, n.slot): index for index, n in enumerate(nodes)}
    destinations = set()
    for index, node in enumerate(nodes):
        if node.next is not None:
            target = (node.next.stage, node.next.slot)
            assert indices[target] > index
            assert (*target, node.next.side) not in destinations
            destinations.add((*target, node.next.side))
            target_node = nodes[indices[target]]
            source = target_node.source_a if node.next.side == 'a' else target_node.source_b
            assert source == WinnerSource('winner', node.stage, node.slot)
    assert len(destinations) == count - 1
    assert nodes[-1].next is None
    if stage == 'quarterfinal':
        assert [n.next for n in nodes] == [
            BracketDestination('semifinal', 1, 'a'), BracketDestination('semifinal', 1, 'b'),
            BracketDestination('semifinal', 2, 'a'), BracketDestination('semifinal', 2, 'b'),
            BracketDestination('final', 1, 'a'), BracketDestination('final', 1, 'b'), None,
        ]
    assert template.status == 'approved'


@pytest.mark.parametrize('change', [
    {'start_stage': 'final'}, {'zone_count': 2}, {'zone_count': True}, {'zone_count': 1.0},
    {'status': 'accepted'}, {'key': ''}, {'opening_pairs': ()},
    {'opening_pairs': (OpeningPair(SeedRef(51, 1), SeedRef(51, 4)),) * 2},
    {'opening_pairs': (OpeningPair(SeedRef(51, 1), SeedRef(51, 5)), OpeningPair(SeedRef(51, 2), SeedRef(51, 3)))},
    {'opening_pairs': (OpeningPair(SeedRef(True, 1), SeedRef(51, 4)), OpeningPair(SeedRef(51, 2), SeedRef(51, 3)))},
    {'opening_pairs': (OpeningPair(SeedRef(51, True), SeedRef(51, 4)), OpeningPair(SeedRef(51, 2), SeedRef(51, 3)))},
])
def test_layout_rejects_invalid_template_without_inventing_seeds(change):
    with pytest.raises(AmericanoDomainError) as caught:
        bracket_layout('semifinal', replace(explicit_template('semifinal', 1), **change))
    assert caught.value.code == 'invalid_configuration'


def test_unknown_stage_is_domain_error():
    with pytest.raises(AmericanoDomainError):
        bracket_layout('semi', explicit_template('semifinal', 1))


def test_constructor_resolves_opening_seeds_and_leaves_final_pending():
    seeds = [ResolvedSeed(51, p, id) for p, id in enumerate((91, 17, 82, 43), 1)]
    nodes = build_bracket('semifinal', seeds, explicit_template('semifinal', 1))
    assert [(n.registration_a_id, n.registration_b_id) for n in nodes] == [(91, 43), (17, 82), (None, None)]
    assert [(n.games_a, n.games_b, n.set_complete) for n in nodes] == [(None, None, False)] * 3
    assert [n.next for n in nodes] == [BracketDestination('final', 1, 'a'), BracketDestination('final', 1, 'b'), None]


@pytest.mark.parametrize('stage,count', [('quarterfinal', 7), ('semifinal', 3), ('final', 1)])
@pytest.mark.parametrize('zone_count', [1, 2])
def test_constructor_all_sizes_with_shuffled_seeds_and_approved_templates(stage, count, zone_count):
    template = explicit_template(stage, zone_count)
    refs = [ref for pair in template.opening_pairs for ref in (pair.a, pair.b)]
    seeds = [ResolvedSeed(ref.zone_id, ref.position, 101 + i) for i, ref in enumerate(refs)]
    original = list(seeds)
    nodes = build_bracket(stage, list(reversed(seeds)), template)
    assert len(nodes) == count
    assert [(n.registration_a_id, n.registration_b_id) for n in nodes if n.stage == stage] == [
        (101 + 2 * i, 102 + 2 * i) for i in range(len(template.opening_pairs))
    ]
    assert all(n.registration_a_id is None and n.registration_b_id is None for n in nodes if n.stage != stage)
    assert [(n.games_a, n.games_b, n.set_complete) for n in nodes] == [(None, None, False)] * count
    assert seeds == original
    assert build_bracket(stage, seeds, template) == nodes
    assert template.status == 'approved'


@pytest.mark.parametrize('stage', ['quarterfinal', 'semifinal', 'final'])
@pytest.mark.parametrize('zone_count', [1, 2])
def test_future_proposed_template_can_be_constructed_without_becoming_approved(stage, zone_count):
    approved = explicit_template(stage, zone_count)
    proposed = replace(approved, key='future-proposal', status='proposed')
    refs = [ref for pair in approved.opening_pairs for ref in (pair.a, pair.b)]
    seeds = [ResolvedSeed(ref.zone_id, ref.position, 101 + i) for i, ref in enumerate(refs)]
    assert build_bracket(stage, seeds, proposed) == build_bracket(stage, seeds, approved)
    assert proposed.status == 'proposed'


@pytest.mark.parametrize('seeds', [
    [ResolvedSeed(51, 1, 11), ResolvedSeed(51, 2, 12), ResolvedSeed(51, 3, 13)],
    [ResolvedSeed(51, p, 11) for p in range(1, 5)],
    [ResolvedSeed(51, p, 10 + p) for p in range(1, 6)],
    [ResolvedSeed(51, 1, 11), ResolvedSeed(51, 2, 12), ResolvedSeed(51, 3, 13), ResolvedSeed(51, 3, 14)],
    [ResolvedSeed(51, 1, 11), ResolvedSeed(51, 2, 12), ResolvedSeed(51, 3, 13), ResolvedSeed(23, 4, 14)],
    [ResolvedSeed(51, p, True if p == 4 else 10 + p) for p in range(1, 5)],
    [ResolvedSeed(51, p, 0 if p == 4 else 10 + p) for p in range(1, 5)],
    [ResolvedSeed(51, p, 1.0 if p == 4 else 10 + p) for p in range(1, 5)],
    [ResolvedSeed(51.0, p, 10 + p) for p in range(1, 5)],
    [ResolvedSeed(51, float(p), 10 + p) for p in range(1, 5)],
])
def test_constructor_rejects_missing_extra_duplicate_or_foreign_seeds(seeds):
    with pytest.raises(AmericanoDomainError) as caught:
        build_bracket('semifinal', seeds, explicit_template('semifinal', 1))
    assert caught.value.code == 'invalid_configuration'


def test_constructor_requires_explicit_template_argument():
    with pytest.raises(TypeError, match='seeding_template'):
        build_bracket('final', [ResolvedSeed(51, 1, 11), ResolvedSeed(51, 2, 12)])


@pytest.mark.parametrize('zone_count', [1, 2])
def test_pure_handoff_from_saved_scores_through_manual_seeds_to_bracket(zone_count):
    from itertools import combinations

    from app.americanos.qualification import TieResolution, qualification_preview, qualification_quotas
    from app.americanos.standings import SavedScore, StandingRegistration, calculate_standings

    ids_by_zone = {51: (91, 17, 82, 43)} if zone_count == 1 else {51: (91, 17), 23: (82, 43)}
    registrations = [StandingRegistration(id, zone, f'P{id}', f'Q{id}', order)
                     for order, (zone, id) in enumerate(((z, i) for z, ids in ids_by_zone.items() for i in ids), 1)]
    scores = [SavedScore(order, zone, a, b, 0, 0)
              for order, (zone, a, b) in enumerate(((z, a, b) for z, ids in ids_by_zone.items() for a, b in combinations(ids, 2)), 1)]
    standings = calculate_standings(registrations, scores)
    quotas = qualification_quotas('semifinal', list(ids_by_zone))
    unresolved = qualification_preview(standings, quotas, [])
    assert len(unresolved.missing_slots) == 4
    assert unresolved.resolved_seeds == ()
    selections = [TieResolution(z, p, id) for z, ids in ids_by_zone.items() for p, id in enumerate(reversed(ids), 1)]
    resolved = qualification_preview(standings, quotas, selections)
    assert resolved.missing_slots == ()
    nodes = build_bracket('semifinal', resolved.resolved_seeds, explicit_template('semifinal', zone_count))
    expected = [(43, 91), (82, 17)] if zone_count == 1 else [(17, 82), (43, 91)]
    assert [(n.registration_a_id, n.registration_b_id) for n in nodes[:2]] == expected
    assert (nodes[-1].registration_a_id, nodes[-1].registration_b_id) == (None, None)
