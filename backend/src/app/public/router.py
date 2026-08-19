"""Endpoints for the public site. No authentication.

Read-only except for one thing: a visitor may vote on who wins a pending
match. That is the only write the public can make, it creates nothing that
identifies a person, and it is rate limited.

Zones have no module of their own here (they are seed data, not a managed
entity), so their single public endpoint lives with the rest of the public API.
"""

from fastapi import APIRouter, Request
from sqlmodel import select

from app.core.ratelimit import check_rate_limit, client_key
from app.database.session import SessionDep
from app.matches import service as match_service
from app.matches.models import MatchStatus
from app.matches.schemas import MatchRead
from app.sponsors import service as sponsor_service
from app.sponsors.schemas import SponsorRead
from app.standings import service as standings_service
from app.standings.schemas import StandingRead
from app.teams import service as team_service
from app.teams.schemas import TeamRead
from app.votes import service as vote_service
from app.votes.schemas import VoteIn, VoteTally
from app.zones.models import Zone
from app.zones.schemas import ZoneRead

router = APIRouter(prefix="/public", tags=["public"])

# Generous enough that nobody voting by hand on a page of matches ever sees it,
# tight enough that a script cannot stuff a poll from one address.
VOTES_PER_WINDOW = 30
VOTE_WINDOW_SECONDS = 60

# A page asks for the matches it is showing, which is six on the home and
# twenty in the results list. The cap is what stops a caller asking for the
# whole table in one request.
MAX_TALLIED_MATCHES = 50


@router.get("/zones", response_model=list[ZoneRead])
def list_zones(session: SessionDep):
    return list(session.exec(select(Zone).order_by(Zone.id)).all())


@router.get("/teams", response_model=list[TeamRead])
def list_teams(session: SessionDep, zone_id: int | None = None):
    return team_service.list_teams(session, zone_id)


@router.get("/matches", response_model=list[MatchRead])
def list_matches(
    session: SessionDep,
    zone_id: int | None = None,
    status: MatchStatus = MatchStatus.PLAYED,
):
    """Played matches by default, pending ones on request.

    The default is `played` because that is what "the results" means to a
    visitor, and it keeps every existing caller working. Asking for `pending`
    is how the home lists what is still to be played: knowing who plays next
    is as much public information as knowing who won.
    """
    matches = match_service.list_matches(session, status, zone_id)
    return [match_service.to_read(session, match) for match in matches]


def _parse_ids(ids: str) -> list[int]:
    """`"3,1,9"` as `[3, 1, 9]`, ignoring anything that is not a number.

    A bad id is dropped rather than rejected: the tally is decoration on a page
    that must render anyway, so it never fails the whole request over one.
    """
    parsed = [chunk.strip() for chunk in ids.split(",")]
    return [int(chunk) for chunk in parsed if chunk.isdigit()][:MAX_TALLIED_MATCHES]


@router.get("/matches/votes", response_model=list[VoteTally])
def tally_match_votes(session: SessionDep, ids: str = "", voter_key: str | None = None):
    """Vote counts for the given matches, in one call instead of one each.

    `voter_key` is optional and only decides whether the answer says what this
    device already picked.
    """
    return vote_service.tally(session, _parse_ids(ids), voter_key)


@router.post("/matches/{match_id}/votes", response_model=VoteTally)
def cast_match_vote(match_id: int, data: VoteIn, request: Request, session: SessionDep):
    check_rate_limit(
        f"vote:{client_key(request)}",
        VOTES_PER_WINDOW,
        VOTE_WINDOW_SECONDS,
        detail="Too many votes. Try again later",
    )
    return vote_service.cast_vote(session, match_id, data)


@router.get("/standings", response_model=list[StandingRead])
def list_standings(session: SessionDep, zone_id: int):
    return standings_service.get_standings(session, zone_id)


@router.get("/sponsors", response_model=list[SponsorRead])
def list_sponsors(session: SessionDep):
    return sponsor_service.list_sponsors(session, only_active=True)
