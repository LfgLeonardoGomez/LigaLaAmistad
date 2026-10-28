import datetime

from pydantic import model_validator
from sqlmodel import Field, SQLModel

from app.predictions.models import DEFAULT_POLL_DAYS
from app.votes.models import VOTER_KEY_MAX_LENGTH, VOTER_KEY_MIN_LENGTH


class ZonePick(SQLModel):
    model_config = {"extra": "forbid"}

    zone_id: int = Field(ge=1, le=2_147_483_647)
    first_team_id: int = Field(ge=1, le=2_147_483_647)
    second_team_id: int = Field(ge=1, le=2_147_483_647)


class PredictionIn(SQLModel):
    """A whole ballot: both zones arrive together.

    The form is filled zone by zone but sent once at the end, so a visitor who
    abandons it halfway leaves nothing behind.
    """

    model_config = {"extra": "forbid"}

    voter_key: str = Field(min_length=VOTER_KEY_MIN_LENGTH, max_length=VOTER_KEY_MAX_LENGTH)
    zones: list[ZonePick] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def unique_zones(self):
        zone_ids = [pick.zone_id for pick in self.zones]
        if len(zone_ids) != len(set(zone_ids)):
            raise ValueError("A ballot may contain each zone only once")
        return self


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
