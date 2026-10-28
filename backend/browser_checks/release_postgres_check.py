"""Rehearse migration + locking/auth tests ONLY in a fresh local PostgreSQL DB.

The target is fixed to the isolated Docker server. Never reads a production URL,
never drops the user's demo DB. The generated validation DB is left for audit.
"""

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.engine import make_url
from alembic import command
from alembic.config import Config

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
ADMIN_URL = make_url('postgresql+psycopg://liga_dev:liga-local-only@127.0.0.1:5544/postgres')
name = f'liga_release_check_{uuid4().hex[:12]}'
admin_engine = sa.create_engine(ADMIN_URL, isolation_level='AUTOCOMMIT')
with admin_engine.connect() as connection:
    connection.execute(sa.text(f'CREATE DATABASE "{name}"'))  # UUID hex, not user input.
admin_engine.dispose()
url = ADMIN_URL.set(database=name).render_as_string(hide_password=False)
os.environ.update({
    'DATABASE_URL': url, 'TEST_DATABASE_URL': url,
    'LIGA_ENV_FILE': str(ROOT / '.local-dev' / 'no-inherited-settings.env'),
    'SECRET_KEY': 'release-validation-local-only-key-2026',
    'COOKIE_SECURE': 'false', 'COOKIE_SAMESITE': 'lax',
    'CORS_ORIGINS': 'http://testserver',
})
os.chdir(BACKEND)
print(f'Private validation database: {name}', flush=True)
config = Config(str(BACKEND / 'alembic.ini'))
command.upgrade(config, 'f1a62d9c4b83')
engine = sa.create_engine(url)
metadata = sa.MetaData()
metadata.reflect(engine)
tables = {key: table for key, table in metadata.tables.items() if key.startswith('americano_')}
now = datetime.now(UTC)

from app.americanos.fixture import ZoneInput, build_fixture

with engine.begin() as connection:
    def insert(table, **values):
        connection.execute(tables[table].insert().values(created_at=now, updated_at=now, **values))

    insert('americano_events', id=1, name='Legacy seven pairs', state='review', zone_count=1,
           start_stage='final', revision=10, groups_revision=7)
    insert('americano_events', id=2, name='Legacy champion', state='completed', zone_count=1,
           start_stage='final', revision=20, groups_revision=1,
           confirmed_at=now, confirmed_source_revision=1, confirmation_key=str(uuid4()))
    for event_id in (1, 2):
        insert('americano_zones', id=event_id, event_id=event_id, label='A')
    for id_ in range(1, 10):
        event_id = 1 if id_ <= 7 else 2
        insert('americano_registrations', id=id_, event_id=event_id, zone_id=event_id,
               player1_name=f'A{id_}', player2_name=f'B{id_}', registration_order=id_ if id_ <= 7 else id_ - 7)
    match_id = 0
    for round_ in build_fixture([ZoneInput(1, 'A', tuple(range(1, 8)))]):
        insert('americano_rounds', id=round_.number, event_id=1, number=round_.number, saved_at=now)
        for match in round_.matches:
            match_id += 1
            insert('americano_group_matches', id=match_id, event_id=1, round_id=round_.number,
                   zone_id=1, registration_a_id=match.registration_a_id, registration_b_id=match.registration_b_id,
                   display_order=match.display_order, games_a=2, games_b=1)
    for position, id_ in enumerate((8, 9), 1):
        insert('americano_qualifier_snapshots', id=position, event_id=2, zone_id=2, position=position,
               registration_id=id_, player1_name=f'A{id_}', player2_name=f'B{id_}', points_half_units=2,
               games_diff=0, source_groups_revision=1)
    insert('americano_knockout_matches', id=1, event_id=2, stage='final', slot=1,
           registration_a_id=8, registration_b_id=9, games_a=6, games_b=0,
           set_complete=True, winner_registration_id=8)
    connection.execute(tables['americano_events'].update().where(tables['americano_events'].c.id == 2)
                       .values(champion_registration_id=8))
    # Explicit historical IDs must also advance their SERIAL sequences, just as
    # ordinary application INSERTs would have done before the migration.
    for table_name in tables:
        connection.execute(sa.text(
            f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
            f"(SELECT max(id) FROM {table_name}), true) WHERE EXISTS (SELECT 1 FROM {table_name})"
        ))


def snapshot():
    with engine.connect() as connection:
        return {key: [dict(row) for row in connection.execute(sa.select(table).order_by(table.c.id)).mappings()]
                for key, table in tables.items()}


before = snapshot()
command.upgrade(config, 'head')
assert snapshot() == before
with engine.connect() as connection:
    assert connection.execute(sa.text('SELECT court_mask FROM americano_events')).scalars().all() == [63, 63]
    assert connection.execute(sa.text('SELECT count(*) FROM americano_group_matches WHERE court_number = display_order')).scalar_one() == 21
    assert connection.execute(sa.text('SELECT court_number FROM americano_knockout_matches')).scalar_one() == 1
command.downgrade(config, 'f1a62d9c4b83')
assert snapshot() == before
command.upgrade(config, 'head')
assert snapshot() == before
command.check(config)

# A migrated, fully played seven-pair fixture must still be confirmable.
from sqlmodel import Session
from app.americanos import schemas as dto, service

with Session(engine) as session:
    preview = service.load_qualification(session, 1)
    assert preview.can_confirm
    response = service.confirm_qualifiers(session, 1, dto.ConfirmQualifiersRequest(
        expected_revision=preview.revision, source_groups_revision=preview.source_groups_revision,
        confirmation_key=str(uuid4()),
    ))
    assert response.event.state == 'playoffs'
    assert response.playoffs.nodes[0].court_number == 1
    assert next(item for item in service.list_events(session) if item.id == 2).champion.id == 8
engine.dispose()
print('PASS upgrade/downgrade data preservation, metadata parity and legacy fixture confirmation', flush=True)

for args in [
    ['tests/test_americano_confirmation.py', '-k', 'real_postgres'],
    ['tests/test_auth.py', 'tests/test_csrf.py'],
]:
    subprocess.run([sys.executable, '-m', 'pytest', *args, '-q'], cwd=BACKEND, env=os.environ.copy(), check=True)
print(json.dumps({'result': 'PASS', 'database': name, 'legacy_matches_preserved': 21, 'production_touched': False}))
