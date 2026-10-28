"""Private Americano operations; one event lock and one transaction per request."""

from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import UTC, datetime
from random import shuffle

from sqlmodel import Session, select

from app.americanos import schemas as dto
from app.americanos.bracket import (
    APPROVED_CORRECTION_POLICY, APPROVED_SET_CONVENTION, BracketChange, FullSetScore,
    NodeRef, OpeningPair, SeedSource, SeedingTemplate, bracket_layout, build_bracket,
    propagate_winner, validate_full_set,
)
from app.americanos.fixture import AmericanoDomainError, FixtureRound, ZoneInput, build_fixture
from app.americanos.models import (
    AmericanoEvent, AmericanoEventState, AmericanoGroupMatch, AmericanoKnockoutMatch, AmericanoQualifierSnapshot,
    AmericanoRegistration, AmericanoRound,
    AmericanoSide, AmericanoStage, AmericanoTieResolution, AmericanoZone, AmericanoZoneLabel,
)
from app.americanos.qualification import ResolvedSeed, SeedRef, TieResolution, qualification_preview, qualification_quotas
from app.americanos.standings import (
    SavedScore, StandingBlock, StandingRegistration, StandingRow, ZoneStanding, calculate_standings,
)


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


def _courts(event: AmericanoEvent) -> list[int]:
    return [number for number in range(1, 7) if event.court_mask & (1 << (number - 1))]


def _summary(session: Session, event: AmericanoEvent, registrations: list[AmericanoRegistration]) -> dto.EventSummary:
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
    champion = next((pair for pair in registrations if pair.id == event.champion_registration_id), None)
    return dto.EventSummary(
        id=event.id, name=event.name, state=event.state.value,
        zone_count=event.zone_count, start_stage=event.start_stage.value,
        courts=_courts(event),
        revision=event.revision, groups_revision=event.groups_revision,
        registration_count=len(registrations), total_rounds=len(rounds),
        saved_rounds=sum(round_.saved_at is not None for round_ in rounds),
        max_unlocked_round=unlocked, continuation=continuation,
        champion=dto.Registration.model_validate(champion, from_attributes=True) if champion else None,
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
        **_summary(session, event, registrations).model_dump(),
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
        return [_summary(session, event, _registrations(session, event.id)) for event in events]


def create_event(session: Session, data: dto.CreateEventRequest) -> dto.EventDetail:
    with _transaction(session, write=True):
        event = AmericanoEvent(
            name=data.name, zone_count=data.zone_count, start_stage=AmericanoStage(data.start_stage),
            court_mask=sum(1 << (court - 1) for court in data.courts),
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
        if "courts" in changes:
            event.court_mask = sum(1 << (court - 1) for court in changes.pop("courts"))
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
        registrations = _compact_registration_orders(session, event.id)
        zone_id = _zones(session, event.id)[0].id if event.zone_count == 1 else None
        session.add(AmericanoRegistration(
            event_id=event.id, zone_id=zone_id,
            player1_name=data.player1_name, player2_name=data.player2_name,
            registration_order=len(registrations) + 1,
        ))
        return _changed_detail(session, event)


def add_registrations(
    session: Session, event_id: int, data: dto.BulkRegistrationRequest,
) -> dto.EventDetail:
    with _transaction(session, write=True):
        event = _event(session, event_id, write=True)
        _validate_draft(event, data.expected_revision)
        registrations = _compact_registration_orders(session, event.id)
        zone_id = _zones(session, event.id)[0].id if event.zone_count == 1 else None
        first_order = len(registrations) + 1
        session.add_all([
            AmericanoRegistration(
                event_id=event.id,
                zone_id=zone_id,
                player1_name=pair.player1_name,
                player2_name=pair.player2_name,
                registration_order=first_order + offset,
            )
            for offset, pair in enumerate(data.registrations)
        ])
        return _changed_detail(session, event)


def _compact_registration_orders(session: Session, event_id: int) -> list[AmericanoRegistration]:
    registrations = _registrations(session, event_id)
    if all(registration.registration_order == order for order, registration in enumerate(registrations, 1)):
        return registrations

    # Stage above the current range so the immediate UNIQUE constraint cannot
    # collide while gaps are compacted after deletions or older drafts.
    last_order = max((registration.registration_order for registration in registrations), default=0)
    for offset, registration in enumerate(registrations, 1):
        registration.registration_order = last_order + offset
        session.add(registration)
    session.flush()

    for order, registration in enumerate(registrations, 1):
        registration.registration_order = order
        session.add(registration)
    session.flush()
    return registrations


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
        session.flush()
        _compact_registration_orders(session, event.id)
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


def clear_zones(session: Session, event_id: int, expected_revision: int) -> dto.EventDetail:
    with _transaction(session, write=True):
        event = _event(session, event_id, write=True)
        _validate_draft(event, expected_revision)
        if event.zone_count != 2:
            raise AmericanoError(
                422, "invalid_configuration", "Solo se puede limpiar el reparto cuando hay dos zonas.",
            )
        for registration in _registrations(session, event.id):
            registration.zone_id = None
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
            court_number=match.court_number,
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
        ], courts=_courts(event))
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
                    court_number=planned_match.court_number,
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
    ], courts=detail.courts)
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


def _seeding_template(detail: dto.EventDetail) -> SeedingTemplate:
    """Apply the six approved D6 templates, using label order and real zone IDs."""
    a = detail.zones[0].id
    if detail.zone_count == 1:
        positions = {
            "quarterfinal": [(1, 8), (4, 5), (2, 7), (3, 6)],
            "semifinal": [(1, 4), (2, 3)], "final": [(1, 2)],
        }[detail.start_stage]
        pairs = [(SeedRef(a, first), SeedRef(a, second)) for first, second in positions]
        suffix = "one-zone"
    else:
        b = detail.zones[1].id
        pairs = {
            "quarterfinal": [
                (SeedRef(a, 1), SeedRef(b, 4)), (SeedRef(b, 2), SeedRef(a, 3)),
                (SeedRef(b, 1), SeedRef(a, 4)), (SeedRef(a, 2), SeedRef(b, 3)),
            ],
            "semifinal": [(SeedRef(a, 1), SeedRef(b, 2)), (SeedRef(b, 1), SeedRef(a, 2))],
            "final": [(SeedRef(a, 1), SeedRef(b, 1))],
        }[detail.start_stage]
        suffix = "two-zones"
    return SeedingTemplate(
        f"{detail.start_stage}-{suffix}-v1", "approved", detail.start_stage, detail.zone_count,
        tuple(OpeningPair(first, second) for first, second in pairs),
    )


def _qualification_detail(
    session: Session, event: AmericanoEvent, resolutions: list[dto.TieResolution] | None = None,
) -> dto.QualificationResponse:
    """Compose a preview under the caller's event lock; never create bracket rows."""
    detail = _detail(session, event)
    standings = _standings_detail(session, event)
    template = _seeding_template(detail)
    frozen = standings.frozen
    blockers = []
    if (event.state == AmericanoEventState.DRAFT or detail.saved_rounds != detail.total_rounds
            or session.exec(select(AmericanoGroupMatch.id).where(
                AmericanoGroupMatch.event_id == event.id,
                (AmericanoGroupMatch.games_a.is_(None) | AmericanoGroupMatch.games_b.is_(None)),
            )).first() is not None):
        blockers.append(dto.QualificationBlocker(
            code="groups_incomplete", message="Faltan resultados de grupos guardados.",
        ))
    slots, missing, seeds = [], [], []
    if detail.configuration_issues:
        blockers.append(dto.QualificationBlocker(
            code="configuration_invalid", message="La configuración no permite completar los cupos.",
        ))
    else:
        # The standings DTO is already materialized from complete saved scores only.
        blocks = [ZoneStanding(zone.zone.id, tuple(StandingBlock(
            block.position_from, block.position_to, block.points_half_units, block.games_diff,
            tuple(StandingRow(
                registration=StandingRegistration(**row.registration.model_dump()),
                **row.model_dump(exclude={"registration"}),
            ) for row in block.rows),
        ) for block in zone.blocks)) for zone in standings.zones]
        if resolutions is None:
            resolutions = [dto.TieResolution(
                zone_id=row.zone_id, position=row.position, registration_id=row.registration_id,
            ) for row in session.exec(select(AmericanoTieResolution).where(
                AmericanoTieResolution.event_id == event.id,
                AmericanoTieResolution.source_groups_revision == event.groups_revision,
            )).all()] if not frozen else []
        try:
            preview = qualification_preview(
                blocks, qualification_quotas(detail.start_stage, [zone.id for zone in detail.zones]),
                [TieResolution(**resolution.model_dump()) for resolution in resolutions],
            )
        except AmericanoDomainError as exc:
            raise AmericanoError(422, exc.code, exc.message, fields=[dto.AmericanoFieldError(
                path=list(exc.path), code=exc.code, message=exc.message,
            )]) from exc
        slots = [dto.QualificationSlot(
            **{**asdict(slot), "candidate_registration_ids": list(slot.candidate_registration_ids)},
        ) for slot in preview.slots]
        if frozen:
            # Closed previews take their selections from the canonical snapshot,
            # not a surviving manual resolution or the visual standing row order.
            snapshots = session.exec(select(AmericanoQualifierSnapshot).where(
                AmericanoQualifierSnapshot.event_id == event.id,
            ).order_by(AmericanoQualifierSnapshot.zone_id, AmericanoQualifierSnapshot.position)).all()
            selected = {(row.zone_id, row.position): row.registration_id for row in snapshots}
            slots = [slot.model_copy(update={
                "registration_id": selected.get((slot.zone_id, slot.position)),
            }) for slot in slots]
        missing = [dto.SeedRef(zone_id=slot.zone_id, position=slot.position)
                   for slot in slots if slot.registration_id is None]
        seeds = [dto.ResolvedSeed(
            zone_id=slot.zone_id, position=slot.position, registration_id=slot.registration_id,
        ) for slot in slots if slot.registration_id is not None]
        if missing:
            blockers.append(dto.QualificationBlocker(
                code="unresolved_ties", message="Seleccioná las parejas para todas las plazas empatadas relevantes.",
            ))
    selected = {(seed.zone_id, seed.position): seed.registration_id for seed in seeds}

    def participant(source):
        return selected.get((source.zone_id, source.position)) if isinstance(source, SeedSource) else None

    return dto.QualificationResponse(
        event_id=event.id, state=detail.state, revision=event.revision,
        source_groups_revision=event.groups_revision, standings=standings.zones,
        quotas=detail.quotas, slots=slots, missing_slots=missing, resolved_seeds=seeds,
        seeding_template=dto.SeedingTemplate(**asdict(template) | {
            "opening_pairs": [dto.OpeningPair(**asdict(pair)) for pair in template.opening_pairs],
        }),
        bracket=[dto.BracketPreviewNode(
            stage=node.stage, slot=node.slot, source_a=asdict(node.source_a), source_b=asdict(node.source_b),
            registration_a_id=participant(node.source_a), registration_b_id=participant(node.source_b),
            next=asdict(node.next) if node.next else None,
        ) for node in bracket_layout(detail.start_stage, template)],
        blockers=blockers, can_confirm=event.state == AmericanoEventState.REVIEW and not blockers,
        frozen=frozen,
    )


def load_qualification(session: Session, event_id: int) -> dto.QualificationResponse:
    with _transaction(session):
        return _qualification_detail(session, _event(session, event_id))


def save_tie_resolutions(
    session: Session, event_id: int, data: dto.SaveTieResolutionsRequest,
) -> dto.QualificationResponse:
    with _transaction(session, write=True):
        event = _event(session, event_id, write=True)
        _validate_revision(event, data.expected_revision)
        if event.state != AmericanoEventState.REVIEW:
            raise AmericanoError(
                409, "state_conflict", "Los desempates solo pueden resolverse en revisión de grupos.",
                current_revision=event.revision,
            )
        if event.groups_revision != data.source_groups_revision:
            raise AmericanoError(
                409, "groups_revision_conflict", "Los resultados cambiaron; recargá la clasificación.",
                current_revision=event.revision, fields=[dto.AmericanoFieldError(
                    path=["source_groups_revision"], code="stale", message="Revisión de grupos obsoleta.",
                )],
            )
        preview = _qualification_detail(session, event, data.resolutions)
        if any(blocker.code == "groups_incomplete" for blocker in preview.blockers):
            raise AmericanoError(
                409, "state_conflict", "Faltan resultados de grupos guardados.", current_revision=event.revision,
            )
        if any(blocker.code == "configuration_invalid" for blocker in preview.blockers):
            raise AmericanoError(422, "invalid_configuration", "La configuración no permite completar los cupos.")
        if preview.missing_slots:
            raise AmericanoError(
                422, "invalid_tie_resolution", "Enviá todas las plazas empatadas relevantes.",
                fields=[dto.AmericanoFieldError(
                    path=["resolutions"], code="incomplete", message="Faltan plazas por resolver.",
                )],
            )
        for row in session.exec(select(AmericanoTieResolution).where(
            AmericanoTieResolution.event_id == event.id,
        )).all():
            session.delete(row)
        # Release unique seed/registration keys before inserting replacements;
        # swapping selected pairs must not depend on ORM flush ordering.
        session.flush()
        for resolution in data.resolutions:
            session.add(AmericanoTieResolution(
                event_id=event.id, source_groups_revision=event.groups_revision,
                **resolution.model_dump(),
            ))
        event.revision += 1
        session.add(event)
        session.flush()
        return preview.model_copy(update={"revision": event.revision})


def _validate_complete_groups(session: Session, event: AmericanoEvent, detail: dto.EventDetail) -> None:
    """Check the complete persisted fixture, not merely the rows still present."""
    fixture = build_fixture([
        ZoneInput(zone.id, zone.label, tuple(
            registration.id for registration in detail.registrations if registration.zone_id == zone.id
        )) for zone in detail.zones
    ], courts=detail.courts)
    rounds = session.exec(select(AmericanoRound).where(
        AmericanoRound.event_id == event.id,
    ).execution_options(populate_existing=True)).all()
    matches = session.exec(select(AmericanoGroupMatch).where(
        AmericanoGroupMatch.event_id == event.id,
    ).execution_options(populate_existing=True)).all()
    round_numbers = {round_.id: round_.number for round_ in rounds}
    expected = {
        (round_.number, match.zone_id, match.registration_a_id, match.registration_b_id, match.display_order,
         match.court_number)
        for round_ in fixture for match in round_.matches
    }
    actual = {
        (round_numbers.get(match.round_id), match.zone_id, match.registration_a_id,
         match.registration_b_id, match.display_order, match.court_number) for match in matches
    }
    if ({round_.number for round_ in rounds} != {round_.number for round_ in fixture}
            or any(round_.saved_at is None for round_ in rounds) or actual != expected
            or any(match.games_a is None or match.games_b is None for match in matches)):
        raise AmericanoError(
            409, "state_conflict", "Faltan resultados de grupos íntegros y guardados.",
            current_revision=event.revision,
        )


def _playoffs_detail(session: Session, event: AmericanoEvent) -> dto.PlayoffsResponse:
    """Read canonical persisted nodes/snapshots inside the caller's event lock."""
    if event.state not in {AmericanoEventState.PLAYOFFS, AmericanoEventState.COMPLETED}:
        raise AmericanoError(
            409, "state_conflict", "Confirmá los clasificados antes de consultar el cuadro.",
            current_revision=event.revision,
        )
    detail = _detail(session, event)
    registrations = {registration.id: registration for registration in detail.registrations}
    snapshots = session.exec(select(AmericanoQualifierSnapshot).where(
        AmericanoQualifierSnapshot.event_id == event.id,
    ).order_by(AmericanoQualifierSnapshot.zone_id, AmericanoQualifierSnapshot.position)
        .execution_options(populate_existing=True)).all()
    nodes = session.exec(select(AmericanoKnockoutMatch).where(
        AmericanoKnockoutMatch.event_id == event.id,
    ).execution_options(populate_existing=True)).all()
    stage_order = {"quarterfinal": 0, "semifinal": 1, "final": 2}
    nodes = sorted(nodes, key=lambda node: (stage_order[node.stage.value], node.slot))
    by_id = {node.id: node for node in nodes}

    def edit_block_reason(node: AmericanoKnockoutMatch):
        if node.registration_a_id is None or node.registration_b_id is None:
            return "participants_pending"
        descendant = by_id.get(node.next_match_id)
        while descendant is not None:
            if descendant.set_complete or descendant.games_a is not None or descendant.games_b is not None:
                return "descendant_played"
            descendant = by_id.get(descendant.next_match_id)
        return None

    result_nodes = []
    for node in nodes:
        reason = edit_block_reason(node)
        result_nodes.append(dto.KnockoutNode(
            id=node.id, stage=node.stage.value, slot=node.slot,
            court_number=node.court_number,
            registration_a=registrations.get(node.registration_a_id),
            registration_b=registrations.get(node.registration_b_id),
            games_a=node.games_a, games_b=node.games_b, set_complete=node.set_complete,
            next_match_id=node.next_match_id, next_side=node.next_side.value if node.next_side else None,
            winner_registration_id=node.winner_registration_id,
            can_edit=reason is None, edit_block_reason=reason,
        ))
    return dto.PlayoffsResponse(
        event_id=event.id, event_name=detail.name, state=detail.state,
        revision=event.revision, groups_revision=event.groups_revision, start_stage=detail.start_stage,
        courts=detail.courts,
        zones=detail.zones,
        snapshots=[dto.QualifierSnapshot(**{
            field: getattr(snapshot, field) for field in dto.QualifierSnapshot.model_fields
        }) for snapshot in snapshots],
        nodes=result_nodes, champion=registrations.get(event.champion_registration_id),
    )


def load_playoffs(session: Session, event_id: int) -> dto.PlayoffsResponse:
    with _transaction(session):
        return _playoffs_detail(session, _event(session, event_id))


def assign_knockout_court(
    session: Session, event_id: int, node_id: int, data: dto.AssignKnockoutCourtRequest,
) -> dto.PlayoffsResponse:
    """Courts are logistical suggestions, independent of scores and bracket propagation.

    Reuse is allowed: matches in a stage need not be simultaneous. The UI makes
    this explicit rather than presenting a stage as a global group round.
    """
    with _transaction(session, write=True):
        event = _event(session, event_id, write=True)
        _validate_revision(event, data.expected_revision)
        if event.state != AmericanoEventState.PLAYOFFS:
            raise AmericanoError(409, "state_conflict", "Las canchas se ajustan durante las eliminatorias.")
        _validate_lookup_integer(node_id)
        node = session.exec(select(AmericanoKnockoutMatch).where(
            AmericanoKnockoutMatch.event_id == event.id, AmericanoKnockoutMatch.id == node_id,
        ).execution_options(populate_existing=True)).first()
        if node is None:
            raise AmericanoError(404, "not_found", "Partido no encontrado.")
        if node.set_complete:
            raise AmericanoError(409, "state_conflict", "No se cambia la cancha de un partido ya jugado.")
        if data.court_number not in _courts(event):
            raise AmericanoError(422, "invalid_configuration", "La cancha no está disponible para este americano.")
        node.court_number = data.court_number
        session.add(node)
        event.revision += 1
        session.add(event)
        session.flush()
        return _playoffs_detail(session, event)


def _canonical_bracket(session: Session, event: AmericanoEvent):
    """Adapt stored rows using frozen seeds and approved topology, never row IDs as slots."""
    detail = _detail(session, event)
    snapshots = session.exec(select(AmericanoQualifierSnapshot).where(
        AmericanoQualifierSnapshot.event_id == event.id,
    ).execution_options(populate_existing=True)).all()
    if any(snapshot.source_groups_revision != event.confirmed_source_revision for snapshot in snapshots):
        raise AmericanoDomainError("invalid_configuration", "Snapshot source revision is inconsistent.")
    planned = build_bracket(detail.start_stage, [ResolvedSeed(
        row.zone_id, row.position, row.registration_id,
    ) for row in snapshots], _seeding_template(detail))
    rows = session.exec(select(AmericanoKnockoutMatch).where(
        AmericanoKnockoutMatch.event_id == event.id,
    ).execution_options(populate_existing=True)).all()
    by_ref = {(row.stage.value, row.slot): row for row in rows}
    if set(by_ref) != {(node.stage, node.slot) for node in planned}:
        raise AmericanoDomainError("invalid_configuration", "The persisted bracket is incomplete.")
    nodes = []
    for node in planned:
        row = by_ref[node.stage, node.slot]
        expected_next = by_ref[node.next.stage, node.next.slot].id if node.next else None
        expected_side = node.next.side if node.next else None
        if (row.next_match_id != expected_next
                or (row.next_side.value if row.next_side else None) != expected_side):
            raise AmericanoDomainError("invalid_configuration", "The persisted bracket destination is inconsistent.")
        for side in ("a", "b"):
            if (isinstance(getattr(node, f"source_{side}"), SeedSource)
                    and getattr(row, f"registration_{side}_id") != getattr(node, f"registration_{side}_id")):
                raise AmericanoDomainError("invalid_configuration", "Opening participants must match frozen seeds.")
        nodes.append(replace(
            node, registration_a_id=row.registration_a_id, registration_b_id=row.registration_b_id,
            games_a=row.games_a, games_b=row.games_b, set_complete=row.set_complete,
        ))
    return nodes, by_ref


def save_knockout(
    session: Session, event_id: int, node_id: int, data: dto.SaveKnockoutRequest,
) -> dto.PlayoffsResponse:
    with _transaction(session, write=True):
        event = _event(session, event_id, write=True)
        _validate_lookup_integer(node_id)
        row = session.exec(select(AmericanoKnockoutMatch).where(
            AmericanoKnockoutMatch.event_id == event.id, AmericanoKnockoutMatch.id == node_id,
        ).execution_options(populate_existing=True)).first()
        # A foreign nested ID must not disclose this event's phase/revision.
        if row is None:
            raise AmericanoError(404, "not_found", "Evento o recurso no encontrado.")
        _validate_revision(event, data.expected_revision)
        if event.state not in {AmericanoEventState.PLAYOFFS, AmericanoEventState.COMPLETED}:
            raise AmericanoError(
                409, "state_conflict", "Los resultados eliminatorios requieren clasificados confirmados.",
                current_revision=event.revision,
            )
        try:
            score = validate_full_set(
                FullSetScore(data.games_a, data.games_b, data.set_complete), APPROVED_SET_CONVENTION,
            )
            nodes, by_ref = _canonical_bracket(session, event)
            propagated = propagate_winner(nodes, BracketChange(
                NodeRef(row.stage.value, row.slot), score, APPROVED_CORRECTION_POLICY,
            ))
        except AmericanoDomainError as exc:
            status = 409 if exc.code in {"participants_pending", "descendant_played"} else 422
            metadata = {"current_revision": event.revision} if status == 409 else {}
            if exc.path:
                metadata["fields"] = [dto.AmericanoFieldError(
                    path=list(exc.path), code=exc.code, message=exc.message,
                )]
            raise AmericanoError(status, exc.code, exc.message, **metadata) from exc
        row.games_a, row.games_b, row.set_complete = score.games_a, score.games_b, True
        row.winner_registration_id = row.registration_a_id if score.winner_side == "a" else row.registration_b_id
        session.add(row)
        session.flush()
        # The pure result changes only this node and its own next side. Persist
        # only differing participants: never overwrite a sibling result/side.
        for node in propagated.nodes:
            stored = by_ref[node.stage, node.slot]
            for side in ("a", "b"):
                field = f"registration_{side}_id"
                if getattr(stored, field) != getattr(node, field):
                    setattr(stored, field, getattr(node, field))
                    session.add(stored)
        if propagated.champion_registration_id is not None:
            event.champion_registration_id = propagated.champion_registration_id
            event.state = AmericanoEventState.COMPLETED
        event.revision += 1  # identical accepted PUTs advance the global revision too
        session.add(event)
        session.flush()
        return _playoffs_detail(session, event)


def _confirmation_detail(session: Session, event: AmericanoEvent) -> dto.ConfirmationResponse:
    detail = _detail(session, event)
    return dto.ConfirmationResponse(
        event=detail, confirmation_key=event.confirmation_key,
        confirmed_source_revision=event.confirmed_source_revision,
        confirmed_at=detail.confirmed_at, playoffs=_playoffs_detail(session, event),
    )


def confirm_qualifiers(
    session: Session, event_id: int, data: dto.ConfirmQualifiersRequest,
) -> dto.ConfirmationResponse:
    with _transaction(session, write=True):
        event = _event(session, event_id, write=True)
        # The DTO normalizes UUID representations. Replay is deliberately before
        # revision/state checks and returns the CURRENT canonical bracket.
        if event.confirmation_key is not None:
            if event.confirmation_key == data.confirmation_key:
                return _confirmation_detail(session, event)
            raise AmericanoError(
                409, "already_confirmed", "Los clasificados ya fueron confirmados por otra operación.",
                current_revision=event.revision,
            )
        _validate_revision(event, data.expected_revision)
        if event.state != AmericanoEventState.REVIEW:
            raise AmericanoError(
                409, "state_conflict", "Completá todos los grupos antes de confirmar los clasificados.",
                current_revision=event.revision,
            )
        if event.groups_revision != data.source_groups_revision:
            raise AmericanoError(
                409, "groups_revision_conflict", "Los resultados cambiaron; recargá la clasificación.",
                current_revision=event.revision, fields=[dto.AmericanoFieldError(
                    path=["source_groups_revision"], code="stale", message="Revisión de grupos obsoleta.",
                )],
            )
        detail = _detail(session, event)
        if detail.configuration_issues:
            raise AmericanoError(422, "invalid_configuration", "La configuración no permite completar los cupos.")
        _validate_complete_groups(session, event, detail)
        preview = _qualification_detail(session, event)
        if preview.missing_slots:
            raise AmericanoError(
                422, "invalid_tie_resolution", "Resolvé todas las plazas empatadas antes de confirmar.",
                fields=[dto.AmericanoFieldError(
                    path=["resolutions"], code="incomplete", message="Faltan plazas por resolver.",
                )],
            )
        template = _seeding_template(detail)
        if template.status != "approved":
            raise AmericanoError(
                409, "decision_pending", "La siembra todavía requiere aprobación.", current_revision=event.revision,
            )
        bracket = build_bracket(
            detail.start_stage, [ResolvedSeed(**seed.model_dump()) for seed in preview.resolved_seeds], template,
        )
        standing_rows = {
            row.registration.id: row for zone in preview.standings for block in zone.blocks for row in block.rows
        }
        for seed in preview.resolved_seeds:
            row = standing_rows[seed.registration_id]
            session.add(AmericanoQualifierSnapshot(
                event_id=event.id, **seed.model_dump(),
                player1_name=row.registration.player1_name, player2_name=row.registration.player2_name,
                points_half_units=row.points_half_units, games_diff=row.games_diff,
                source_groups_revision=event.groups_revision,
            ))
        session.flush()
        persisted = {}
        # Descendants first: immediate FK + CHECK forbid a temporary null
        # destination on a non-final node, even inside this transaction.
        for planned in reversed(bracket):
            node = AmericanoKnockoutMatch(
                event_id=event.id, stage=AmericanoStage(planned.stage), slot=planned.slot,
                court_number=_courts(event)[(planned.slot - 1) % len(_courts(event))],
                registration_a_id=planned.registration_a_id, registration_b_id=planned.registration_b_id,
                next_match_id=persisted[(planned.next.stage, planned.next.slot)].id if planned.next else None,
                next_side=AmericanoSide(planned.next.side) if planned.next else None,
            )
            session.add(node)
            session.flush()
            persisted[planned.stage, planned.slot] = node
        event.confirmation_key = data.confirmation_key
        event.confirmed_source_revision = event.groups_revision
        event.confirmed_at = datetime.now(UTC)
        event.state = AmericanoEventState.PLAYOFFS
        event.revision += 1
        session.add(event)
        session.flush()
        # DTO validation/materialization belongs to the transaction too.
        return _confirmation_detail(session, event)


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
