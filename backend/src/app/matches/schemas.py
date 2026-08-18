import datetime

from sqlmodel import Field, SQLModel

from app.matches.models import COMMENT_MAX_LENGTH, MatchStatus


class MatchCreate(SQLModel):
    team_a_id: int
    team_b_id: int
    date: datetime.date


class MatchUpdate(SQLModel):
    """Corrects the date or the teams of a pending match."""

    model_config = {"extra": "forbid"}

    team_a_id: int | None = None
    team_b_id: int | None = None
    date: datetime.date | None = None


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
    status: MatchStatus
    sets: list[SetRead] = Field(default_factory=list)
    winner_team_id: int | None = None
    photo_url: str | None = None
    comment: str | None = None
