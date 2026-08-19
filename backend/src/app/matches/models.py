import datetime
import enum

from sqlalchemy import CheckConstraint, Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.models import TimestampMixin

# One tweet. The comment is a jab at the losing pair, not a match report, and a
# hard cap keeps the public result card from growing a wall of text.
COMMENT_MAX_LENGTH = 280


class MatchStatus(str, enum.Enum):
    """A match is `played` only once its sets have been loaded."""

    PENDING = "pending"
    PLAYED = "played"


class MatchVenue(str, enum.Enum):
    """The clubs the league plays at.

    A closed list and not free text: the venue is read at a glance on the home
    page, and "Boss", "boss padel" and "Bos Padel" would be three clubs there.
    `OTHER` is the escape hatch for the odd court nobody plays at twice.
    """

    BOSS_PADEL = "boss_padel"
    COFAM = "cofam"
    ARENA = "arena"
    INDOOR = "indoor"
    PADELON = "padelon"
    PUNTO_DE_ORO = "punto_de_oro"
    OTHER = "otro"


class Match(TimestampMixin, table=True):
    """A match between two teams.

    Has no `zone_id` on purpose: the zone is derived from the teams, which are
    validated to belong to the same zone when the match is created.
    The winner is not stored either — it is computed from the sets.

    `photo_url` and `comment` hang off the result, not off the scoreboard: a
    correction of the marker keeps them, undoing the result drops them.

    `time` and `venue` are optional: a match is scheduled before the pairs
    agree on where and at what time, and the matches already loaded have
    neither.
    """

    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("team_a_id != team_b_id", name="ck_matches_distinct_teams"),
    )

    id: int | None = Field(default=None, primary_key=True)
    team_a_id: int = Field(foreign_key="teams.id", index=True)
    team_b_id: int = Field(foreign_key="teams.id", index=True)
    date: datetime.date = Field(index=True)
    time: datetime.time | None = Field(default=None)
    venue: MatchVenue | None = Field(
        default=None,
        sa_column=Column(
            SAEnum(
                MatchVenue,
                name="match_venue",
                # Without this, Postgres would store the member NAME
                # (`BOSS_PADEL`) instead of the value the API speaks.
                values_callable=lambda members: [member.value for member in members],
            ),
            nullable=True,
        ),
    )
    status: MatchStatus = Field(
        default=MatchStatus.PENDING,
        sa_column=Column(
            SAEnum(
                MatchStatus,
                name="match_status",
                values_callable=lambda members: [member.value for member in members],
            ),
            nullable=False,
        ),
    )
    photo_url: str | None = Field(default=None, max_length=255)
    comment: str | None = Field(default=None, max_length=COMMENT_MAX_LENGTH)


class MatchSet(SQLModel, table=True):
    """A single set inside a match.

    A match has two or three sets, or none while it is pending. Correcting a
    result deletes every set of the match and creates the new ones.
    """

    __tablename__ = "match_sets"
    __table_args__ = (
        UniqueConstraint("match_id", "set_number", name="uq_match_sets_match_set_number"),
    )

    id: int | None = Field(default=None, primary_key=True)
    match_id: int = Field(foreign_key="matches.id", index=True)
    set_number: int = Field(ge=1)
    team_a_games: int = Field(ge=0)
    team_b_games: int = Field(ge=0)
