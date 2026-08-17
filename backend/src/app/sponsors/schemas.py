from sqlmodel import Field, SQLModel


class SponsorCreate(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    logo_url: str = Field(min_length=1, max_length=255)
    url: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class SponsorUpdate(SQLModel):
    model_config = {"extra": "forbid"}

    name: str | None = Field(default=None, min_length=1, max_length=100)
    logo_url: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class SponsorRead(SQLModel):
    id: int
    name: str
    logo_url: str
    url: str | None
    is_active: bool
