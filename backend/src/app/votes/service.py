"""Counting public votes on who wins a match."""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.matches.models import Match, MatchStatus
from app.votes.models import MatchVote
from app.votes.schemas import VoteIn, VoteTally


def voting_is_open(match: Match) -> bool:
    """Whether a match still accepts votes.

    Deliberately the only place this is decided. Today it closes when the
    result is loaded, which leaves a window between a match being played and
    someone getting round to loading it, where a voter who already knows the
    outcome can vote on a certainty. Closing at the scheduled kick-off instead
    would shut that window, and it is a change to this one function.
    """
    return match.status == MatchStatus.PENDING


def _get_match(session: Session, match_id: int) -> Match:
    match = session.get(Match, match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Match not found"
        )
    return match


def _counts(session: Session, match_ids: list[int]) -> dict[int, dict[int, int]]:
    """Votes per team per match, in one query rather than one per match."""
    if not match_ids:
        return {}

    rows = session.exec(
        select(MatchVote.match_id, MatchVote.team_id, func.count())
        .where(MatchVote.match_id.in_(match_ids))
        .group_by(MatchVote.match_id, MatchVote.team_id)
    ).all()

    counts: dict[int, dict[int, int]] = {}
    for match_id, team_id, total in rows:
        counts.setdefault(match_id, {})[team_id] = total
    return counts


def _own_votes(session: Session, match_ids: list[int], voter_key: str | None) -> dict[int, int]:
    if not voter_key or not match_ids:
        return {}

    rows = session.exec(
        select(MatchVote.match_id, MatchVote.team_id).where(
            MatchVote.match_id.in_(match_ids), MatchVote.voter_key == voter_key
        )
    ).all()
    return {match_id: team_id for match_id, team_id in rows}


def _to_tally(match: Match, counts: dict[int, int], voted_team_id: int | None) -> VoteTally:
    team_a_votes = counts.get(match.team_a_id, 0)
    team_b_votes = counts.get(match.team_b_id, 0)
    return VoteTally(
        match_id=match.id,
        team_a_votes=team_a_votes,
        team_b_votes=team_b_votes,
        total=team_a_votes + team_b_votes,
        voted_team_id=voted_team_id,
        open=voting_is_open(match),
    )


def tally(session: Session, match_ids: list[int], voter_key: str | None = None) -> list[VoteTally]:
    """Vote counts for the given matches. Unknown ids are simply left out."""
    matches = list(session.exec(select(Match).where(Match.id.in_(match_ids))).all()) if match_ids else []
    counts = _counts(session, match_ids)
    own = _own_votes(session, match_ids, voter_key)

    order = {match_id: index for index, match_id in enumerate(match_ids)}
    matches.sort(key=lambda match: order.get(match.id, 0))

    return [_to_tally(match, counts.get(match.id, {}), own.get(match.id)) for match in matches]


def cast_vote(session: Session, match_id: int, data: VoteIn) -> VoteTally:
    """Record or move one device's pick, then return the new counts."""
    match = _get_match(session, match_id)

    if not voting_is_open(match):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Voting is closed for this match",
        )

    if data.team_id not in (match.team_a_id, match.team_b_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That team does not play this match",
        )

    existing = session.exec(
        select(MatchVote).where(
            MatchVote.match_id == match_id, MatchVote.voter_key == data.voter_key
        )
    ).first()

    if existing is None:
        session.add(MatchVote(match_id=match_id, team_id=data.team_id, voter_key=data.voter_key))
    else:
        # Changing your mind moves the vote. The unique constraint guarantees
        # there is at most one row to move, so nobody accumulates votes.
        existing.team_id = data.team_id
        session.add(existing)

    session.commit()

    return tally(session, [match_id], data.voter_key)[0]
