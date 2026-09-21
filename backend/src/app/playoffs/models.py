"""Playoffs: the bracket built once the group stage closes.

No match logic lives here. A playoff node is a slot in the bracket — who
plays whom, and where the winner goes next — and the moment both of its
sides are known it is backed by an ordinary row in `matches`, so every
behaviour a match already has (sets, winner, correction, photo, comment,
votes) keeps working exactly as it does in the group stage, with nothing
duplicated in this module.
"""

import enum
from typing import NamedTuple

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.core.models import TimestampMixin


class PlayoffRound(str, enum.Enum):
    """The five rounds of the bracket, in play order."""

    ROUND_1 = "round_1"
    ROUND_2 = "round_2"
    QUARTERFINAL = "quarterfinal"
    SEMIFINAL = "semifinal"
    FINAL = "final"


class PlayoffMatchStatus(str, enum.Enum):
    """Whether a node still needs its match played, or was decided without one.

    `BYE` covers both a node left with a single team (it advances untested,
    no match is ever created for it) and one left with none (an under-strength
    zone leaves the slot empty; there is nothing to advance either).
    """

    PENDING = "pending"
    BYE = "bye"


class PlayoffSide(str, enum.Enum):
    """Which side of a downstream node a winner is written into."""

    A = "a"
    B = "b"


class PlayoffSeed(TimestampMixin, table=True):
    """Immutable snapshot of one zone's group-stage standing, taken once.

    The bracket is wired against POSITIONS (1st, 2nd, 3rd...), not against
    teams directly, because standings are never stored — they are recomputed
    live from played matches (see `app.standings.service`). If the bracket
    read a team's seed from live standings, correcting an already-played
    group-stage result after the bracket was drawn could reshuffle who is
    seeded where, silently reassigning a playoff spot that was already being
    played for. This table freezes the ranking at the moment the bracket is
    built and is never touched again.
    """

    __tablename__ = "playoff_seeds"
    __table_args__ = (
        UniqueConstraint("zone_id", "position", name="uq_playoff_seeds_zone_position"),
        UniqueConstraint("team_id", name="uq_playoff_seeds_team"),
    )

    id: int | None = Field(default=None, primary_key=True)
    zone_id: int = Field(foreign_key="zones.id", index=True)
    team_id: int = Field(foreign_key="teams.id", index=True)
    position: int = Field(ge=1)


class PlayoffMatch(TimestampMixin, table=True):
    """One node of the bracket: structure, not an event.

    `team_a_id`/`team_b_id` are nullable because a node exists before it is
    known who plays it — every round-2 node, for instance, is created at the
    same time as the round-1 nodes that feed it, before either round-1 match
    has been played. `match_id` stays null for exactly as long: only once
    both sides are known does a `Match` row get created and linked here, and
    from that point on every result/scoring concern lives on that row, not on
    this one.

    `next_match_id`/`next_side` point to the node the winner advances to.
    Both are null only for the final, which has nowhere left to send a
    winner.
    """

    __tablename__ = "playoff_matches"
    __table_args__ = (
        UniqueConstraint("round", "slot", name="uq_playoff_matches_round_slot"),
    )

    id: int | None = Field(default=None, primary_key=True)
    round: PlayoffRound = Field(
        sa_column=Column(
            SAEnum(
                PlayoffRound,
                name="playoff_round",
                # Without this, Postgres would store the member NAME
                # (`ROUND_1`) instead of the value the API speaks.
                values_callable=lambda members: [member.value for member in members],
            ),
            nullable=False,
        ),
    )
    slot: int = Field(ge=1)
    team_a_id: int | None = Field(default=None, foreign_key="teams.id")
    team_b_id: int | None = Field(default=None, foreign_key="teams.id")
    match_id: int | None = Field(default=None, foreign_key="matches.id")
    next_match_id: int | None = Field(default=None, foreign_key="playoff_matches.id")
    # Plain text, not a Postgres enum: it only ever takes `PlayoffSide.A` or
    # `PlayoffSide.B`'s value, and a third native enum type for two letters
    # is not worth the migration ceremony the round and status enums already
    # justify.
    next_side: str | None = Field(default=None, max_length=1)
    status: PlayoffMatchStatus = Field(
        default=PlayoffMatchStatus.PENDING,
        sa_column=Column(
            SAEnum(
                PlayoffMatchStatus,
                name="playoff_match_status",
                values_callable=lambda members: [member.value for member in members],
            ),
            nullable=False,
        ),
    )


class BracketNodeTemplate(NamedTuple):
    """One fixed slot of the bracket, and where its winner goes next.

    `seed_a`/`seed_b` are `(zone_letter, position)` pairs read straight off
    the group-stage snapshot; `None` means that side is filled later, by
    another node's winner instead of a seed.
    """

    round: PlayoffRound
    slot: int
    seed_a: tuple[str, int] | None
    seed_b: tuple[str, int] | None
    next_round: PlayoffRound | None
    next_slot: int | None
    next_side: PlayoffSide | None


# The bracket is a fixed tournament-design decision, not something an
# algorithm derives from the seed count — so it is data, not code that
# computes it.
#
# The seeding is deliberate, not arbitrary:
#
# - `1A` and `1B` are drawn into opposite halves of the bracket (`1A` feeds
#   the semifinal on the side the quarterfinal-1 winner reaches; `1B` feeds
#   the other), so the two zone winners can only meet in the final.
# - `2A` is drawn opposite `1A`'s own quarterfinal (it seeds quarterfinal-3,
#   which lands in the OTHER semifinal from quarterfinal-1's `1A`), so the
#   same-zone rematch of the top two pairs of zone A is also final-only.
# - Every direct qualifier (`1A`, `2A`, `1B`, `2B`) is paired in its
#   quarterfinal against the round-2 winner expected to be weakest: the one
#   that survived two rounds against the bottom half of the OTHER zone's
#   standings, rather than a round-2 slot fed by higher seeds.
#
# A future reader must not "simplify" this table by re-deriving it from a
# loop — the crossings above are the whole point, and a generic loop will not
# reproduce them by accident.
BRACKET_TEMPLATE: tuple[BracketNodeTemplate, ...] = (
    # --- Round 1 --------------------------------------------------------------
    BracketNodeTemplate(PlayoffRound.ROUND_1, 1, ("A", 3), ("B", 10), PlayoffRound.ROUND_2, 1, PlayoffSide.A),
    BracketNodeTemplate(PlayoffRound.ROUND_1, 5, ("A", 7), ("B", 6), PlayoffRound.ROUND_2, 1, PlayoffSide.B),
    BracketNodeTemplate(PlayoffRound.ROUND_1, 8, ("A", 10), ("B", 3), PlayoffRound.ROUND_2, 2, PlayoffSide.A),
    BracketNodeTemplate(PlayoffRound.ROUND_1, 4, ("A", 6), ("B", 7), PlayoffRound.ROUND_2, 2, PlayoffSide.B),
    BracketNodeTemplate(PlayoffRound.ROUND_1, 2, ("A", 4), ("B", 9), PlayoffRound.ROUND_2, 3, PlayoffSide.A),
    BracketNodeTemplate(PlayoffRound.ROUND_1, 6, ("A", 8), ("B", 5), PlayoffRound.ROUND_2, 3, PlayoffSide.B),
    BracketNodeTemplate(PlayoffRound.ROUND_1, 7, ("A", 9), ("B", 4), PlayoffRound.ROUND_2, 4, PlayoffSide.A),
    BracketNodeTemplate(PlayoffRound.ROUND_1, 3, ("A", 5), ("B", 8), PlayoffRound.ROUND_2, 4, PlayoffSide.B),
    # --- Round 2 ----------------------------------------------------------------
    BracketNodeTemplate(PlayoffRound.ROUND_2, 1, None, None, PlayoffRound.QUARTERFINAL, 2, PlayoffSide.B),
    BracketNodeTemplate(PlayoffRound.ROUND_2, 2, None, None, PlayoffRound.QUARTERFINAL, 3, PlayoffSide.B),
    BracketNodeTemplate(PlayoffRound.ROUND_2, 3, None, None, PlayoffRound.QUARTERFINAL, 4, PlayoffSide.B),
    BracketNodeTemplate(PlayoffRound.ROUND_2, 4, None, None, PlayoffRound.QUARTERFINAL, 1, PlayoffSide.B),
    # --- Quarterfinal -------------------------------------------------------------
    BracketNodeTemplate(PlayoffRound.QUARTERFINAL, 1, ("A", 1), None, PlayoffRound.SEMIFINAL, 1, PlayoffSide.A),
    BracketNodeTemplate(PlayoffRound.QUARTERFINAL, 2, ("B", 2), None, PlayoffRound.SEMIFINAL, 1, PlayoffSide.B),
    BracketNodeTemplate(PlayoffRound.QUARTERFINAL, 3, ("A", 2), None, PlayoffRound.SEMIFINAL, 2, PlayoffSide.A),
    BracketNodeTemplate(PlayoffRound.QUARTERFINAL, 4, ("B", 1), None, PlayoffRound.SEMIFINAL, 2, PlayoffSide.B),
    # --- Semifinal ------------------------------------------------------------
    BracketNodeTemplate(PlayoffRound.SEMIFINAL, 1, None, None, PlayoffRound.FINAL, 1, PlayoffSide.A),
    BracketNodeTemplate(PlayoffRound.SEMIFINAL, 2, None, None, PlayoffRound.FINAL, 1, PlayoffSide.B),
    # --- Final ------------------------------------------------------------------
    BracketNodeTemplate(PlayoffRound.FINAL, 1, None, None, None, None, None),
)
