import datetime

from sqlmodel import Field, SQLModel

from app.matches.models import COMMENT_MAX_LENGTH, MatchStatus, MatchVenue


class MatchCreate(SQLModel):
    team_a_id: int
    team_b_id: int
    date: datetime.date
    time: datetime.time | None = None
    venue: MatchVenue | None = None


class MatchUpdate(SQLModel):
    """Corrects the date, the time, the venue or the teams of a pending match.

    An absent field is left alone (the service applies only what was sent), so
    an explicit `null` is how the time or the venue goes back to undecided.
    """

    model_config = {"extra": "forbid"}

    team_a_id: int | None = None
    team_b_id: int | None = None
    date: datetime.date | None = None
    time: datetime.time | None = None
    venue: MatchVenue | None = None


class SetIn(SQLModel):
    set_number: int = Field(ge=1)
    team_a_games: int = Field(ge=0)
    team_b_games: int = Field(ge=0)


class MatchResultIn(SQLModel):
    """Sets, plus an optional comment.

    On a correction (`PUT`) an absent `comment` leaves the stored one alone,
    which is why the service reads `model_fields_set` and not just the value.
    """

    sets: list[SetIn]
    comment: str | None = Field(default=None, max_length=COMMENT_MAX_LENGTH)


class MatchCommentIn(SQLModel):
    """Edits the comment on its own, without touching the sets."""

    model_config = {"extra": "forbid"}

    comment: str | None = Field(default=None, max_length=COMMENT_MAX_LENGTH)


class SetRead(SQLModel):
    set_number: int
    team_a_games: int
    team_b_games: int


class MatchRead(SQLModel):
    id: int
    team_a_id: int
    team_b_id: int
    date: datetime.date
    time: datetime.time | None = None
    venue: MatchVenue | None = None
    status: MatchStatus
    sets: list[SetRead] = Field(default_factory=list)
    winner_team_id: int | None = None
    photo_url: str | None = None
    comment: str | None = None
