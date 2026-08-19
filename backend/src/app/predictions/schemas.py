import datetime

from sqlmodel import Field, SQLModel

from app.predictions.models import DEFAULT_POLL_DAYS
from app.votes.models import VOTER_KEY_MAX_LENGTH, VOTER_KEY_MIN_LENGTH


class ZonePick(SQLModel):
    model_config = {"extra": "forbid"}

    zone_id: int
    first_team_id: int
    second_team_id: int


class PredictionIn(SQLModel):
    """A whole ballot: both zones arrive together.

    The form is filled zone by zone but sent once at the end, so a visitor who
    abandons it halfway leaves nothing behind.
    """

    model_config = {"extra": "forbid"}

    voter_key: str = Field(min_length=VOTER_KEY_MIN_LENGTH, max_length=VOTER_KEY_MAX_LENGTH)
    zones: list[ZonePick] = Field(min_length=1)


class PollState(SQLModel):
    """Whether the poll is running, and what this device already said."""

    open: bool
    opens_at: datetime.datetime | None = None
    closes_at: datetime.datetime | None = None
    voted: bool = False
    zones: list[ZonePick] = Field(default_factory=list)


class OpenPollIn(SQLModel):
    model_config = {"extra": "forbid"}

    days: int = Field(default=DEFAULT_POLL_DAYS, ge=1, le=90)


class TeamResult(SQLModel):
    team_id: int
    first_votes: int
    second_votes: int
    points: int


class ZoneResult(SQLModel):
    zone_id: int
    teams: list[TeamResult]


class PollResults(SQLModel):
    """Revealed only once the window has closed."""

    closes_at: datetime.datetime
    voters: int
    zones: list[ZoneResult]
