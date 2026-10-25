"""Fresh-process metadata registration; no conftest or existing database.

The child process uses a sole SQLite in-memory engine and never imports app.main.
Migration preparation checks below are purely structural, not migration trials.
"""

import ast
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import AddConstraint, CreateIndex, CreateTable


BACKEND = Path(__file__).resolve().parents[1]
REVISION = BACKEND / "migrations/versions/f1a62d9c4b83_add_americanos.py"


def test_standalone_test_schema_registers_americanos_without_router_import():
    code = """
import sys
from sqlalchemy import event, inspect
from app.database.session import create_db_and_tables, engine
assert str(engine.url) == 'sqlite:///:memory:'
assert 'app.main' not in sys.modules
assert 'app.americanos.models' not in sys.modules
@event.listens_for(engine, 'connect')
def private_memory_only(connection, record):
    assert connection.execute('PRAGMA database_list').fetchone()[2] == ''
    connection.execute('PRAGMA foreign_keys=ON')
create_db_and_tables()
actual = set(inspect(engine).get_table_names())
expected = {'americano_events', 'americano_zones', 'americano_registrations',
    'americano_rounds', 'americano_group_matches', 'americano_tie_resolutions',
    'americano_qualifier_snapshots', 'americano_knockout_matches'}
assert {name for name in actual if name.startswith('americano_')} == expected
assert {'teams', 'zones', 'matches', 'admin_users'} <= actual
assert 'app.main' not in sys.modules
with engine.connect() as connection:
    assert connection.exec_driver_sql('PRAGMA foreign_key_check').all() == []
engine.dispose()
print('Eight Americano tables registered without importing the application')
"""
    environment = {
        **os.environ,
        "PYTHONPATH": str(BACKEND / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "DATABASE_URL": "sqlite:///:memory:",
        "TEST_DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "metadata-regression-private-memory-only-2026",
        "COOKIE_SECURE": "false",
        "COOKIE_SAMESITE": "lax",
    }
    result = subprocess.run(
        [sys.executable, "-B", "-c", code], cwd=BACKEND, env=environment,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Eight Americano tables registered" in result.stdout


class _PlanRecorder:
    """No Alembic context/engine: collect SQLAlchemy objects, never execute DDL."""

    def __init__(self):
        self.metadata = sa.MetaData()
        self.created = []
        self.dropped = []
        self.alters = []
        self.indexes_created = []
        self.indexes_dropped = []

    def create_table(self, name, *items):
        assert name.startswith("americano_")
        self.created.append(name)
        return sa.Table(name, self.metadata, *items)

    def create_index(self, name, table_name, columns):
        assert name.startswith("ix_americano_") and table_name.startswith("americano_")
        table = self.metadata.tables[table_name]
        self.indexes_created.append((name, table_name))
        return sa.Index(name, *(table.c[column] for column in columns))

    def create_foreign_key(self, name, source, target, local, remote):
        assert source in self.created and target in self.created
        assert source.startswith("americano_") and target.startswith("americano_")
        self.alters.append(("add", name, source))
        self.metadata.tables[source].append_constraint(sa.ForeignKeyConstraint(
            local, [f"{target}.{column}" for column in remote], name=name, use_alter=True,
        ))

    def drop_constraint(self, name, table_name, *, type_):
        assert name == "fk_americano_events_champion"
        assert table_name == "americano_events" and type_ == "foreignkey"
        self.alters.append(("drop", name, table_name))

    def drop_index(self, name, *, table_name):
        assert name.startswith("ix_americano_") and table_name.startswith("americano_")
        self.indexes_dropped.append((name, table_name))

    def drop_table(self, name):
        assert name.startswith("americano_")
        self.dropped.append(name)


def _revision():
    spec = importlib.util.spec_from_file_location("americano_migration_plan", REVISION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _signature(table):
    dialect = postgresql.dialect()
    columns = {column.name: (column.type.compile(dialect=dialect), column.nullable, column.primary_key)
               for column in table.columns}
    constraints = set()
    for constraint in table.constraints:
        if isinstance(constraint, sa.CheckConstraint):
            sql = str(constraint.sqltext.compile(dialect=dialect, compile_kwargs={"literal_binds": True}))
            constraints.add(("check", constraint.name, sql))
        elif isinstance(constraint, sa.UniqueConstraint):
            constraints.add(("unique", constraint.name, tuple(column.name for column in constraint.columns)))
        elif isinstance(constraint, sa.ForeignKeyConstraint):
            constraints.add(("fk", constraint.name, tuple(column.name for column in constraint.columns),
                             tuple(element.target_fullname for element in constraint.elements)))
    indexes = {(index.name, tuple(column.name for column in index.columns), index.unique) for index in table.indexes}
    return columns, constraints, indexes


def test_additive_revision_mock_plan_matches_all_eight_models_and_inverse():
    # This is preparation only: op is replaced BEFORE calling the plan functions.
    # No migration environment, connection, Alembic context or actual DDL exists.
    from app.americanos import models  # noqa: F401
    from sqlmodel import SQLModel

    module = _revision()
    recorder = _PlanRecorder()
    module.op = recorder
    module.upgrade()
    expected = {name: table for name, table in SQLModel.metadata.tables.items() if name.startswith("americano_")}
    assert len(recorder.created) == len(expected) == 8
    assert set(recorder.created) == set(expected)
    dialect = postgresql.dialect()
    for name, table in recorder.metadata.tables.items():
        assert _signature(table) == _signature(expected[name]), name
        assert str(CreateTable(table).compile(dialect=dialect)).startswith("\nCREATE TABLE americano_")
        assert all(fk.target_fullname.startswith("americano_") for fk in table.foreign_keys)
        for index in table.indexes:
            assert " ON americano_" in str(CreateIndex(index).compile(dialect=dialect))
    champion = next(fk for fk in recorder.metadata.tables["americano_events"].foreign_key_constraints
                    if fk.name == "fk_americano_events_champion")
    assert "ALTER TABLE americano_events ADD CONSTRAINT" in str(AddConstraint(champion).compile(dialect=dialect))
    assert "id SERIAL" in str(CreateTable(recorder.metadata.tables["americano_events"]).compile(dialect=dialect))
    module.downgrade()
    assert recorder.dropped == list(reversed(recorder.created))
    assert set(recorder.indexes_created) == set(recorder.indexes_dropped)
    assert recorder.alters == [
        ("add", "fk_americano_events_champion", "americano_events"),
        ("drop", "fk_americano_events_champion", "americano_events"),
    ]


def test_revision_has_single_current_parent_and_env_import_is_explicit():
    revisions = {}
    parents = set()
    for path in REVISION.parent.glob("*.py"):
        assignments = {}
        for node in ast.parse(path.read_text(encoding="utf-8-sig")).body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                assignments[node.target.id] = ast.literal_eval(node.value)
        revisions[assignments["revision"]] = assignments["down_revision"]
        if assignments["down_revision"]:
            parents.add(assignments["down_revision"])
    assert revisions["f1a62d9c4b83"] == "e8a3c015f9b2"
    assert set(revisions) - parents == {"f1a62d9c4b83"}
    tree = ast.parse((BACKEND / "migrations/env.py").read_text(encoding="utf-8-sig"))
    assert any(isinstance(node, ast.ImportFrom) and node.module == "app.americanos"
               and any(alias.name == "models" for alias in node.names) for node in tree.body)
