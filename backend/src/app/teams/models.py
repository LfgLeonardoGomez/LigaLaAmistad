import enum

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field

from app.core.models import TimestampMixin


class TeamStatus(str, enum.Enum):
    """League status of a team. `withdrawn` keeps history and still counts for rivals."""

    ACTIVE = "active"
    WITHDRAWN = "withdrawn"


class Team(TimestampMixin, table=True):
    """A pair of players. Never deleted: leaving the league sets status to `withdrawn`."""

    __tablename__ = "teams"

    id: int | None = Field(default=None, primary_key=True)
    zone_id: int = Field(foreign_key="zones.id", index=True)
    player_one_name: str = Field(max_length=50)
    player_two_name: str = Field(max_length=50)
    photo_url: str | None = Field(default=None, max_length=255)
    status: TeamStatus = Field(
        default=TeamStatus.ACTIVE,
        sa_column=Column(
            SAEnum(
                TeamStatus,
                name="team_status",
                values_callable=lambda members: [member.value for member in members],
            ),
            nullable=False,
        ),
    )
