"""Idempotent demo on the explicitly isolated local database; never production."""

import os

from sqlalchemy.engine import make_url

target = make_url(os.environ.get("DATABASE_URL", "sqlite://"))
if (target.host, target.port, target.database, target.username) != (
    "127.0.0.1", 5544, "liga_americanos_dev", "liga_dev",
):
    raise SystemExit("Refusing demo writes outside the isolated local database.")

from sqlmodel import Session
from app.americanos import schemas as dto, service
from app.database.session import engine

NAME = "Demo empate puestos 1 y 2"
with Session(engine) as session:
    existing = next((event for event in service.list_events(session) if event.name == NAME), None)
    if existing:
        print(f"Demo existente: evento {existing.id} ({existing.state}); no se alteraron sus datos.")
    else:
        detail = service.create_event(session, dto.CreateEventRequest(
            name=NAME, zone_count=1, start_stage="final", courts=[3, 6],
        ))
        for first, second in [("Ana", "Sol"), ("Luz", "Eva"), ("Leo", "Juan"), ("Nico", "Teo")]:
            detail = service.add_registration(session, detail.id, dto.RegistrationRequest(
                expected_revision=detail.revision, player1_name=first, player2_name=second,
            ))
        detail = service.generate_fixture(session, detail.id, dto.RevisionRequest(expected_revision=detail.revision)).event
        top = {pair.id for pair in detail.registrations[:2]}
        for number in range(1, detail.total_rounds + 1):
            round_ = service.load_round(session, detail.id, number)
            results = []
            for match in round_.matches:
                a, b = match.registration_a.id in top, match.registration_b.id in top
                results.append(dto.GroupResult(
                    match_id=match.id, games_a=1 if a == b else 2 if a else 0,
                    games_b=1 if a == b else 2 if b else 0,
                ))
            service.save_round(session, detail.id, number, dto.SaveRoundRequest(expected_revision=round_.revision, results=results))
        preview = service.load_qualification(session, detail.id)
        assert [slot.position for slot in preview.slots if slot.requires_resolution] == [1, 2]
        assert len(preview.missing_slots) == 2 and not preview.can_confirm
        print(f"Demo creada: /admin/americanos/{detail.id}/clasificados; empate real en puestos 1 y 2, pendiente de resolver.")
