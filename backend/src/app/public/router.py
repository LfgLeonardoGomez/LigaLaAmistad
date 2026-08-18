"""Read-only endpoints for the public site. No authentication.

Zones have no module of their own here (they are seed data, not a managed
entity), so their single public endpoint lives with the rest of the public API.
"""

from fastapi import APIRouter
from sqlmodel import select

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
from app.zones.models import Zone
from app.zones.schemas import ZoneRead

router = APIRouter(prefix="/public", tags=["public"])


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


@router.get("/standings", response_model=list[StandingRead])
def list_standings(session: SessionDep, zone_id: int):
    return standings_service.get_standings(session, zone_id)


@router.get("/sponsors", response_model=list[SponsorRead])
def list_sponsors(session: SessionDep):
    return sponsor_service.list_sponsors(session, only_active=True)
