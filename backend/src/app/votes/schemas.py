from sqlmodel import Field, SQLModel

from app.votes.models import VOTER_KEY_MAX_LENGTH, VOTER_KEY_MIN_LENGTH


class VoteIn(SQLModel):
    model_config = {"extra": "forbid"}

    team_id: int
    voter_key: str = Field(min_length=VOTER_KEY_MIN_LENGTH, max_length=VOTER_KEY_MAX_LENGTH)


class VoteTally(SQLModel):
    """How a match is being voted, from the point of view of one device.

    Both counts travel even when they are zero: the front end draws the bar
    from the first vote, so it always needs the pair of numbers rather than a
    percentage it would have to guess at.
    """

    match_id: int
    team_a_votes: int
    team_b_votes: int
    total: int
    # What the asking device picked, or null if it did not vote or did not say
    # who it is. This is what lets the card come back highlighted after a
    # reload instead of offering the vote again.
    voted_team_id: int | None = None
    open: bool
