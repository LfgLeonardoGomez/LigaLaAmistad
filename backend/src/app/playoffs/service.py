"""Playoff bracket: generation and advancement.

The wiring between nodes is not computed here — it is the fixed
`BRACKET_TEMPLATE` from `app.playoffs.models`, because the crossings are a
tournament-design decision, not something that falls out of an algorithm.
This module only ever does two things with it: lay the 19 nodes out once
(`build_bracket`), and re-decide one node from its sources whenever something
upstream changes (`_settle`, driven by `advance`).

`_settle` is written to be safe to call more than once for the same node.
That single property is what lets both generation-time byes and a later
correction share the same code path: a bye cascades forward by calling
`_settle` on the node it feeds, and a correction that invalidates a chain of
already-decided nodes is handled by unplaying whatever depended on the stale
winner (`_reset_downstream`) and then simply calling `_settle` again.
"""

import datetime
from collections import defaultdict
from typing import NamedTuple

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.models import utc_now
from app.matches import service as matches_service
from app.matches.models import Match, MatchSet, MatchStatus
from app.matches.schemas import MatchRead, SetRead
from app.matches.service import get_sets, winner_team_id
from app.playoffs.models import (
    BRACKET_TEMPLATE,
    PlayoffMatch,
    PlayoffMatchStatus,
    PlayoffRound,
    PlayoffSeed,
    PlayoffSide,
)
from app.playoffs.schemas import (
    BracketMode,
    BracketRead,
    GroupStagePendingError,
    PendingGroupMatchRead,
    PlayoffNodeRead,
    PlayoffResultsLoadedError,
    PlayoffRoundRead,
    PlayoffTeamRead,
)
from app.standings.service import get_standings
from app.teams.models import Team
from app.votes.models import MatchVote
from app.zones.models import Zone

_ROUND_ORDER = (
    PlayoffRound.ROUND_1,
    PlayoffRound.ROUND_2,
    PlayoffRound.QUARTERFINAL,
    PlayoffRound.SEMIFINAL,
    PlayoffRound.FINAL,
)


class _SeedSource(NamedTuple):
    zone_letter: str
    position: int


class _NodeSource(NamedTuple):
    round: PlayoffRound
    slot: int


_Source = _SeedSource | _NodeSource


def _build_node_sources() -> dict[tuple[PlayoffRound, int], tuple[_Source | None, _Source | None]]:
    """Invert `BRACKET_TEMPLATE` into "what feeds each side of each node".

    Built once, from the template, rather than walked by hand every time:
    every node's side is fed either by a seed (round 1, and the direct
    qualifier side of each quarterfinal) or by another node's winner
    (everything else), and this table is what lets `_resolve_source` treat
    both cases the same way.
    """
    sources: dict[tuple[PlayoffRound, int], list[_Source | None]] = {
        (node.round, node.slot): [None, None] for node in BRACKET_TEMPLATE
    }
    for node in BRACKET_TEMPLATE:
        if node.seed_a is not None:
            sources[(node.round, node.slot)][0] = _SeedSource(*node.seed_a)
        if node.seed_b is not None:
            sources[(node.round, node.slot)][1] = _SeedSource(*node.seed_b)
        if node.next_round is not None:
            index = 0 if node.next_side is PlayoffSide.A else 1
            sources[(node.next_round, node.next_slot)][index] = _NodeSource(node.round, node.slot)
    return {key: (value[0], value[1]) for key, value in sources.items()}


NODE_SOURCES = _build_node_sources()


def _build_draw_order() -> dict[PlayoffRound, tuple[int, ...]]:
    """Each round's nodes, in the order the bracket draws without a crossing.

    Derived from `NODE_SOURCES` — never hand-listed — because the wiring
    already fully determines it: starting at the final (a single node) and
    walking backward, a round's draw order is simply each already-ordered
    node in the round after it, expanded into whichever of ITS two sources
    are nodes of this round, side A before side B. A round fed entirely by
    seeds (round 1's own sources) contributes nothing to the walk and keeps
    its natural slot order.

    Hand-listing this instead would put the same fact in two places, and a
    future change to `BRACKET_TEMPLATE`'s wiring would silently stop
    matching it — this function is what keeps that impossible.
    """
    order: dict[PlayoffRound, tuple[int, ...]] = {PlayoffRound.FINAL: (1,)}
    for round_index in range(len(_ROUND_ORDER) - 1, 0, -1):
        this_round = _ROUND_ORDER[round_index]
        previous_round = _ROUND_ORDER[round_index - 1]
        previous_slots: list[int] = []
        for slot in order[this_round]:
            for source in NODE_SOURCES[(this_round, slot)]:
                if isinstance(source, _NodeSource) and source.round is previous_round:
                    previous_slots.append(source.slot)
        order[previous_round] = tuple(previous_slots)
    return order


DRAW_ORDER = _build_draw_order()


def _placeholder_date() -> datetime.date:
    """A newly wired playoff match needs *a* date; `Match.date` has no default.

    The pairing is decided before the day is, the same situation `Match.time`
    and `Match.venue` already model for the group stage. It is not meant to
    be accurate — the admin corrects it the same way a group-stage match's
    time or venue gets corrected, through the existing `PATCH
    /admin/matches/{id}`.
    """
    return utc_now().date()


def _ordered_zone_ids(session: Session) -> tuple[int, int]:
    """Zone A is the lower-id of the two zones, zone B the other.

    Zones are created once by seed, in that fixed order, and never
    reordered (see `app.zones.models.Zone`), so this is a stable mapping
    from the letters the bracket template speaks to real zone ids.
    """
    zones = list(session.exec(select(Zone).order_by(Zone.id)).all())
    if len(zones) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Playoffs need exactly two zones",
        )
    return zones[0].id, zones[1].id


SeedLookup = dict[tuple[str, int], int]


def _seed_lookup_from_standings(session: Session, zone_a_id: int, zone_b_id: int) -> SeedLookup:
    """`(zone_letter, position) -> team_id`, computed LIVE from current standings.

    Used by the preview (`preview_bracket`) and nowhere else: it must never
    be mistaken for the frozen snapshot, because it changes every time a
    group-stage result is loaded or corrected.
    """
    lookup: SeedLookup = {}
    for zone_letter, zone_id in (("A", zone_a_id), ("B", zone_b_id)):
        for row in get_standings(session, zone_id):
            lookup[(zone_letter, row.position)] = row.team_id
    return lookup


def _seed_lookup_from_snapshot(session: Session, zone_a_id: int, zone_b_id: int) -> SeedLookup:
    """`(zone_letter, position) -> team_id`, read from the frozen `playoff_seeds` snapshot.

    Used by `build_bracket` and `advance` — the only two places a real
    bracket is resolved — so a group-stage correction made after the bracket
    was drawn cannot reseed a playoff spot that is already being played for.
    """
    lookup: SeedLookup = {}
    for zone_letter, zone_id in (("A", zone_a_id), ("B", zone_b_id)):
        for seed in session.exec(select(PlayoffSeed).where(PlayoffSeed.zone_id == zone_id)).all():
            lookup[(zone_letter, seed.position)] = seed.team_id
    return lookup


SeedLabels = dict[int, str]


def _seed_labels(seed_lookup: SeedLookup) -> SeedLabels:
    """Invert `(zone_letter, position) -> team_id` into `team_id -> "3A"`.

    The label a team's seed chip shows, for every team the lookup covers —
    which is every team in both zones, since both `_seed_lookup_from_snapshot`
    and `_seed_lookup_from_standings` walk a zone's full standings, not just
    the handful of positions `BRACKET_TEMPLATE` names directly. That is what
    lets `_team_summary` give a correct seed to a round-2, semifinal or final
    team too, not only the ones a template entry seeds directly.
    """
    return {team_id: f"{position}{zone_letter}" for (zone_letter, position), team_id in seed_lookup.items()}


def _snapshot_seeds(session: Session, zone_a_id: int, zone_b_id: int) -> None:
    """Write one `PlayoffSeed` row per team, from each zone's current standings."""
    for zone_id in (zone_a_id, zone_b_id):
        for row in get_standings(session, zone_id):
            session.add(PlayoffSeed(zone_id=zone_id, team_id=row.team_id, position=row.position))
    session.flush()


def _resolve_source(
    session: Session, source: _Source | None, seed_lookup: SeedLookup
) -> tuple[str, int | None]:
    """The state of one side of a node: `"known"`, `"dead"` or `"pending"`.

    `"known"` comes with the team id. `"dead"` means this side will never be
    filled (a missing seed, or a node that resolved as a bye with nothing on
    either side). `"pending"` means it depends on a real match that has not
    been played yet — genuinely undecided, not absent.

    The seed side reads `seed_lookup` rather than querying `PlayoffSeed`
    itself so the same resolver serves both the real bracket (built from the
    frozen snapshot) and the live preview (built from current standings) —
    see `_seed_lookup_from_snapshot`/`_seed_lookup_from_standings`.
    """
    if source is None:
        return "dead", None

    if isinstance(source, _SeedSource):
        team_id = seed_lookup.get((source.zone_letter, source.position))
        return ("known", team_id) if team_id is not None else ("dead", None)

    node = session.exec(
        select(PlayoffMatch).where(PlayoffMatch.round == source.round, PlayoffMatch.slot == source.slot)
    ).one()

    if node.status == PlayoffMatchStatus.BYE:
        if node.team_a_id is not None:
            return "known", node.team_a_id
        if node.team_b_id is not None:
            return "known", node.team_b_id
        return "dead", None

    if node.match_id is not None:
        match = session.get(Match, node.match_id)
        winner_id = winner_team_id(match, get_sets(session, node.match_id))
        return ("known", winner_id) if winner_id is not None else ("pending", None)

    return "pending", None


def _settle(session: Session, round_: PlayoffRound, slot: int, seed_lookup: SeedLookup) -> None:
    """Decide (or redecide) one node from its sources, cascading forward.

    Safe to call any number of times: a node whose match has already been
    played is left alone (its outcome is final), but everything else —
    including a node this same call resolves as a bye — is recomputed fresh
    from `_resolve_source` every time. That is what lets a correction just
    call this again instead of needing separate patch-up logic.
    """
    node = session.exec(
        select(PlayoffMatch).where(PlayoffMatch.round == round_, PlayoffMatch.slot == slot)
    ).one()

    existing_match = session.get(Match, node.match_id) if node.match_id is not None else None
    if existing_match is not None and existing_match.status == MatchStatus.PLAYED:
        return

    source_a, source_b = NODE_SOURCES[(round_, slot)]
    state_a, team_a = _resolve_source(session, source_a, seed_lookup)
    state_b, team_b = _resolve_source(session, source_b, seed_lookup)

    if state_a == "known" and state_b == "known":
        if existing_match is None:
            new_match = Match(
                team_a_id=team_a,
                team_b_id=team_b,
                date=_placeholder_date(),
                status=MatchStatus.PENDING,
            )
            session.add(new_match)
            session.flush()
            node.match_id = new_match.id
        else:
            existing_match.team_a_id = team_a
            existing_match.team_b_id = team_b
            session.add(existing_match)
        node.team_a_id = team_a
        node.team_b_id = team_b
        node.status = PlayoffMatchStatus.PENDING
        session.add(node)
        session.flush()
        return

    # Neither side is a genuine, still-to-be-played match at this point: any
    # match left over from before a correction is stale and gets dropped.
    if existing_match is not None:
        session.delete(existing_match)
        node.match_id = None

    if state_a == "pending" or state_b == "pending":
        # At least one side is still waiting on a real match. Record whatever
        # IS known so far, but do not decide the node yet.
        node.team_a_id = team_a if state_a == "known" else None
        node.team_b_id = team_b if state_b == "known" else None
        node.status = PlayoffMatchStatus.PENDING
        session.add(node)
        session.flush()
        return

    # Both sides are settled and at most one is "known" — a bye, possibly an
    # empty one.
    node.team_a_id = team_a if state_a == "known" else None
    node.team_b_id = team_b if state_b == "known" else None
    node.status = PlayoffMatchStatus.BYE
    session.add(node)
    session.flush()

    winner_id = team_a if state_a == "known" else (team_b if state_b == "known" else None)
    if winner_id is not None and node.next_match_id is not None:
        destination = session.get(PlayoffMatch, node.next_match_id)
        _settle(session, destination.round, destination.slot, seed_lookup)


def get_playoff_match_ids(session: Session) -> set[int]:
    """Every real `Match` id that is a playoff bracket node.

    The shared source of truth for "is this match a playoff match" — used to
    keep playoff matches out of the public API until the public bracket page
    exists (`app.public.router`), out of public voting (`app.votes.service`),
    and out of the pending-group-stage guard below.
    """
    return set(
        session.exec(select(PlayoffMatch.match_id).where(PlayoffMatch.match_id.is_not(None))).all()
    )


def is_playoff_match(session: Session, match_id: int) -> bool:
    return (
        session.exec(select(PlayoffMatch.id).where(PlayoffMatch.match_id == match_id)).first()
        is not None
    )


def _pending_group_stage_matches(session: Session) -> list[Match]:
    """Group-stage matches still pending: not linked to any playoff node.

    At the point `build_bracket` can run, no playoff node exists yet, so in
    practice this is simply every pending match — but it is written against
    the actual linkage (rather than just "every pending match") so it stays
    correct if this is ever called again once a bracket already exists.
    """
    linked = get_playoff_match_ids(session)
    pending = session.exec(select(Match).where(Match.status == MatchStatus.PENDING)).all()
    return [match for match in pending if match.id not in linked]


def _group_stage_pending_error(session: Session, pending: list[Match]) -> dict:
    team_ids = {team_id for match in pending for team_id in (match.team_a_id, match.team_b_id)}
    teams_by_id = {
        team.id: team for team in session.exec(select(Team).where(Team.id.in_(team_ids))).all()
    }
    # No bracket exists yet at this point — there is no frozen snapshot to
    # read from — so this reads the same live standings the projection does.
    # It is meaningful here too: it is each team's current zone position,
    # which is exactly what generating now (with `force`) would seed them by.
    zone_a_id, zone_b_id = _ordered_zone_ids(session)
    seed_labels = _seed_labels(_seed_lookup_from_standings(session, zone_a_id, zone_b_id))
    payload = GroupStagePendingError(
        detail="The group stage still has pending matches. Pass force=true to generate anyway.",
        pending_count=len(pending),
        pending_matches=[
            PendingGroupMatchRead(
                id=match.id,
                team_a=_team_summary(teams_by_id.get(match.team_a_id), seed_labels),
                team_b=_team_summary(teams_by_id.get(match.team_b_id), seed_labels),
            )
            for match in pending
        ],
    )
    return payload.model_dump()


def build_bracket(session: Session, force: bool = False) -> BracketRead:
    """Close the group stage: snapshot the standings and lay out the bracket.

    Refuses to run twice — the seeds are a one-time snapshot, and a second
    call would either duplicate them or silently redraw a bracket that may
    already have matches in progress.

    Also refuses, unless `force` is set, to run while group-stage matches are
    still pending: generating early freezes a half-complete standings
    snapshot and seeds the whole bracket wrong. `force` exists because a
    withdrawn pair leaves its remaining matches pending forever in this
    league, which would otherwise make the bracket impossible to generate.
    """
    if session.exec(select(PlayoffMatch)).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The playoff bracket already exists",
        )

    if not force:
        pending = _pending_group_stage_matches(session)
        if pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_group_stage_pending_error(session, pending),
            )

    zone_a_id, zone_b_id = _ordered_zone_ids(session)
    _snapshot_seeds(session, zone_a_id, zone_b_id)
    seed_lookup = _seed_lookup_from_snapshot(session, zone_a_id, zone_b_id)

    nodes_by_key: dict[tuple[PlayoffRound, int], PlayoffMatch] = {}
    for template in BRACKET_TEMPLATE:
        node = PlayoffMatch(round=template.round, slot=template.slot)
        session.add(node)
        session.flush()
        nodes_by_key[(template.round, template.slot)] = node

    for template in BRACKET_TEMPLATE:
        if template.next_round is None:
            continue
        node = nodes_by_key[(template.round, template.slot)]
        node.next_match_id = nodes_by_key[(template.next_round, template.next_slot)].id
        node.next_side = template.next_side.value
        session.add(node)
    session.flush()

    for playoff_round in _ROUND_ORDER:
        for template in BRACKET_TEMPLATE:
            if template.round is playoff_round:
                _settle(session, template.round, template.slot, seed_lookup)

    session.commit()
    return get_bracket(session)


def _reset_downstream(session: Session, node: PlayoffMatch) -> None:
    """Unplay every match downstream of `node` that trusted its now-stale winner.

    Only undoes RESULTS — through `matches_service.delete_result`, so sets,
    photo and comment logic is not reinvented here — and never repopulates
    anything itself. The `_settle` cascade that `advance` runs right after
    this does that, from scratch, once nothing blocks it from recomputing.
    """
    if node.next_match_id is None:
        return

    destination = session.get(PlayoffMatch, node.next_match_id)
    if destination.match_id is None:
        return  # nothing was ever decided past this point

    match = session.get(Match, destination.match_id)
    if match.status == MatchStatus.PLAYED:
        _reset_downstream(session, destination)
        matches_service.delete_result(session, destination.match_id)


def advance(session: Session, playoff_match: PlayoffMatch) -> None:
    """Propagate a decided node's winner into the node it feeds.

    Called after the match linked to `playoff_match` gets a result, or has
    its result corrected. Handles both the same way: any downstream node that
    already trusted the old winner is unplayed first (`_reset_downstream`),
    then the destination — and anything further it cascades into — is
    recomputed from scratch (`_settle`). For a fresh result there is nothing
    to unplay, so the reset step is a no-op.
    """
    if playoff_match.next_match_id is None:
        return  # the final: nowhere further for a winner to go

    _reset_downstream(session, playoff_match)
    destination = session.get(PlayoffMatch, playoff_match.next_match_id)
    zone_a_id, zone_b_id = _ordered_zone_ids(session)
    seed_lookup = _seed_lookup_from_snapshot(session, zone_a_id, zone_b_id)
    _settle(session, destination.round, destination.slot, seed_lookup)
    session.commit()


# --- Presentation ---------------------------------------------------------------


def _team_summary(team: Team | None, seed_labels: SeedLabels) -> PlayoffTeamRead | None:
    if team is None:
        return None
    return PlayoffTeamRead(
        id=team.id,
        player_one_name=team.player_one_name,
        player_two_name=team.player_two_name,
        photo_url=team.photo_url,
        # Falls back to "" only for a team `seed_labels` genuinely has no
        # position for, which should not happen — every team in the league
        # has a zone standing — but a bracket slot is not the place to raise
        # over a data problem the standings module already owns.
        seed=seed_labels.get(team.id, ""),
    )


def _match_read(match: Match, sets: list[MatchSet]) -> MatchRead:
    return MatchRead(
        id=match.id,
        team_a_id=match.team_a_id,
        team_b_id=match.team_b_id,
        date=match.date,
        time=match.time,
        venue=match.venue,
        status=match.status,
        sets=[SetRead.model_validate(s, from_attributes=True) for s in sets],
        winner_team_id=winner_team_id(match, sets),
        photo_url=match.photo_url,
        comment=match.comment,
    )


def get_bracket(session: Session) -> BracketRead:
    """The single source for `GET /playoffs/bracket`.

    Dispatches between the two modes ITSELF, rather than leaving it to a
    query flag or the caller, so there is no way to ask this endpoint for a
    projection once the real bracket exists: `official` reads only the
    persisted nodes and never consults live standings; `projection` never
    persists anything and stops being reachable the moment a bracket is
    generated.
    """
    if session.exec(select(PlayoffMatch)).first() is not None:
        return _official_bracket(session)
    return _project_bracket(session)


def _official_bracket(session: Session) -> BracketRead:
    """The persisted bracket, resolved for the front end in a handful of queries.

    Every id a node carries (both teams, its match, that match's sets) is
    fetched in bulk up front and joined in memory, instead of one query per
    node — the point being that a 19-node bracket costs the same four
    queries whether it renders one round or five.
    """
    nodes = list(
        session.exec(select(PlayoffMatch).order_by(PlayoffMatch.round, PlayoffMatch.slot)).all()
    )

    team_ids = {
        team_id for node in nodes for team_id in (node.team_a_id, node.team_b_id) if team_id is not None
    }
    teams_by_id = (
        {team.id: team for team in session.exec(select(Team).where(Team.id.in_(team_ids))).all()}
        if team_ids
        else {}
    )
    zone_a_id, zone_b_id = _ordered_zone_ids(session)
    seed_labels = _seed_labels(_seed_lookup_from_snapshot(session, zone_a_id, zone_b_id))

    match_ids = [node.match_id for node in nodes if node.match_id is not None]
    matches_by_id = (
        {match.id: match for match in session.exec(select(Match).where(Match.id.in_(match_ids))).all()}
        if match_ids
        else {}
    )

    sets_by_match: dict[int, list[MatchSet]] = defaultdict(list)
    if match_ids:
        for match_set in session.exec(
            select(MatchSet).where(MatchSet.match_id.in_(match_ids)).order_by(MatchSet.set_number)
        ).all():
            sets_by_match[match_set.match_id].append(match_set)

    nodes_by_round: dict[PlayoffRound, dict[int, PlayoffNodeRead]] = defaultdict(dict)
    for node in nodes:
        nodes_by_round[node.round][node.slot] = PlayoffNodeRead(
            id=node.id,
            slot=node.slot,
            status=node.status,
            team_a=_team_summary(teams_by_id.get(node.team_a_id), seed_labels),
            team_b=_team_summary(teams_by_id.get(node.team_b_id), seed_labels),
            match=(
                _match_read(matches_by_id[node.match_id], sets_by_match[node.match_id])
                if node.match_id is not None
                else None
            ),
        )

    return BracketRead(
        mode=BracketMode.OFFICIAL,
        rounds=[
            PlayoffRoundRead(
                round=playoff_round,
                nodes=[
                    nodes_by_round[playoff_round][slot]
                    for slot in DRAW_ORDER[playoff_round]
                    if slot in nodes_by_round[playoff_round]
                ],
            )
            for playoff_round in _ROUND_ORDER
            if playoff_round in nodes_by_round
        ],
        pending_group_matches=None,
    )


def _played_playoff_match_count(session: Session) -> int:
    match_ids = list(get_playoff_match_ids(session))
    if not match_ids:
        return 0
    return len(
        list(
            session.exec(
                select(Match.id).where(Match.id.in_(match_ids), Match.status == MatchStatus.PLAYED)
            ).all()
        )
    )


def wipe_bracket(session: Session, force: bool = False) -> None:
    """Delete the bracket, its seeds, and every match it generated.

    For re-generating during testing, per the design brief. A generated
    match's sets and votes go with it — nothing about it is meant to outlive
    the bracket that created it.

    Refuses, unless `force` is set, once any bracket match already has a
    loaded result — wiping a bracket that has actually been played discards
    real results, not just a draft.
    """
    if not force:
        played_count = _played_playoff_match_count(session)
        if played_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=PlayoffResultsLoadedError(
                    detail=(
                        "The bracket already has loaded results. "
                        "Pass force=true to wipe it anyway."
                    ),
                    played_count=played_count,
                ).model_dump(),
            )

    match_ids = list(get_playoff_match_ids(session))

    if match_ids:
        for match_set in session.exec(select(MatchSet).where(MatchSet.match_id.in_(match_ids))).all():
            session.delete(match_set)
        for vote in session.exec(select(MatchVote).where(MatchVote.match_id.in_(match_ids))).all():
            session.delete(vote)
        for match in session.exec(select(Match).where(Match.id.in_(match_ids))).all():
            session.delete(match)

    for node in session.exec(select(PlayoffMatch)).all():
        session.delete(node)
    for seed in session.exec(select(PlayoffSeed)).all():
        session.delete(seed)

    session.commit()


def _project_bracket(session: Session) -> BracketRead:
    """Live projection of what the bracket would look like right now.

    Only reachable through `get_bracket`, and only before a bracket exists.
    Resolves `BRACKET_TEMPLATE` against CURRENT standings (never
    `playoff_seeds` — the snapshot table stays untouched by this path, and
    would be stale the moment it existed anyway) and writes nothing — no
    `PlayoffSeed`, no `PlayoffMatch`, no `Match`. Only a node whose side is
    fed directly by a seed can be populated this way: round 1 (both sides)
    and each quarterfinal's direct qualifier (`BRACKET_TEMPLATE`'s
    `seed_a`). Anything fed by another node's winner is left empty, because
    that winner does not exist without a real match being played.
    """
    zone_a_id, zone_b_id = _ordered_zone_ids(session)
    seed_lookup = _seed_lookup_from_standings(session, zone_a_id, zone_b_id)
    seed_labels = _seed_labels(seed_lookup)

    team_ids = set(seed_lookup.values())
    teams_by_id = (
        {team.id: team for team in session.exec(select(Team).where(Team.id.in_(team_ids))).all()}
        if team_ids
        else {}
    )

    nodes_by_round: dict[PlayoffRound, dict[int, PlayoffNodeRead]] = defaultdict(dict)
    for template in BRACKET_TEMPLATE:
        team_a_id = seed_lookup.get(template.seed_a) if template.seed_a is not None else None
        team_b_id = seed_lookup.get(template.seed_b) if template.seed_b is not None else None

        # Only a node whose BOTH sides are seeds (round 1) can be
        # conclusively called a bye from standings alone. A quarterfinal's
        # unresolved side, or anything in round 2 and beyond, is waiting on a
        # real match this preview does not play — that is "pending", not a
        # bye, however many of its sides currently show `None`.
        both_sides_are_seeded = template.seed_a is not None and template.seed_b is not None
        if both_sides_are_seeded and (team_a_id is None or team_b_id is None):
            node_status = PlayoffMatchStatus.BYE
        else:
            node_status = PlayoffMatchStatus.PENDING

        nodes_by_round[template.round][template.slot] = PlayoffNodeRead(
            id=None,
            slot=template.slot,
            status=node_status,
            team_a=_team_summary(teams_by_id.get(team_a_id), seed_labels),
            team_b=_team_summary(teams_by_id.get(team_b_id), seed_labels),
            match=None,
        )

    return BracketRead(
        mode=BracketMode.PROJECTION,
        rounds=[
            PlayoffRoundRead(
                round=playoff_round,
                nodes=[nodes_by_round[playoff_round][slot] for slot in DRAW_ORDER[playoff_round]],
            )
            for playoff_round in _ROUND_ORDER
        ],
        pending_group_matches=len(_pending_group_stage_matches(session)),
    )
