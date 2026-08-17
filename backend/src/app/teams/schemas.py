from sqlmodel import Field, SQLModel

from app.teams.models import TeamStatus


class TeamCreate(SQLModel):
    zone_id: int
    player_one_name: str = Field(min_length=1, max_length=50)
    player_two_name: str = Field(min_length=1, max_length=50)
    photo_url: str | None = Field(default=None, max_length=255)


class TeamUpdate(SQLModel):
    """Fields an admin may change after creation.

    `zone_id` is declared only so the API can reject it with a clear 400: a team
    never changes zone. Any other unknown field is rejected by `extra="forbid"`.
    """

    model_config = {"extra": "forbid"}

    player_one_name: str | None = Field(default=None, min_length=1, max_length=50)
    player_two_name: str | None = Field(default=None, min_length=1, max_length=50)
    photo_url: str | None = Field(default=None, max_length=255)
    status: TeamStatus | None = None
    zone_id: int | None = None


class TeamRead(SQLModel):
    id: int
    zone_id: int
    player_one_name: str
    player_two_name: str
    photo_url: str | None
    status: TeamStatus
