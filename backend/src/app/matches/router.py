from fastapi import APIRouter, Depends, status

from app.auth.deps import get_current_admin
from app.database.session import SessionDep
from app.matches import service
from app.matches.models import MatchStatus
from app.matches.schemas import MatchCreate, MatchRead, MatchResultIn, MatchUpdate

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


@router.delete("/{match_id}/result", response_model=MatchRead)
def delete_result(match_id: int, session: SessionDep):
    return service.to_read(session, service.delete_result(session, match_id))
