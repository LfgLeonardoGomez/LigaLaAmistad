import datetime

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field

from app.core.models import TimestampMixin

# What a first place is worth against a second, when the picks are added up.
POINTS_FIRST = 2
POINTS_SECOND = 1

# How long a poll runs when the admin opens one without saying.
DEFAULT_POLL_DAYS = 7


class PredictionWindow(TimestampMixin, table=True):
    """The period during which the season prediction accepts votes.

    A row per poll rather than a flag on a settings table: the closing date is
    the whole point of the feature. A prediction that can be cast at any time
    is not a prediction, and the results cannot be revealed while it is still
    possible to vote on them.

    Only the newest row matters. The older ones are kept because they are the
    record of what was asked and when.
    """

    __tablename__ = "prediction_windows"

    id: int | None = Field(default=None, primary_key=True)
    opens_at: datetime.datetime = Field(sa_type=DateTime(timezone=True), nullable=False)
    closes_at: datetime.datetime = Field(sa_type=DateTime(timezone=True), nullable=False)


class Prediction(TimestampMixin, table=True):
    """One device's pick of first and second place in one zone.

    Same anonymity as the match votes: a key the browser made up, no account.
    One row per (window, zone, device), so changing your mind moves the pick
    instead of stuffing the count.
    """

    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint(
            "window_id", "zone_id", "voter_key", name="uq_predictions_window_zone_voter"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    window_id: int = Field(foreign_key="prediction_windows.id", index=True)
    zone_id: int = Field(foreign_key="zones.id", index=True)
    voter_key: str = Field(max_length=64, index=True)
    first_team_id: int = Field(foreign_key="teams.id")
    second_team_id: int = Field(foreign_key="teams.id")
