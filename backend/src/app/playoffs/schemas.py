import enum

from sqlmodel import SQLModel

from app.matches.schemas import MatchRead
from app.playoffs.models import PlayoffMatchStatus, PlayoffRound


class BracketMode(str, enum.Enum):
    """Which of the two things `GET /playoffs/bracket` is currently showing.

    `PROJECTION`: no bracket has been generated yet — a live, unpersisted
    guess from current standings. `OFFICIAL`: the bracket has been
    generated — the real, persisted thing. The two never coexist: the moment
    a bracket is generated, the projection is gone and this endpoint cannot
    be asked for it again.
    """

    PROJECTION = "projection"
    OFFICIAL = "official"


class PlayoffTeamRead(SQLModel):
    """Enough to label a bracket slot and show its pair without a second request.

    `photo_url` rides along because the bracket modal shows each pair's photo
    on click; without it the front end would need to re-fetch the team just
    to render what this endpoint already has in hand.

    `seed` (`"3A"`, `"10B"`) is a property of the TEAM within this playoff,
    not of the node it currently occupies — every team has a zone position
    whether it got here by seed or by winning its way here, so this is filled
    in for every team in every round, not just round 1 and a quarterfinal's
    direct qualifier. That is deliberate: it is what the front end reads for
    the seed chip, instead of keeping its own copy of which side of which
    node is a seed. See `_team_summary` for where it comes from in each mode.
    """

    id: int
    player_one_name: str
    player_two_name: str
    photo_url: str | None = None
    seed: str


class PlayoffNodeRead(SQLModel):
    """One bracket slot, with both teams resolved and its match, if it has one.

    `team_a`/`team_b` are `None` exactly when the node's `status` is `bye`
    with that side unresolved, or when the node is still waiting on an
    earlier round to finish.

    `id` is `None` for a node that only exists as a projection (see
    `BracketRead.mode`), since nothing has been persisted for it to be the
    id of.
    """

    id: int | None = None
    slot: int
    status: PlayoffMatchStatus
    team_a: PlayoffTeamRead | None = None
    team_b: PlayoffTeamRead | None = None
    match: MatchRead | None = None


class PlayoffRoundRead(SQLModel):
    """One round's nodes, in DRAW order — not slot order.

    Draw order is the order the bracket is drawn on paper: walk the tree back
    from the final, each node before the one it feeds. Rendered slot by
    slot, that order is what keeps every connector line from one round to the
    next straight; slot order draws crossings almost everywhere except the
    last three rounds, where slot order and draw order happen to coincide.
    See `app.playoffs.service.DRAW_ORDER` for how it is computed from
    `BRACKET_TEMPLATE`. `slot` itself is untouched — it is still the node's
    stable identity, just not the array position.
    """

    round: PlayoffRound
    nodes: list[PlayoffNodeRead]


class BracketRead(SQLModel):
    """The whole bracket, rounds in play order, each carrying its own nodes.

    The single response shape for `GET /playoffs/bracket`, whichever mode it
    is in (see `mode`). In `official` mode it is built from a handful of bulk
    queries rather than one lookup per node, so the front end can render it
    column by column without causing an N+1 on the way there; in
    `projection` mode nothing is persisted at all.

    `pending_group_matches` is the count of group-stage matches still
    pending — the same figure that blocks `POST /playoffs/generate` without
    `force` — and is only meaningful in `projection` mode. It is `None` in
    `official` mode, where the group stage is already closed.
    """

    mode: BracketMode
    rounds: list[PlayoffRoundRead]
    pending_group_matches: int | None = None


class GenerateBracketIn(SQLModel):
    """`force` skips the pending-group-stage guard.

    Needed because a withdrawn pair leaves its remaining matches `pending`
    forever in this league — without an escape hatch, one withdrawal would
    make the bracket impossible to ever generate.
    """

    model_config = {"extra": "forbid"}

    force: bool = False


class PendingGroupMatchRead(SQLModel):
    """One group-stage match the generate guard is refusing to ignore."""

    id: int
    team_a: PlayoffTeamRead
    team_b: PlayoffTeamRead


class GroupStagePendingError(SQLModel):
    """Body of the 409 `POST /playoffs/generate` raises when matches are still pending.

    Structured on purpose — not a bare string — so the admin's confirm dialog
    can name exactly which matches are being left behind instead of the
    admin having to go find out.
    """

    detail: str
    pending_count: int
    pending_matches: list[PendingGroupMatchRead]


class PlayoffResultsLoadedError(SQLModel):
    """Body of the 409 `DELETE /playoffs` raises once a bracket match has a result."""

    detail: str
    played_count: int
