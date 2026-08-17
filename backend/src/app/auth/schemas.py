from pydantic import EmailStr
from sqlmodel import Field, SQLModel

MIN_PASSWORD_LENGTH = 8


class LoginIn(SQLModel):
    email: str
    password: str


class AdminRead(SQLModel):
    """Never carries `password_hash`. That is the whole point of a read schema."""

    id: int
    email: str
    is_active: bool


class AdminCreate(SQLModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)


class AdminUpdate(SQLModel):
    """An admin can be deactivated, or have their password reset."""

    model_config = {"extra": "forbid"}

    password: str | None = Field(
        default=None, min_length=MIN_PASSWORD_LENGTH, max_length=128
    )
    is_active: bool | None = None
