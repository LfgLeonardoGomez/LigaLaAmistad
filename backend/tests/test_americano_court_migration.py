"""Trial the additive court migration ONLY on a private in-memory SQLite DB."""

import datetime
import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from .test_americano_metadata import _PlanRecorder, _revision


def test_court_migration_preserves_legacy_rows_and_roundtrips():
    legacy = _revision()
    plan = _PlanRecorder()
    legacy.op = plan
    legacy.upgrade()
    path = Path(__file__).resolve().parents[1] / "migrations/versions/a2c37e91d046_add_americano_courts.py"
    spec = importlib.util.spec_from_file_location("court_migration_trial", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite:///:memory:")
    now = datetime.datetime.now(datetime.UTC)
    timestamps = {"created_at": now, "updated_at": now}
    with engine.connect() as connection:
        plan.metadata.create_all(connection)

        def insert(table, **values):
            connection.execute(plan.metadata.tables[table].insert().values(**timestamps, **values))

        insert("americano_events", id=1, name="Histórico", state="groups", zone_count=1,
               start_stage="final", revision=4, groups_revision=1)
        insert("americano_zones", id=1, event_id=1, label="A")
        for id_ in (1, 2, 3, 4):
            insert("americano_registrations", id=id_, event_id=1, zone_id=1,
                   player1_name=f"A{id_}", player2_name=f"B{id_}", registration_order=id_)
        insert("americano_rounds", id=1, event_id=1, number=1, saved_at=now)
        for id_, pair in enumerate(((1, 4), (2, 3)), 1):
            insert("americano_group_matches", id=id_, event_id=1, round_id=1, zone_id=1,
                   registration_a_id=pair[0], registration_b_id=pair[1], display_order=id_, games_a=2, games_b=0)
        insert("americano_knockout_matches", id=1, event_id=1, stage="final", slot=1, set_complete=False)
        connection.commit()

        def snapshot():
            return {name: [dict(row) for row in connection.execute(sa.select(table).order_by(table.c.id)).mappings()]
                    for name, table in plan.metadata.tables.items()}

        before = snapshot()
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        assert snapshot() == before
        assert connection.exec_driver_sql("SELECT court_mask FROM americano_events").scalar_one() == 63
        assert connection.exec_driver_sql("SELECT court_number FROM americano_group_matches ORDER BY id").scalars().all() == [1, 2]
        assert connection.exec_driver_sql("SELECT court_number FROM americano_knockout_matches").scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        migration.downgrade()
        assert snapshot() == before
        assert "court_mask" not in {column["name"] for column in sa.inspect(connection).get_columns("americano_events")}
        assert "court_number" not in {column["name"] for column in sa.inspect(connection).get_columns("americano_group_matches")}
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    engine.dispose()
