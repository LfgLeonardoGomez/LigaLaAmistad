from fastapi import APIRouter, Depends, UploadFile, status

from app.auth.deps import get_current_admin
from app.core.config import settings
from app.core.images import upload_image
from app.database.session import SessionDep
from app.teams import service
from app.teams.schemas import TeamCreate, TeamRead, TeamUpdate

router = APIRouter(
    prefix="/admin/teams",
    tags=["admin: teams"],
    dependencies=[Depends(get_current_admin)],
)


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(data: TeamCreate, session: SessionDep):
    return service.create_team(session, data)


@router.get("", response_model=list[TeamRead])
def list_teams(session: SessionDep, zone_id: int | None = None):
    return service.list_teams(session, zone_id)


@router.get("/{team_id}", response_model=TeamRead)
def get_team(team_id: int, session: SessionDep):
    return service.get_team(session, team_id)


@router.patch("/{team_id}", response_model=TeamRead)
def update_team(team_id: int, data: TeamUpdate, session: SessionDep):
    return service.update_team(session, team_id, data)


@router.post("/{team_id}/photo", response_model=TeamRead)
def upload_team_photo(team_id: int, file: UploadFile, session: SessionDep):
    """Upload the pair's photo. Not `async`: the Cloudinary call blocks."""
    service.get_team(session, team_id)  # 404 before spending an upload
    url = upload_image(file, folder=settings.cloudinary_teams_folder)
    return service.set_photo_url(session, team_id, url)
