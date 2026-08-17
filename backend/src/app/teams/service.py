from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.teams.models import Team
from app.teams.schemas import TeamCreate, TeamUpdate
from app.zones.models import Zone


def create_team(session: Session, data: TeamCreate) -> Team:
    if session.get(Zone, data.zone_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {data.zone_id} not found",
        )

    team = Team(**data.model_dump())
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


def list_teams(session: Session, zone_id: int | None = None) -> list[Team]:
    statement = select(Team).order_by(Team.id)
    if zone_id is not None:
        statement = statement.where(Team.zone_id == zone_id)
    return list(session.exec(statement).all())


def get_team(session: Session, team_id: int) -> Team:
    team = session.get(Team, team_id)
    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )
    return team


def set_photo_url(session: Session, team_id: int, photo_url: str) -> Team:
    team = get_team(session, team_id)
    team.photo_url = photo_url
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


def update_team(session: Session, team_id: int, data: TeamUpdate) -> Team:
    changes = data.model_dump(exclude_unset=True)

    if "zone_id" in changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="zone_id is immutable and cannot be changed",
        )

    team = get_team(session, team_id)
    for field, value in changes.items():
        setattr(team, field, value)

    session.add(team)
    session.commit()
    session.refresh(team)
    return team
