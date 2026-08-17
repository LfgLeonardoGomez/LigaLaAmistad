import datetime
import enum

from sqlalchemy import CheckConstraint, Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.models import TimestampMixin


class MatchStatus(str, enum.Enum):
    """A match is `played` only once its sets have been loaded."""

    PENDING = "pending"
    PLAYED = "played"


class Match(TimestampMixin, table=True):
    """A match between two teams.

    Has no `zone_id` on purpose: the zone is derived from the teams, which are
    validated to belong to the same zone when the match is created.
    The winner is not stored either — it is computed from the sets.
    """

    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("team_a_id != team_b_id", name="ck_matches_distinct_teams"),
    )

    id: int | None = Field(default=None, primary_key=True)
    team_a_id: int = Field(foreign_key="teams.id", index=True)
    team_b_id: int = Field(foreign_key="teams.id", index=True)
    date: datetime.date = Field(index=True)
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
