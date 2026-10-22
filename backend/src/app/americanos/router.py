"""Private event operations. Validation errors are local to this router."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BeforeValidator

from app.americanos import schemas as dto
from app.americanos import service
from app.auth.deps import get_current_admin
from app.database.session import SessionDep


def _integer_text(value: str) -> int:
    # Path/query values are strings on the wire; never coerce "2.0" to integer 2.
    if not value.isascii() or not value.isdecimal():
        raise ValueError("Debe ser un entero positivo.")
    return int(value)


RevisionQuery = Annotated[int, Query(ge=1), BeforeValidator(_integer_text)]
PathId = Annotated[dto.AmericanoId, Path(), BeforeValidator(_integer_text)]


class AmericanoRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request: Request) -> Response:
            try:
                return await original(request)
            except service.AmericanoError as exc:
                return JSONResponse(status_code=exc.status, content=exc.body.model_dump())
            except RequestValidationError as exc:
                fields = [dto.AmericanoFieldError(
                    path=list(error["loc"][1:]), code=error["type"], message=error["msg"],
                ) for error in exc.errors()]
                error = dto.AmericanoErrorBody(
                    code="validation_error", message="Solicitud inválida.",
                    detail="Solicitud inválida.", fields=fields,
                )
                return JSONResponse(status_code=422, content=error.model_dump())

        return handle


router = APIRouter(
    prefix="/admin/americanos", tags=["americanos"], route_class=AmericanoRoute,
    dependencies=[Depends(get_current_admin)],
)


@router.get("")
def list_events(session: SessionDep) -> dto.ListEventsResponse:
    return service.list_events(session)


@router.post("", status_code=201)
def create_event(data: dto.CreateEventRequest, session: SessionDep) -> dto.EventDetail:
    return service.create_event(session, data)


@router.get("/{event_id}")
def load_event(event_id: PathId, session: SessionDep) -> dto.EventDetail:
    return service.load_event(session, event_id)


@router.patch("/{event_id}")
def update_event(event_id: PathId, data: dto.UpdateEventRequest, session: SessionDep) -> dto.EventDetail:
    return service.update_event(session, event_id, data)


@router.post("/{event_id}/registrations", status_code=201)
def add_registration(event_id: PathId, data: dto.RegistrationRequest, session: SessionDep) -> dto.EventDetail:
    return service.add_registration(session, event_id, data)


@router.patch("/{event_id}/registrations/{registration_id}")
def update_registration(
    event_id: PathId, registration_id: PathId, data: dto.UpdateRegistrationRequest, session: SessionDep,
) -> dto.EventDetail:
    return service.update_registration(session, event_id, registration_id, data)


@router.delete("/{event_id}/registrations/{registration_id}")
def delete_registration(
    event_id: PathId, registration_id: PathId, expected_revision: RevisionQuery, session: SessionDep,
) -> dto.EventDetail:
    return service.delete_registration(session, event_id, registration_id, expected_revision)


@router.put("/{event_id}/zones")
def set_zones(event_id: PathId, data: dto.SetZonesRequest, session: SessionDep) -> dto.EventDetail:
    return service.set_zones(session, event_id, data)


@router.post("/{event_id}/zones/randomize")
def randomize_zones(event_id: PathId, data: dto.RevisionRequest, session: SessionDep) -> dto.EventDetail:
    return service.randomize_zones(session, event_id, data)


@router.post("/{event_id}/fixture")
def generate_fixture(
    event_id: PathId, data: dto.RevisionRequest, session: SessionDep,
) -> dto.GenerateFixtureResponse:
    return service.generate_fixture(session, event_id, data)


@router.get("/{event_id}/rounds/{number}")
def load_round(event_id: PathId, number: PathId, session: SessionDep) -> dto.RoundResponse:
    return service.load_round(session, event_id, number)


@router.get("/{event_id}/standings")
def load_standings(event_id: PathId, session: SessionDep) -> dto.StandingsResponse:
    return service.load_standings(session, event_id)


@router.put("/{event_id}/rounds/{number}/results")
def save_round(
    event_id: PathId, number: PathId, data: dto.SaveRoundRequest, session: SessionDep,
) -> dto.SaveRoundResponse:
    return service.save_round(session, event_id, number, data)
