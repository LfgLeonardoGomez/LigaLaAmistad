"""Pure bracket topology plus D8 set rules, independent of API and persistence."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

from app.americanos.fixture import AmericanoDomainError, Side, StartStage, _positive_integer
from app.americanos.qualification import ResolvedSeed, SeedRef, qualification_quotas


@dataclass(frozen=True)
class NodeRef:
    stage: StartStage
    slot: int


@dataclass(frozen=True)
class SeedSource:
    kind: Literal['seed']
    zone_id: int
    position: int


@dataclass(frozen=True)
class WinnerSource:
    kind: Literal['winner']
    stage: StartStage
    slot: int


BracketSource = SeedSource | WinnerSource


@dataclass(frozen=True)
class OpeningPair:
    a: SeedRef
    b: SeedRef


@dataclass(frozen=True)
class SeedingTemplate:
    key: str
    status: Literal['approved', 'proposed']
    start_stage: StartStage
    zone_count: Literal[1, 2]
    opening_pairs: tuple[OpeningPair, ...]


@dataclass(frozen=True)
class BracketDestination:
    stage: StartStage
    slot: int
    side: Side


@dataclass(frozen=True)
class BracketLayoutNode:
    stage: StartStage
    slot: int
    source_a: BracketSource
    source_b: BracketSource
    next: BracketDestination | None


@dataclass(frozen=True)
class BracketNode:
    stage: StartStage
    slot: int
    source_a: BracketSource
    source_b: BracketSource
    registration_a_id: int | None
    registration_b_id: int | None
    games_a: int | None
    games_b: int | None
    set_complete: bool
    next: BracketDestination | None


def _validate_template(start_stage: StartStage, template: SeedingTemplate) -> None:
    if template.start_stage != start_stage or start_stage not in ('quarterfinal', 'semifinal', 'final'):
        raise AmericanoDomainError('invalid_configuration', 'Template and bracket stages must match.', ('seeding_template', 'start_stage'))
    if type(template.zone_count) is not int or template.zone_count not in (1, 2):
        raise AmericanoDomainError('invalid_configuration', 'Template requires one or two zones.', ('seeding_template', 'zone_count'))
    if not isinstance(template.key, str) or not template.key.strip() or template.status not in ('approved', 'proposed'):
        raise AmericanoDomainError('invalid_configuration', 'Template key and approval status are required.', ('seeding_template',))
    refs = [ref for pair in template.opening_pairs for ref in (pair.a, pair.b)]
    for index, ref in enumerate(refs):
        _positive_integer(ref.zone_id, ('seeding_template', 'seeds', index, 'zone_id'))
        _positive_integer(ref.position, ('seeding_template', 'seeds', index, 'position'))
    zone_ids = sorted({ref.zone_id for ref in refs})
    if len(zone_ids) != template.zone_count:
        raise AmericanoDomainError('invalid_configuration', 'Template zones must match zone_count.', ('seeding_template',))
    quotas = qualification_quotas(start_stage, zone_ids)
    expected = {SeedRef(zone_id, position) for zone_id, quota in quotas.items() for position in range(1, quota + 1)}
    if len(refs) != len(expected) or set(refs) != expected:
        raise AmericanoDomainError('invalid_configuration', 'Template must use every required seed exactly once without byes.', ('seeding_template', 'opening_pairs'))


def bracket_layout(
    start_stage: StartStage, seeding_template: SeedingTemplate,
) -> tuple[BracketLayoutNode, ...]:
    """Build preview sources/destinations without requiring resolved participants."""
    _validate_template(start_stage, seeding_template)
    stages: tuple[StartStage, ...] = ('quarterfinal', 'semifinal', 'final')
    active_stages = stages[stages.index(start_stage):]
    nodes = []
    count = len(seeding_template.opening_pairs)
    for index, stage in enumerate(active_stages):
        for slot in range(1, count + 1):
            if index == 0:
                pair = seeding_template.opening_pairs[slot - 1]
                a: BracketSource = SeedSource('seed', pair.a.zone_id, pair.a.position)
                b: BracketSource = SeedSource('seed', pair.b.zone_id, pair.b.position)
            else:
                a = WinnerSource('winner', active_stages[index - 1], 2 * slot - 1)
                b = WinnerSource('winner', active_stages[index - 1], 2 * slot)
            destination = None if stage == 'final' else BracketDestination(
                active_stages[index + 1], (slot + 1) // 2, 'a' if slot % 2 else 'b',
            )
            nodes.append(BracketLayoutNode(stage, slot, a, b, destination))
        count //= 2
    return tuple(nodes)


def build_bracket(
    start_stage: StartStage, resolved_seeds: Sequence[ResolvedSeed], seeding_template: SeedingTemplate,
) -> tuple[BracketNode, ...]:
    """Resolve all opening seeds; template approval is the caller's responsibility."""
    layout = bracket_layout(start_stage, seeding_template)
    for index, seed in enumerate(resolved_seeds):
        for field in ('zone_id', 'position', 'registration_id'):
            _positive_integer(getattr(seed, field), ('resolved_seeds', index, field))
    seeds = {(s.zone_id, s.position): s.registration_id for s in resolved_seeds}
    expected = {(ref.zone_id, ref.position) for pair in seeding_template.opening_pairs for ref in (pair.a, pair.b)}
    if (set(seeds) != expected or len(resolved_seeds) != len(expected)
            or len(set(seeds.values())) != len(expected)):
        raise AmericanoDomainError('invalid_configuration', 'Exactly one unique registration per required seed is required.', ('resolved_seeds',))
    return tuple(
        BracketNode(
            node.stage, node.slot, node.source_a, node.source_b,
            seeds[node.source_a.zone_id, node.source_a.position] if isinstance(node.source_a, SeedSource) else None,
            seeds[node.source_b.zone_id, node.source_b.position] if isinstance(node.source_b, SeedSource) else None,
            None, None, False, node.next,
        )
        for node in layout
    )


@dataclass(frozen=True)
class FullSetScore:
    games_a: int
    games_b: int
    set_complete: bool


@dataclass(frozen=True)
class SetConvention:
    key: str
    minimum_winner_games: int
    win_by: int
    tiebreak_at: int | None
    tiebreak_winner_games: int | None


@dataclass(frozen=True)
class ValidatedSet:
    games_a: int
    games_b: int
    winner_side: Side


APPROVED_SET_CONVENTION = SetConvention('traditional-tiebreak-v1', 6, 2, 6, 7)


def validate_full_set(score: FullSetScore, convention: SetConvention) -> ValidatedSet:
    """Validate the D8 terminal score, preserving zero and deriving its winner."""
    parameters = (convention.minimum_winner_games, convention.win_by,
                  convention.tiebreak_at, convention.tiebreak_winner_games)
    if (not isinstance(convention.key, str) or not convention.key.strip()
            or any(type(value) is not int for value in parameters) or parameters != (6, 2, 6, 7)):
        raise AmericanoDomainError('invalid_configuration', 'Only the approved D8 convention is supported.', ('convention',))
    for field in ('games_a', 'games_b'):
        value = getattr(score, field)
        if type(value) is not int or value < 0:
            raise AmericanoDomainError('invalid_set', 'Expected a nonnegative integer.', (field,))
    if score.set_complete is not True:
        raise AmericanoDomainError('invalid_set', 'The set must be declared complete.', ('set_complete',))
    winner, loser = max(score.games_a, score.games_b), min(score.games_a, score.games_b)
    if not (winner == 6 and loser <= 4 or winner == 7 and loser in (5, 6)):
        raise AmericanoDomainError('invalid_set', 'Expected 6-0 through 6-4, 7-5 or 7-6, or the reverse.')
    return ValidatedSet(score.games_a, score.games_b, 'a' if score.games_a > score.games_b else 'b')


@dataclass(frozen=True)
class CorrectionPolicy:
    key: str
    block_played_descendants: bool
    allow_final_correction: bool


@dataclass(frozen=True)
class BracketChange:
    node: NodeRef
    score: ValidatedSet
    correction_policy: CorrectionPolicy


@dataclass(frozen=True)
class PropagationResult:
    nodes: tuple[BracketNode, ...]
    champion_registration_id: int | None


APPROVED_CORRECTION_POLICY = CorrectionPolicy('conservative-d8-v1', True, True)


def _index_bracket(nodes: Sequence[BracketNode]) -> dict[NodeRef, int]:
    """Check logical identities and reciprocal sources/destinations."""
    stages: tuple[StartStage, ...] = ('quarterfinal', 'semifinal', 'final')
    indices: dict[NodeRef, int] = {}
    for index, node in enumerate(nodes):
        if (node.stage not in stages or type(node.slot) is not int
                or not 1 <= node.slot <= (4, 2, 1)[stages.index(node.stage)]):
            raise AmericanoDomainError('invalid_configuration', 'Invalid bracket node reference.', ('nodes', index))
        ref = NodeRef(node.stage, node.slot)
        if ref in indices:
            raise AmericanoDomainError('invalid_configuration', 'Bracket node references must be unique.', ('nodes', index))
        indices[ref] = index
    for index, node in enumerate(nodes):
        if node.stage == 'final':
            valid = node.next is None
        else:
            expected = BracketDestination(stages[stages.index(node.stage) + 1], (node.slot + 1) // 2,
                                          'a' if node.slot % 2 else 'b')
            valid = (node.next is not None and type(node.next.slot) is int and node.next == expected
                     and NodeRef(expected.stage, expected.slot) in indices)
        if not valid:
            raise AmericanoDomainError('invalid_configuration', 'Invalid bracket destination.', ('nodes', index, 'next'))
    opening_stage = min((stages.index(node.stage) for node in nodes), default=2)
    seeds: set[SeedRef] = set()
    for index, node in enumerate(nodes):
        for side in ('a', 'b'):
            source = getattr(node, f'source_{side}')
            path = ('nodes', index, f'source_{side}')
            if isinstance(source, SeedSource) and source.kind == 'seed':
                if stages.index(node.stage) != opening_stage:
                    raise AmericanoDomainError('invalid_configuration', 'Only opening nodes can have seed sources.', path)
                _positive_integer(source.zone_id, (*path, 'zone_id'))
                _positive_integer(source.position, (*path, 'position'))
                ref = SeedRef(source.zone_id, source.position)
                if ref in seeds:
                    raise AmericanoDomainError('invalid_configuration', 'Seed sources must be unique.', path)
                seeds.add(ref)
            elif (isinstance(source, WinnerSource) and source.kind == 'winner'
                  and source.stage in stages and type(source.slot) is int and source.slot > 0):
                parent_index = indices.get(NodeRef(source.stage, source.slot))
                previous_stage = stages[stages.index(node.stage) - 1] if node.stage != 'quarterfinal' else None
                expected_slot = 2 * node.slot - (1 if side == 'a' else 0)
                if (parent_index is None or source.stage != previous_stage or source.slot != expected_slot
                        or nodes[parent_index].next != BracketDestination(node.stage, node.slot, side)):
                    raise AmericanoDomainError('invalid_configuration', 'Invalid winner source reference.', path)
            else:
                raise AmericanoDomainError('invalid_configuration', 'Invalid bracket source.', path)
    for node in nodes:
        if node.next is not None:
            target_index = indices[NodeRef(node.next.stage, node.next.slot)]
            source = getattr(nodes[target_index], f'source_{node.next.side}')
            if source != WinnerSource('winner', node.stage, node.slot):
                raise AmericanoDomainError('invalid_configuration', 'Destination must reference its incoming winner.',
                                           ('nodes', target_index, f'source_{node.next.side}'))
    return indices


def _validate_participants(nodes: Sequence[BracketNode], indices: dict[NodeRef, int]) -> None:
    """Check strict IDs and derivable winners without guessing external seed IDs."""
    for index, node in enumerate(nodes):
        for side in ('a', 'b'):
            participant = getattr(node, f'registration_{side}_id')
            if participant is not None or node.set_complete:
                _positive_integer(participant, ('nodes', index, f'registration_{side}_id'))
            source = getattr(node, f'source_{side}')
            if isinstance(source, WinnerSource):
                parent = nodes[indices[NodeRef(source.stage, source.slot)]]
                expected = None
                if parent.set_complete:
                    score = validate_full_set(FullSetScore(parent.games_a, parent.games_b, True), APPROVED_SET_CONVENTION)
                    expected = parent.registration_a_id if score.winner_side == 'a' else parent.registration_b_id
                if participant != expected:
                    raise AmericanoDomainError('invalid_configuration', 'Participant must match its source winner.',
                                               ('nodes', index, f'registration_{side}_id'))


def propagate_winner(nodes: Sequence[BracketNode], change: BracketChange) -> PropagationResult:
    """Copy a canonical bracket, recording a set and advancing its winner.

    Any played descendant blocks the change, including same-winner corrections.
    Source topology and participant consistency are checked before copying;
    the descendant-played guard takes priority over participant consistency.
    Final corrections return the replacement champion; event state, transaction
    boundaries and keeping groups closed belong to the calling application.
    """
    policy = change.correction_policy
    if (not isinstance(policy.key, str) or not policy.key.strip()
            or policy.block_played_descendants is not True or policy.allow_final_correction is not True):
        raise AmericanoDomainError('invalid_configuration', 'Only the approved D8 correction policy is supported.', ('correction_policy',))
    score = validate_full_set(FullSetScore(change.score.games_a, change.score.games_b, True), APPROVED_SET_CONVENTION)
    if change.score.winner_side != score.winner_side:
        raise AmericanoDomainError('invalid_set', 'Winner side must agree with the games.', ('winner_side',))
    if (change.node.stage not in ('quarterfinal', 'semifinal', 'final')
            or type(change.node.slot) is not int or change.node.slot < 1):
        raise AmericanoDomainError('invalid_reference', 'Unknown bracket node.', ('node',))
    indices = _index_bracket(nodes)
    index = indices.get(change.node)
    if index is None:
        raise AmericanoDomainError('invalid_reference', 'Unknown bracket node.', ('node',))
    node = nodes[index]
    if node.registration_a_id is None or node.registration_b_id is None:
        raise AmericanoDomainError('participants_pending', 'Both participants must be known before recording a result.')
    _positive_integer(node.registration_a_id, ('nodes', index, 'registration_a_id'))
    _positive_integer(node.registration_b_id, ('nodes', index, 'registration_b_id'))
    if node.registration_a_id == node.registration_b_id:
        raise AmericanoDomainError('invalid_configuration', 'Participants must be distinct.', ('nodes', index))
    destination = node.next
    while destination is not None:
        descendant = nodes[indices[NodeRef(destination.stage, destination.slot)]]
        if descendant.set_complete or descendant.games_a is not None or descendant.games_b is not None:
            raise AmericanoDomainError('descendant_played', 'A played descendant prevents any correction.')
        destination = descendant.next
    _validate_participants(nodes, indices)
    winner = node.registration_a_id if score.winner_side == 'a' else node.registration_b_id
    updated = [replace(candidate) for candidate in nodes]
    updated[index] = replace(node, games_a=score.games_a, games_b=score.games_b, set_complete=True)
    destination = node.next
    if destination is None:
        return PropagationResult(tuple(updated), winner)
    target = indices[NodeRef(destination.stage, destination.slot)]
    updated[target] = replace(updated[target], **{f'registration_{destination.side}_id': winner})
    return PropagationResult(tuple(updated), None)
