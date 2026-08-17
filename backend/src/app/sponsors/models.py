from sqlmodel import Field

from app.core.models import TimestampMixin


class Sponsor(TimestampMixin, table=True):
    """A tournament sponsor.

    Here `is_active` is a visibility flag for the public site only. It has no
    domain consequence, unlike `Team.status`.
    """

    __tablename__ = "sponsors"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    logo_url: str = Field(max_length=255)
    url: str | None = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
