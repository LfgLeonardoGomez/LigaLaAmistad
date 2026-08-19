from fastapi import APIRouter, Depends

from app.auth.deps import get_current_admin
from app.database.session import SessionDep
from app.predictions import service
from app.predictions.schemas import OpenPollIn, PollState

router = APIRouter(
    prefix="/admin/predictions",
    tags=["admin: predictions"],
    dependencies=[Depends(get_current_admin)],
)


@router.post("/open", response_model=PollState)
def open_poll(data: OpenPollIn, session: SessionDep):
    """Start a new poll. Any earlier one stops mattering from here."""
    service.open_poll(session, data.days)
    return service.state(session)


@router.post("/close", response_model=PollState)
def close_poll(session: SessionDep):
    """End the poll now, which is what publishes the results."""
    service.close_poll(session)
    return service.state(session)
