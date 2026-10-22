"""Private Americano operations; one event lock and one transaction per request."""

from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from random import shuffle

from sqlmodel import Session, select

from app.americanos import schemas as dto
from app.americanos.fixture import FixtureRound, ZoneInput, build_fixture
from app.americanos.models import (
    AmericanoEvent, AmericanoEventState, AmericanoGroupMatch, AmericanoRegistration, AmericanoRound,
    AmericanoStage, AmericanoTieResolution, AmericanoZone, AmericanoZoneLabel,
)
from app.americanos.qualification import qualification_quotas
from app.americanos.standings import SavedScore, StandingRegistration, calculate_standings


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


def _validate_lookup_integer(value: int) -> None:
    # Transport accepts JSON-safe integers; these lookups use PostgreSQL INTEGER.
    # An unrepresentable identity is missing, not an invalid transport value.
    if not 1 <= value <= 2_147_483_647:
        raise AmericanoError(404, "not_found", "Evento o recurso no encontrado.")


def _event(session: Session, event_id: int, *, write: bool = False) -> AmericanoEvent:
    _validate_lookup_integer(event_id)
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
        .order_by(AmericanoRegistration.registration_order).execution_options(populate_existing=True)
    ).all())


def _zones(session: Session, event_id: int) -> list[AmericanoZone]:
    return list(session.exec(
        select(AmericanoZone).where(AmericanoZone.event_id == event_id)
        .order_by(AmericanoZone.label).execution_options(populate_existing=True)
    ).all())


def _summary(session: Session, event: AmericanoEvent, registration_count: int) -> dto.EventSummary:
    rounds = session.exec(
        select(AmericanoRound).where(AmericanoRound.event_id == event.id)
        .order_by(AmericanoRound.number).execution_options(populate_existing=True)
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


def _validate_revision(event: AmericanoEvent, expected_revision: int) -> None:
    if event.revision != expected_revision:
        raise AmericanoError(
            409, "revision_conflict", "El evento cambió; recargá antes de guardar.",
            current_revision=event.revision,
            fields=[dto.AmericanoFieldError(
                path=["expected_revision"], code="stale", message="Revisión obsoleta.",
            )],
        )


def _validate_draft(event: AmericanoEvent, expected_revision: int) -> None:
    _validate_revision(event, expected_revision)
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
    _validate_lookup_integer(registration_id)
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


def _round_response(
    detail: dto.EventDetail, planned: FixtureRound, matches: list[AmericanoGroupMatch],
    *, saved: bool = False,
) -> dto.RoundResponse:
    """Combine persisted matches with deterministic rests for an unlocked round."""
    registrations = {registration.id: registration for registration in detail.registrations}
    return dto.RoundResponse(
        event_id=detail.id, event_name=detail.name, state=detail.state,
        revision=detail.revision, groups_revision=detail.groups_revision,
        number=planned.number, total_rounds=detail.total_rounds, max_unlocked_round=detail.max_unlocked_round,
        saved=saved, locked=False, read_only=detail.state in {"playoffs", "completed"}, zones=detail.zones,
        matches=[dto.GroupMatch(
            id=match.id, zone_id=match.zone_id, display_order=match.display_order,
            registration_a=registrations[match.registration_a_id],
            registration_b=registrations[match.registration_b_id],
            games_a=match.games_a, games_b=match.games_b,
        ) for match in matches],
        resting=[dto.RestingRegistration(
            registration=registrations[rest.registration_id], reason=rest.reason,
        ) for rest in planned.resting],
    )


def generate_fixture(
    session: Session, event_id: int, data: dto.RevisionRequest,
) -> dto.GenerateFixtureResponse:
    with _transaction(session, write=True):
        event = _event(session, event_id, write=True)
        _validate_draft(event, data.expected_revision)
        zones = _zones(session, event.id)
        registrations = _registrations(session, event.id)
        if [zone.label for zone in zones] != list(AmericanoZoneLabel)[:event.zone_count]:
            raise AmericanoError(422, "invalid_configuration", "Las zonas del evento están incompletas.")
        required = qualification_quotas(event.start_stage.value, [zone.id for zone in zones])
        if any(registration.zone_id not in required for registration in registrations):
            raise AmericanoError(
                422, "invalid_configuration", "Todas las parejas deben tener una zona propia asignada.",
            )
        for zone in zones:
            if sum(registration.zone_id == zone.id for registration in registrations) < required[zone.id]:
                raise AmericanoError(
                    422, "invalid_configuration",
                    f"La zona {zone.label.value} requiere {required[zone.id]} parejas.",
                )
        fixture = build_fixture([
            ZoneInput(zone.id, zone.label.value, tuple(
                registration.id for registration in registrations if registration.zone_id == zone.id
            )) for zone in zones
        ])
        first_matches = []
        for planned_round in fixture:
            round_ = AmericanoRound(event_id=event.id, number=planned_round.number)
            session.add(round_)
            session.flush()
            for planned_match in planned_round.matches:
                match = AmericanoGroupMatch(
                    event_id=event.id, round_id=round_.id, zone_id=planned_match.zone_id,
                    registration_a_id=planned_match.registration_a_id,
                    registration_b_id=planned_match.registration_b_id,
                    display_order=planned_match.display_order,
                )
                session.add(match)
                if planned_round.number == 1:
                    first_matches.append(match)
        event.state = AmericanoEventState.GROUPS if fixture else AmericanoEventState.REVIEW
        detail = _changed_detail(session, event)
        return dto.GenerateFixtureResponse(
            event=detail,
            first_round=_round_response(detail, fixture[0], first_matches) if fixture else None,
        )


def _round_record(session: Session, event_id: int, number: int) -> AmericanoRound:
    _validate_lookup_integer(number)
    round_ = session.exec(select(AmericanoRound).where(
        AmericanoRound.event_id == event_id, AmericanoRound.number == number,
    ).execution_options(populate_existing=True)).first()
    if round_ is None:
        raise AmericanoError(404, "not_found", "Evento o recurso no encontrado.")
    return round_


def _round_matches(session: Session, event_id: int, round_id: int) -> list[AmericanoGroupMatch]:
    return list(session.exec(select(AmericanoGroupMatch).where(
        AmericanoGroupMatch.event_id == event_id, AmericanoGroupMatch.round_id == round_id,
    ).order_by(AmericanoGroupMatch.display_order).execution_options(populate_existing=True)).all())


def _validate_unlocked(event: AmericanoEvent, number: int, max_unlocked_round: int) -> None:
    if number > max_unlocked_round:
        raise AmericanoError(
            409, "round_locked", "Guardá las rondas anteriores antes de abrir esta ronda.",
            current_revision=event.revision,
        )


def _round_detail(session: Session, event: AmericanoEvent, number: int) -> dto.RoundResponse:
    """Materialize a round inside the caller's event lock and transaction."""
    round_ = _round_record(session, event.id, number)
    detail = _detail(session, event)
    _validate_unlocked(event, number, detail.max_unlocked_round)
    fixture = build_fixture([
        ZoneInput(zone.id, zone.label, tuple(
            registration.id for registration in detail.registrations if registration.zone_id == zone.id
        )) for zone in detail.zones
    ])
    return _round_response(
        detail, fixture[number - 1], _round_matches(session, event.id, round_.id),
        saved=round_.saved_at is not None,
    )


def load_round(session: Session, event_id: int, number: int) -> dto.RoundResponse:
    with _transaction(session):
        return _round_detail(session, _event(session, event_id), number)


def _standings_detail(session: Session, event: AmericanoEvent) -> dto.StandingsResponse:
    """Materialize standings without committing or releasing the caller's lock."""
    detail = _detail(session, event)
    zone_ids = {zone.id for zone in detail.zones}
    matches = session.exec(select(AmericanoGroupMatch).join(
        AmericanoRound, AmericanoGroupMatch.round_id == AmericanoRound.id,
    ).where(
        AmericanoGroupMatch.event_id == event.id, AmericanoRound.event_id == event.id,
        AmericanoRound.saved_at.is_not(None),
    ).execution_options(populate_existing=True)).all()
    standings = calculate_standings([
        StandingRegistration(**registration.model_dump()) for registration in detail.registrations
        if registration.zone_id in zone_ids
    ], [SavedScore(
        match.id, match.zone_id, match.registration_a_id, match.registration_b_id,
        match.games_a, match.games_b,
    ) for match in matches if match.games_a is not None and match.games_b is not None])
    by_zone = {zone.zone_id: zone.blocks for zone in standings}
    return dto.StandingsResponse(
        event_id=event.id, state=detail.state, revision=detail.revision,
        groups_revision=detail.groups_revision, frozen=detail.state in {"playoffs", "completed"},
        zones=[dto.ZoneStandings(zone=zone, blocks=[dto.StandingBlock(
            position_from=block.position_from, position_to=block.position_to,
            points_half_units=block.points_half_units, games_diff=block.games_diff,
            rows=[dto.StandingRow(**asdict(row)) for row in block.rows],
        ) for block in by_zone.get(zone.id, ())]) for zone in detail.zones],
    )


def load_standings(session: Session, event_id: int) -> dto.StandingsResponse:
    with _transaction(session):
        return _standings_detail(session, _event(session, event_id))


def save_round(
    session: Session, event_id: int, number: int, data: dto.SaveRoundRequest,
) -> dto.SaveRoundResponse:
    with _transaction(session, write=True):
        event = _event(session, event_id, write=True)
        _validate_revision(event, data.expected_revision)
        if event.state not in {AmericanoEventState.GROUPS, AmericanoEventState.REVIEW}:
            raise AmericanoError(
                409, "state_conflict", "Los resultados de grupos no pueden editarse en esta fase.",
                current_revision=event.revision,
            )
        round_ = _round_record(session, event.id, number)
        _validate_unlocked(event, number, _detail(session, event).max_unlocked_round)
        matches = _round_matches(session, event.id, round_.id)
        results = {result.match_id: result for result in data.results}
        expected_ids = {match.id for match in matches}
        extra_ids = set(results) - expected_ids
        if extra_ids:
            # Compare untrusted JSON-safe IDs in Python, never bind them to INTEGER.
            own_ids = set(session.exec(select(AmericanoGroupMatch.id).where(
                AmericanoGroupMatch.event_id == event.id,
            )).all())
            if not extra_ids <= own_ids:
                raise AmericanoError(
                    422, "invalid_reference", "Los resultados contienen referencias ajenas al evento.",
                )
        if set(results) != expected_ids:
            raise AmericanoError(
                422, "invalid_round_results", "Enviá todos y solo los partidos de la ronda.",
                fields=[dto.AmericanoFieldError(
                    path=["results"], code="membership", message="El conjunto de partidos no coincide con la ronda.",
                )],
            )
        all_others_saved = session.exec(select(AmericanoRound.id).where(
            AmericanoRound.event_id == event.id, AmericanoRound.id != round_.id,
            AmericanoRound.saved_at.is_(None),
        )).first() is None
        changed = any(
            (match.games_a, match.games_b) != (results[match.id].games_a, results[match.id].games_b)
            for match in matches
        )
        if changed:
            for resolution in session.exec(select(AmericanoTieResolution).where(
                AmericanoTieResolution.event_id == event.id,
            )).all():
                session.delete(resolution)
            event.groups_revision += 1
        for match in matches:
            result = results[match.id]
            match.games_a, match.games_b = result.games_a, result.games_b
            session.add(match)
        round_.saved_at = round_.saved_at or datetime.now(UTC)
        session.add(round_)
        if all_others_saved:
            event.state = AmericanoEventState.REVIEW
        event.revision += 1
        session.add(event)
        session.flush()
        return dto.SaveRoundResponse(
            round=_round_detail(session, event, number), standings=_standings_detail(session, event),
        )
