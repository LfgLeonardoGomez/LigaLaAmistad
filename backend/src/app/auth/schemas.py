from pydantic import EmailStr, field_validator
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

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value


class AdminUpdate(SQLModel):
    """An admin can be deactivated, or have their password reset."""

    model_config = {"extra": "forbid"}

    password: str | None = Field(
        default=None, min_length=MIN_PASSWORD_LENGTH, max_length=128
    )
    is_active: bool | None = None

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str | None) -> str | None:
        if value is not None and len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value
