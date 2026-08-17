import datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def utc_now() -> datetime.datetime:
    """Current instant as a timezone-aware UTC datetime."""
    return datetime.datetime.now(datetime.UTC)


class TimestampMixin(SQLModel):
    """Creation and last-update timestamps, always stored in UTC.

    Not a table itself. Table models inherit from it to get both columns.

    `sa_type` rather than `sa_column`: a Column instance cannot be shared by
    several mapped classes, and this mixin is inherited by four of them. A type
    instance can.
    """

    created_at: datetime.datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
    updated_at: datetime.datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"onupdate": utc_now},
    )
