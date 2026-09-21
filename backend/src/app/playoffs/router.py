from fastapi import APIRouter, Depends, status

from app.auth.deps import get_current_admin
from app.database.session import SessionDep
from app.playoffs import service
from app.playoffs.schemas import BracketRead, GenerateBracketIn

router = APIRouter(
    prefix="/playoffs",
    tags=["admin: playoffs"],
    dependencies=[Depends(get_current_admin)],
)


@router.post("/generate", response_model=BracketRead, status_code=status.HTTP_201_CREATED)
def generate_bracket(session: SessionDep, data: GenerateBracketIn = GenerateBracketIn()):
    """Close the group stage and build the bracket from its standings.

    Refuses (409, with the list of what is still pending) while group-stage
    matches remain unplayed, unless `force` is set — see
    `service.build_bracket`.
    """
    service.build_bracket(session, force=data.force)
    return service.get_bracket(session)


@router.get("/bracket", response_model=BracketRead)
def get_bracket(session: SessionDep):
    """The single source of the bracket: a live projection before generation,
    the official persisted bracket after — see `service.get_bracket`.
    """
    return service.get_bracket(session)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_bracket(session: SessionDep, force: bool = False):
    """Wipe the bracket, its seeds and its generated matches. For re-generating during testing.

    Refuses (409) if any bracket match already has a loaded result, unless
    `force` is set.
    """
    service.wipe_bracket(session, force=force)
