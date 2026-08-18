from fastapi import APIRouter, Depends, UploadFile, status

from app.auth.deps import get_current_admin
from app.core.config import settings
from app.core.images import upload_image
from app.database.session import SessionDep
from app.matches import service
from app.matches.models import MatchStatus
from app.matches.schemas import (
    MatchCommentIn,
    MatchCreate,
    MatchRead,
    MatchResultIn,
    MatchUpdate,
)

router = APIRouter(
    prefix="/admin/matches",
    tags=["admin: matches"],
    dependencies=[Depends(get_current_admin)],
)


@router.post("", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
def create_match(data: MatchCreate, session: SessionDep):
    match = service.create_match(session, data)
    return service.to_read(session, match)


@router.get("", response_model=list[MatchRead])
def list_matches(
    session: SessionDep,
    status: MatchStatus | None = None,
    zone_id: int | None = None,
):
    matches = service.list_matches(session, status, zone_id)
    return [service.to_read(session, match) for match in matches]


@router.get("/{match_id}", response_model=MatchRead)
def get_match(match_id: int, session: SessionDep):
    return service.to_read(session, service.get_match(session, match_id))


@router.patch("/{match_id}", response_model=MatchRead)
def update_match(match_id: int, data: MatchUpdate, session: SessionDep):
    match = service.update_match(session, match_id, data)
    return service.to_read(session, match)


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match(match_id: int, session: SessionDep):
    service.delete_match(session, match_id)


@router.post("/{match_id}/result", response_model=MatchRead)
def set_result(match_id: int, data: MatchResultIn, session: SessionDep):
    return service.to_read(session, service.set_result(session, match_id, data))


@router.put("/{match_id}/result", response_model=MatchRead)
def replace_result(match_id: int, data: MatchResultIn, session: SessionDep):
    return service.to_read(session, service.replace_result(session, match_id, data))


@router.patch("/{match_id}/result", response_model=MatchRead)
def set_result_comment(match_id: int, data: MatchCommentIn, session: SessionDep):
    """Edit the comment without re-sending the sets."""
    return service.to_read(session, service.set_comment(session, match_id, data.comment))


@router.post("/{match_id}/result/photo", response_model=MatchRead)
def upload_match_photo(match_id: int, file: UploadFile, session: SessionDep):
    """Upload the match photo. Not `async`: the Cloudinary call blocks."""
    service.require_played(session, match_id, "adding a photo")  # before the upload
    url = upload_image(file, folder=settings.cloudinary_matches_folder)
    return service.to_read(session, service.set_photo_url(session, match_id, url))


@router.delete("/{match_id}/result", response_model=MatchRead)
def delete_result(match_id: int, session: SessionDep):
    return service.to_read(session, service.delete_result(session, match_id))
