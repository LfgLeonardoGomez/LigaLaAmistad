from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.core.models import TimestampMixin

# A key the browser makes up and keeps. Long enough to be unguessable, short
# enough to index: it is an opaque identifier, never anything about a person.
VOTER_KEY_MAX_LENGTH = 64
VOTER_KEY_MIN_LENGTH = 8


class MatchVote(TimestampMixin, table=True):
    """One device's pick for who wins a match.

    Anonymous on purpose. The public site has no accounts, so asking people to
    register in order to guess a padel result would cost far more than the
    fraud it prevents. The device key is enough to stop one person voting fifty
    times in a row; someone who clears their storage can vote again, and that
    is accepted.

    The unique constraint is what makes a vote changeable rather than
    duplicable: voting again moves the existing row instead of adding one.
    """

    __tablename__ = "match_votes"
    __table_args__ = (
        UniqueConstraint("match_id", "voter_key", name="uq_match_votes_match_voter"),
    )

    id: int | None = Field(default=None, primary_key=True)
    match_id: int = Field(foreign_key="matches.id", index=True)
    team_id: int = Field(foreign_key="teams.id")
    voter_key: str = Field(max_length=VOTER_KEY_MAX_LENGTH, index=True)
