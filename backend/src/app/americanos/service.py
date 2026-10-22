"""Private Americano operations; one event lock and one transaction per request."""

from contextlib import contextmanager
from datetime import UTC
from random import shuffle

from sqlmodel import Session, select

from app.americanos import schemas as dto
from app.americanos.models import (
    AmericanoEvent, AmericanoEventState, AmericanoRegistration, AmericanoRound,
    AmericanoStage, AmericanoZone, AmericanoZoneLabel,
)
from app.americanos.qualification import qualification_quotas


class AmericanoError(Exception):
    def __init__(self, status: int, code: str, message: str, **metadata):
        super().__init__(message)
        self.status = status
        self.body = dto.AmericanoErrorBody(
            code=code, message=message, detail=message, **metadata,
        )


@contextmanager
def _transaction(session: Session, *, write: bool = False):
    # Auth has already used this Session: reuse its autobegun transaction.
    try:
        yield
        if write:
            session.commit()
        else:
            session.rollback()  # release read locks without any writes
    except Exception:
        session.rollback()
        raise


def _event(session: Session, event_id: int, *, write: bool = False) -> AmericanoEvent:
    event = session.exec(
        select(AmericanoEvent).where(AmericanoEvent.id == event_id)
        .with_for_update(read=not write).execution_options(populate_existing=True)
    ).first()
    if event is None:
        raise AmericanoError(404, "not_found", "Evento o recurso no encontrado.")
    return event


def _registrations(session: Session, event_id: int) -> list[AmericanoRegistration]:
    return list(session.exec(
        select(AmericanoRegistration).where(AmericanoRegistration.event_id == event_id)
        .order_by(AmericanoRegistration.registration_order)
    ).all())


def _zones(session: Session, event_id: int) -> list[AmericanoZone]:
    return list(session.exec(
        select(AmericanoZone).where(AmericanoZone.event_id == event_id)
        .order_by(AmericanoZone.label)
    ).all())


def _summary(session: Session, event: AmericanoEvent, registration_count: int) -> dto.EventSummary:
    rounds = session.exec(
        select(AmericanoRound).where(AmericanoRound.event_id == event.id)
        .order_by(AmericanoRound.number)
    ).all()
    prefix = 0
    for round_ in rounds:
        if round_.saved_at is None:
            break
        prefix += 1
    unlocked = min(prefix + 1, len(rounds))
    if event.state == AmericanoEventState.DRAFT:
        continuation = dto.SetupContinuation(kind="setup")
    elif event.state == AmericanoEventState.GROUPS:
        continuation = dto.RoundContinuation(kind="round", round_number=unlocked)
    elif event.state == AmericanoEventState.REVIEW:
        continuation = dto.QualificationContinuation(kind="qualification")
    else:
        continuation = dto.PlayoffsContinuation(kind="playoffs")
    return dto.EventSummary(
        id=event.id, name=event.name, state=event.state.value,
        zone_count=event.zone_count, start_stage=event.start_stage.value,
        revision=event.revision, groups_revision=event.groups_revision,
        registration_count=registration_count, total_rounds=len(rounds),
        saved_rounds=sum(round_.saved_at is not None for round_ in rounds),
        max_unlocked_round=unlocked, continuation=continuation,
    )


def _detail(session: Session, event: AmericanoEvent) -> dto.EventDetail:
    zones = _zones(session, event.id)
    registrations = _registrations(session, event.id)
    required = qualification_quotas(event.start_stage.value, [zone.id for zone in zones])
    quotas = []
    issues = []
    for zone in zones:
        count = sum(registration.zone_id == zone.id for registration in registrations)
        sufficient = count >= required[zone.id]
        quotas.append(dto.ZoneQuota(
            zone_id=zone.id, required=required[zone.id], registered=count, sufficient=sufficient,
        ))
        if not sufficient:
            issues.append(dto.ConfigurationIssue(
                code="insufficient_registrations", zone_id=zone.id, registration_ids=[],
                message=f"La zona {zone.label.value} requiere {required[zone.id]} parejas.",
            ))
    unassigned = [registration.id for registration in registrations if registration.zone_id is None]
    if unassigned:
        issues.append(dto.ConfigurationIssue(
            code="unassigned_registrations", zone_id=None, registration_ids=unassigned,
            message="Hay parejas sin zona asignada.",
        ))
    confirmed_at = event.confirmed_at
    if confirmed_at is not None:
        # SQLite loses the tzinfo of UTC timestamps; PostgreSQL retains it.
        confirmed_at = confirmed_at.replace(tzinfo=UTC) if confirmed_at.tzinfo is None else confirmed_at
    return dto.EventDetail(
        **_summary(session, event, len(registrations)).model_dump(),
        zones=[dto.Zone(id=zone.id, label=zone.label.value) for zone in zones],
        registrations=[dto.Registration(
            id=registration.id, zone_id=registration.zone_id,
            player1_name=registration.player1_name, player2_name=registration.player2_name,
            registration_order=registration.registration_order,
        ) for registration in registrations],
        quotas=quotas, configuration_issues=issues,
        can_generate=event.state == AmericanoEventState.DRAFT and not issues,
        confirmed_at=confirmed_at.astimezone(UTC).isoformat() if confirmed_at else None,
        champion_registration_id=event.champion_registration_id,
    )


def list_events(session: Session) -> dto.ListEventsResponse:
    with _transaction(session):
        events = session.exec(
            select(AmericanoEvent).order_by(AmericanoEvent.id.desc())
            .with_for_update(read=True).execution_options(populate_existing=True)
        ).all()
        return [_summary(session, event, len(_registrations(session, event.id))) for event in events]


def create_event(session: Session, data: dto.CreateEventRequest) -> dto.EventDetail:
    with _transaction(session, write=True):
        event = AmericanoEvent(
            name=data.name, zone_count=data.zone_count, start_stage=AmericanoStage(data.start_stage),
        )
        session.add(event)
        session.flush()
        for label in list(AmericanoZoneLabel)[:data.zone_count]:
            session.add(AmericanoZone(event_id=event.id, label=label))
        session.flush()
        return _detail(session, event)


def load_event(session: Session, event_id: int) -> dto.EventDetail:
    with _transaction(session):
        return _detail(session, _event(session, event_id))


def _validate_draft(event: AmericanoEvent, expected_revision: int) -> None:
    if event.revision != expected_revision:
        raise AmericanoError(
            409, "revision_conflict", "El evento cambió; recargá antes de guardar.",
            current_revision=event.revision,
            fields=[dto.AmericanoFieldError(
                path=["expected_revision"], code="stale", message="Revisión obsoleta.",
            )],
        )
    if event.state != AmericanoEventState.DRAFT:
        raise AmericanoError(
            409, "state_conflict", "La configuración solo puede editarse en borrador.",
            current_revision=event.revision,
        )


def _change_zone_count(session: Session, event: AmericanoEvent, count: int) -> None:
    zones = _zones(session, event.id)
    if count == 1:
        for registration in _registrations(session, event.id):
            registration.zone_id = zones[0].id
            session.add(registration)
        # Remove all references before deleting B: composite FKs are immediate.
        session.flush()
        if len(zones) == 2:
            session.delete(zones[1])
    elif len(zones) == 1:
        session.add(AmericanoZone(event_id=event.id, label=AmericanoZoneLabel.B))
    event.zone_count = count


def _changed_detail(session: Session, event: AmericanoEvent) -> dto.EventDetail:
    """Flush one revision advance and materialize the response before committing."""
    event.revision += 1
    session.add(event)
    session.flush()
    return _detail(session, event)


def update_event(session: Session, event_id: int, data: dto.UpdateEventRequest) -> dto.EventDetail:
    with _transaction(session, write=True):
        event = _event(session, event_id, write=True)
        _validate_draft(event, data.expected_revision)
        changes = data.model_dump(exclude_unset=True, exclude={"expected_revision"})
        if "zone_count" in changes:
            _change_zone_count(session, event, changes.pop("zone_count"))
        if "start_stage" in changes:
            event.start_stage = AmericanoStage(changes.pop("start_stage"))
        if "name" in changes:
            event.name = changes["name"]
        return _changed_detail(session, event)


def add_registration(session: Session, event_id: int, data: dto.RegistrationRequest) -> dto.EventDetail:
    with _transaction(session, write=True):
        event = _event(session, event_id, write=True)
        _validate_draft(event, data.expected_revision)
        registrations = _registrations(session, event.id)
        zone_id = _zones(session, event.id)[0].id if event.zone_count == 1 else None
        session.add(AmericanoRegistration(
            event_id=event.id, zone_id=zone_id,
            player1_name=data.player1_name, player2_name=data.player2_name,
            registration_order=max((r.registration_order for r in registrations), default=0) + 1,
        ))
        return _changed_detail(session, event)


def _draft_registration(
    session: Session, event_id: int, registration_id: int, expected_revision: int,
) -> tuple[AmericanoEvent, AmericanoRegistration]:
    event = _event(session, event_id, write=True)
    registration = session.exec(select(AmericanoRegistration).where(
        AmericanoRegistration.event_id == event.id, AmericanoRegistration.id == registration_id,
    )).first()
    # Do not disclose the event's revision/phase for a foreign nested identity.
    if registration is None:
        raise AmericanoError(404, "not_found", "Evento o recurso no encontrado.")
    _validate_draft(event, expected_revision)
    return event, registration


def update_registration(
    session: Session, event_id: int, registration_id: int, data: dto.UpdateRegistrationRequest,
) -> dto.EventDetail:
    with _transaction(session, write=True):
        event, registration = _draft_registration(
            session, event_id, registration_id, data.expected_revision,
        )
        for field, value in data.model_dump(exclude_unset=True, exclude={"expected_revision"}).items():
            setattr(registration, field, value)
        session.add(registration)
        return _changed_detail(session, event)


def delete_registration(
    session: Session, event_id: int, registration_id: int, expected_revision: int,
) -> dto.EventDetail:
    with _transaction(session, write=True):
        event, registration = _draft_registration(session, event_id, registration_id, expected_revision)
        session.delete(registration)
        return _changed_detail(session, event)


def set_zones(session: Session, event_id: int, data: dto.SetZonesRequest) -> dto.EventDetail:
    with _transaction(session, write=True):
        event = _event(session, event_id, write=True)
        _validate_draft(event, data.expected_revision)
        registrations = _registrations(session, event.id)
        selected = set(data.zone_a_registration_ids)
        registration_ids = {registration.id for registration in registrations}
        if not selected <= registration_ids:
            raise AmericanoError(
                422, "invalid_reference", "La selección contiene parejas que no pertenecen al evento.",
            )
        if data.zone_count == 1 and selected != registration_ids:
            raise AmericanoError(
                422, "invalid_configuration", "Una zona debe incluir todas las parejas del evento.",
            )
        _change_zone_count(session, event, data.zone_count)
        session.flush()
        zones = _zones(session, event.id)
        for registration in registrations:
            registration.zone_id = zones[0].id if registration.id in selected else zones[-1].id
            session.add(registration)
        return _changed_detail(session, event)


def randomize_zones(session: Session, event_id: int, data: dto.RevisionRequest) -> dto.EventDetail:
    with _transaction(session, write=True):
        event = _event(session, event_id, write=True)
        _validate_draft(event, data.expected_revision)
        if event.zone_count != 2:
            raise AmericanoError(
                422, "invalid_configuration", "El reparto aleatorio requiere dos zonas.",
            )
        zones = _zones(session, event.id)
        registrations = _registrations(session, event.id)
        shuffle(registrations)
        split = (len(registrations) + 1) // 2
        for index, registration in enumerate(registrations):
            registration.zone_id = zones[0].id if index < split else zones[1].id
            session.add(registration)
        return _changed_detail(session, event)
