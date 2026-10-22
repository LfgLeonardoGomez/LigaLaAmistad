"""Model constraints on private SQLite only; run with pytest --noconftest.

No application, settings, session engine or shared fixtures are imported. Every
test owns an in-memory connection with foreign keys enabled and creates only
the eight Americano tables (never the application's full metadata).
"""

import datetime
import sys

import pytest
from sqlalchemy import MetaData, event, inspect, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import AddConstraint, CreateTable
from sqlmodel import Session, SQLModel, create_engine

from app.americanos.models import (
    AmericanoEvent,
    AmericanoGroupMatch,
    AmericanoKnockoutMatch,
    AmericanoQualifierSnapshot,
    AmericanoRegistration,
    AmericanoRound,
    AmericanoTieResolution,
    AmericanoZone,
)


MODELS = (
    AmericanoEvent, AmericanoZone, AmericanoRegistration, AmericanoRound,
    AmericanoGroupMatch, AmericanoTieResolution, AmericanoQualifierSnapshot,
    AmericanoKnockoutMatch,
)
TABLES = [model.__table__ for model in MODELS]


@pytest.fixture
def connection():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA database_list").one()[2] == ""
        SQLModel.metadata.create_all(connection, tables=TABLES)
        connection.commit()
        yield connection
        connection.rollback()
    # Closing the sole connection disposes of the entire private database.
    engine.dispose()


def insert(connection, model, **values):
    connection.execute(model.__table__.insert().values(**values))


@pytest.fixture
def graph(connection):
    for event_id in (1, 2):
        insert(connection, AmericanoEvent, id=event_id, name="Evening", zone_count=2,
               start_stage="semifinal")
        for offset, label in ((1, "A"), (2, "B")):
            insert(connection, AmericanoZone, id=event_id * 10 + offset,
                   event_id=event_id, label=label)
        for order in (1, 2, 3, 4):
            insert(connection, AmericanoRegistration, id=event_id * 100 + order,
                   event_id=event_id, zone_id=event_id * 10 + 1,
                   player1_name="Ana", player2_name="Sol", registration_order=order)
        insert(connection, AmericanoRound, id=event_id * 1000 + 1,
               event_id=event_id, number=1)
        insert(connection, AmericanoRound, id=event_id * 1000 + 2,
               event_id=event_id, number=2)
        insert(connection, AmericanoKnockoutMatch, id=event_id * 10000 + 1,
               event_id=event_id, stage="final", slot=1)
    connection.commit()
    return connection


def values_for(model):
    return {
        AmericanoEvent: dict(id=3, name="Morning", zone_count=1, start_stage="final"),
        AmericanoZone: dict(id=13, event_id=1, label="B"),
        AmericanoRegistration: dict(id=105, event_id=1, zone_id=11,
                                   player1_name="Luz", player2_name="Mar", registration_order=5),
        AmericanoRound: dict(id=1003, event_id=1, number=3),
        AmericanoGroupMatch: dict(id=1, event_id=1, round_id=1001, zone_id=11,
                                 registration_a_id=101, registration_b_id=102, display_order=1),
        AmericanoTieResolution: dict(id=1, event_id=1, zone_id=11, position=1,
                                    registration_id=101, source_groups_revision=0),
        AmericanoQualifierSnapshot: dict(id=1, event_id=1, zone_id=11, position=1,
                                        registration_id=101, player1_name="Ana", player2_name="Sol",
                                        points_half_units=3, games_diff=-2, source_groups_revision=0),
        AmericanoKnockoutMatch: dict(id=10002, event_id=1, stage="semifinal", slot=1,
                                   next_match_id=10001, next_side="a"),
    }[model]


def reject(connection, model, **changes):
    values = values_for(model) | changes
    with pytest.raises(IntegrityError, match="CHECK"), connection.begin_nested():
        insert(connection, model, **values)


def test_only_eight_isolated_tables_and_no_league_foreign_keys(connection):
    assert set(inspect(connection).get_table_names()) == {
        "americano_events", "americano_zones", "americano_registrations", "americano_rounds",
        "americano_group_matches", "americano_tie_resolutions", "americano_qualifier_snapshots",
        "americano_knockout_matches",
    }
    for table in TABLES:
        assert all(fk.column.table.name.startswith("americano_") for fk in table.foreign_keys)
    assert not {"app.main", "app.core.config", "app.database.session"}.intersection(sys.modules)


@pytest.mark.parametrize("zone_count,stage", [(1, "quarterfinal"), (2, "semifinal"), (1, "final")])
def test_event_defaults_round_trip_with_timestamps(connection, zone_count, stage):
    with Session(bind=connection) as session:
        row = AmericanoEvent(name="Evening", zone_count=zone_count, start_stage=stage)
        session.add(row)
        session.flush()
        session.refresh(row)
        assert (row.state, row.revision, row.groups_revision) == ("draft", 1, 0)
        assert (row.zone_count, row.start_stage) == (zone_count, stage)
        assert row.confirmed_at is None and row.champion_registration_id is None
        assert isinstance(row.created_at, datetime.datetime)
        assert isinstance(row.updated_at, datetime.datetime)


@pytest.mark.parametrize("changes", [
    {"state": "unknown"}, {"state": "DRAFT"}, {"start_stage": "quarters"},
    {"start_stage": "semis"}, {"zone_count": 0}, {"zone_count": 3},
    {"revision": 0}, {"revision": -1}, {"groups_revision": -1},
    {"confirmed_source_revision": -1}, {"name": ""}, {"name": "   "},
])
def test_invalid_event_fields_are_database_errors(graph, changes):
    reject(graph, AmericanoEvent, **changes)


@pytest.mark.parametrize("state", ["draft", "groups", "review", "playoffs", "completed"])
def test_all_canonical_states_persist(graph, state):
    insert(graph, AmericanoEvent, **(values_for(AmericanoEvent) | {"state": state}))
    assert graph.execute(select(AmericanoEvent.state).where(AmericanoEvent.id == 3)).scalar_one() == state


@pytest.mark.parametrize("missing", [False, True], ids=["cross-event", "missing"])
@pytest.mark.parametrize("model,field,foreign_id", [
    (AmericanoRegistration, "zone_id", 21),
    (AmericanoGroupMatch, "round_id", 2001),
    (AmericanoGroupMatch, "zone_id", 21),
    (AmericanoGroupMatch, "registration_a_id", 201),
    (AmericanoGroupMatch, "registration_b_id", 202),
    (AmericanoTieResolution, "zone_id", 21),
    (AmericanoTieResolution, "registration_id", 201),
    (AmericanoQualifierSnapshot, "zone_id", 21),
    (AmericanoQualifierSnapshot, "registration_id", 201),
    (AmericanoKnockoutMatch, "registration_a_id", 201),
    (AmericanoKnockoutMatch, "registration_b_id", 202),
    (AmericanoKnockoutMatch, "winner_registration_id", 201),
    (AmericanoKnockoutMatch, "next_match_id", 20001),
])
def test_composite_references_reject_cross_event_insert(graph, model, field, foreign_id, missing):
    # Keep other CHECK/UNIQUE constraints valid, so rejection proves the FK.
    values = values_for(model)
    if model is AmericanoGroupMatch and field == "registration_a_id":
        values.update(registration_b_id=202)
    if model is AmericanoKnockoutMatch and field == "winner_registration_id":
        values.update(registration_a_id=201, registration_b_id=202,
                      games_a=10, games_b=8, set_complete=True)
    if missing:
        foreign_id = 99999
        if model is AmericanoGroupMatch and field == "registration_a_id":
            values.update(registration_b_id=100000)
        if model is AmericanoKnockoutMatch and field == "winner_registration_id":
            values.update(registration_a_id=foreign_id)
    with pytest.raises(IntegrityError, match="FOREIGN KEY"), graph.begin_nested():
        insert(graph, model, **(values | {field: foreign_id}))


@pytest.mark.parametrize("registration_id", [201, 202, 999])
def test_champion_cannot_reference_other_event_or_missing_registration(graph, registration_id):
    with pytest.raises(IntegrityError, match="FOREIGN KEY"), graph.begin_nested():
        graph.execute(AmericanoEvent.__table__.update().where(AmericanoEvent.id == 1)
                      .values(champion_registration_id=registration_id))


@pytest.mark.parametrize("games_a,games_b", [(None, None), (0, 0), (0, 9), (9, 0), (9, 9)])
def test_group_scores_preserve_pending_and_complete_zero(graph, games_a, games_b):
    insert(graph, AmericanoGroupMatch,
           **(values_for(AmericanoGroupMatch) | {"games_a": games_a, "games_b": games_b}))
    assert graph.execute(select(AmericanoGroupMatch.games_a, AmericanoGroupMatch.games_b)).one() == (
        games_a, games_b)


@pytest.mark.parametrize("games_a,games_b", [
    (None, 0), (0, None), (-1, 0), (0, -1), (10, 0), (0, 10), (1.5, 0), (0, 2.5),
])
def test_invalid_group_scores_fail_at_insert(graph, games_a, games_b):
    reject(graph, AmericanoGroupMatch, games_a=games_a, games_b=games_b)


@pytest.mark.parametrize("a,b", [(101, 101), (102, 101)])
def test_group_pair_must_be_distinct_and_canonical(graph, a, b):
    reject(graph, AmericanoGroupMatch, registration_a_id=a, registration_b_id=b)


@pytest.mark.parametrize("model,changes", [
    (AmericanoZone, {"label": "C"}), (AmericanoZone, {"label": "a"}),
    (AmericanoRegistration, {"registration_order": 0}),
    (AmericanoRegistration, {"registration_order": -1}),
    (AmericanoRegistration, {"player1_name": ""}),
    (AmericanoRegistration, {"player2_name": "   "}),
    (AmericanoRound, {"number": 0}), (AmericanoRound, {"number": -1}),
    (AmericanoGroupMatch, {"display_order": 0}), (AmericanoGroupMatch, {"display_order": -1}),
    (AmericanoTieResolution, {"position": 0}), (AmericanoTieResolution, {"source_groups_revision": -1}),
    (AmericanoQualifierSnapshot, {"position": 0}),
    (AmericanoQualifierSnapshot, {"source_groups_revision": -1}),
    (AmericanoQualifierSnapshot, {"points_half_units": -1}),
    (AmericanoQualifierSnapshot, {"points_half_units": 1.5}),
    (AmericanoQualifierSnapshot, {"player1_name": ""}),
    (AmericanoQualifierSnapshot, {"player2_name": "   "}),
    (AmericanoKnockoutMatch, {"slot": 0}), (AmericanoKnockoutMatch, {"slot": -1}),
    (AmericanoKnockoutMatch, {"stage": "semis"}),
    (AmericanoKnockoutMatch, {"next_side": "c"}),
])
def test_child_checks_are_enforced(graph, model, changes):
    reject(graph, model, **changes)


@pytest.mark.parametrize("model,first,duplicate", [
    (AmericanoZone, {"id": 13, "label": "A"}, {}),
    (AmericanoRegistration, {}, {"id": 106}),
    (AmericanoRound, {}, {"id": 1004}),
    (AmericanoGroupMatch, {}, {"id": 2, "round_id": 1002}),
    (AmericanoGroupMatch, {}, {"id": 2, "registration_b_id": 103}),
    (AmericanoTieResolution, {}, {"id": 2, "registration_id": 102}),
    (AmericanoTieResolution, {}, {"id": 2, "position": 2}),
    (AmericanoQualifierSnapshot, {}, {"id": 2, "registration_id": 102}),
    (AmericanoQualifierSnapshot, {}, {"id": 2, "position": 2}),
    (AmericanoKnockoutMatch, {}, {"id": 10003, "next_side": "b"}),
])
def test_scoped_uniqueness_is_enforced(graph, model, first, duplicate):
    values = values_for(model) | first
    # The seeded graph already owns both labels; test its existing A directly.
    if model is not AmericanoZone:
        insert(graph, model, **values)
    with pytest.raises(IntegrityError, match="UNIQUE"), graph.begin_nested():
        insert(graph, model, **(values | duplicate))


@pytest.mark.parametrize("changes", [
    {"next_match_id": None}, {"next_side": None},
    {"stage": "final"}, {"next_match_id": 10002},
    {"registration_a_id": 101, "registration_b_id": 101},
    {"games_a": 6}, {"games_b": 4}, {"games_a": 6, "games_b": 4},
    {"set_complete": True},
    {"registration_a_id": 101, "registration_b_id": 102, "games_a": 6,
     "games_b": 6, "set_complete": True, "winner_registration_id": 101},
    {"registration_a_id": 101, "registration_b_id": 102, "games_a": -1,
     "games_b": 6, "set_complete": True, "winner_registration_id": 102},
    {"registration_a_id": 101, "registration_b_id": 102, "games_a": 10,
     "games_b": 8, "set_complete": True, "winner_registration_id": 103},
    {"registration_a_id": 101, "registration_b_id": 102, "games_a": 10,
     "games_b": 8, "set_complete": True, "winner_registration_id": 102},
    {"winner_registration_id": 101},
])
def test_knockout_shape_requires_consistent_result_and_destination(graph, changes):
    reject(graph, AmericanoKnockoutMatch, **changes)


@pytest.mark.parametrize("a,b,winner", [(10, 8, 101), (8, 10, 102)])
def test_knockout_stores_unbounded_games_without_choosing_set_convention(graph, a, b, winner):
    insert(graph, AmericanoKnockoutMatch,
           **(values_for(AmericanoKnockoutMatch) | dict(registration_a_id=101,
               registration_b_id=102, games_a=a, games_b=b, set_complete=True,
               winner_registration_id=winner)))
    assert graph.execute(select(AmericanoKnockoutMatch.winner_registration_id)
                         .where(AmericanoKnockoutMatch.id == 10002)).scalar_one() == winner


@pytest.mark.parametrize("registration_id", [101, 102])
def test_champion_accepts_own_registration_and_prevents_its_deletion(graph, registration_id):
    graph.execute(AmericanoEvent.__table__.update().where(AmericanoEvent.id == 1)
                  .values(champion_registration_id=registration_id))
    assert graph.execute(select(AmericanoEvent.champion_registration_id)
                         .where(AmericanoEvent.id == 1)).scalar_one() == registration_id
    with pytest.raises(IntegrityError, match="FOREIGN KEY"), graph.begin_nested():
        graph.execute(AmericanoRegistration.__table__.delete()
                      .where(AmericanoRegistration.id == registration_id))


@pytest.mark.parametrize("event_id", [1, 2])
def test_same_names_and_orders_are_valid_across_events_with_nullable_draft_zone(graph, event_id):
    insert(graph, AmericanoRegistration, event_id=event_id, zone_id=None,
           player1_name="Ana", player2_name="Sol", registration_order=5)
    assert graph.execute(select(AmericanoRegistration.zone_id)
                         .where(AmericanoRegistration.event_id == event_id,
                                AmericanoRegistration.registration_order == 5)).scalar_one() is None
    assert len(graph.execute(select(AmericanoRegistration.id)
                             .where(AmericanoRegistration.player1_name == "Ana")).all()) == 9


@pytest.mark.parametrize("points,diff,revision", [(0, 0, 0), (1, -9, 2), (9, 12, 3)])
def test_snapshot_preserves_exact_half_units_names_and_signed_difference(graph, points, diff, revision):
    values = values_for(AmericanoQualifierSnapshot) | dict(
        points_half_units=points, games_diff=diff, source_groups_revision=revision)
    insert(graph, AmericanoQualifierSnapshot, **values)
    assert graph.execute(select(AmericanoQualifierSnapshot.points_half_units,
                                AmericanoQualifierSnapshot.games_diff,
                                AmericanoQualifierSnapshot.source_groups_revision,
                                AmericanoQualifierSnapshot.player1_name,
                                AmericanoQualifierSnapshot.player2_name)).one() == (
        points, diff, revision, "Ana", "Sol")


@pytest.mark.parametrize("model", [AmericanoTieResolution, AmericanoQualifierSnapshot])
def test_seeds_can_repeat_in_other_event_but_not_duplicate_own_pairs(graph, model):
    insert(graph, model, **values_for(model))
    insert(graph, model, **(values_for(model) | dict(id=2, event_id=2, zone_id=21, registration_id=201)))
    assert graph.execute(select(model.event_id, model.position).order_by(model.event_id)).all() == [
        (1, 1), (2, 1)]


@pytest.mark.parametrize("label", ["A", "B"])
def test_zone_label_and_round_number_repeat_across_events(graph, label):
    assert graph.execute(select(AmericanoZone.event_id)
                         .where(AmericanoZone.label == label).order_by(AmericanoZone.event_id)).all() == [
        (1,), (2,)]
    assert graph.execute(select(AmericanoRound.event_id)
                         .where(AmericanoRound.number == 1).order_by(AmericanoRound.event_id)).all() == [
        (1,), (2,)]


@pytest.mark.parametrize("field", ["round_id", "zone_id", "registration_b_id"])
def test_cross_event_updates_are_rejected_without_changing_saved_match(graph, field):
    insert(graph, AmericanoGroupMatch, **values_for(AmericanoGroupMatch))
    foreign_id = {"round_id": 2001, "zone_id": 21, "registration_b_id": 202}[field]
    with pytest.raises(IntegrityError, match="FOREIGN KEY"), graph.begin_nested():
        graph.execute(AmericanoGroupMatch.__table__.update().values(**{field: foreign_id}))
    assert graph.execute(select(AmericanoGroupMatch.round_id, AmericanoGroupMatch.zone_id,
                                AmericanoGroupMatch.registration_b_id)).one() == (1001, 11, 102)


@pytest.mark.parametrize("side", ["a", "b"])
def test_destination_side_has_one_feeder_and_other_side_remains_available(graph, side):
    insert(graph, AmericanoKnockoutMatch, **(values_for(AmericanoKnockoutMatch) | {"next_side": side}))
    second = values_for(AmericanoKnockoutMatch) | dict(id=10003, slot=2, next_side=side)
    with pytest.raises(IntegrityError, match="UNIQUE"), graph.begin_nested():
        insert(graph, AmericanoKnockoutMatch, **second)
    insert(graph, AmericanoKnockoutMatch, **(second | {"next_side": "b" if side == "a" else "a"}))
    assert graph.execute(select(AmericanoKnockoutMatch.next_side)
                         .where(AmericanoKnockoutMatch.stage == "semifinal")
                         .order_by(AmericanoKnockoutMatch.next_side)).all() == [("a",), ("b",)]


@pytest.mark.parametrize("participants", [{}, {"registration_a_id": 101},
                                         {"registration_a_id": 102, "registration_b_id": 101}])
def test_pending_knockout_allows_unknown_or_seed_ordered_participants(graph, participants):
    insert(graph, AmericanoKnockoutMatch, **(values_for(AmericanoKnockoutMatch) | participants))
    assert graph.execute(select(AmericanoKnockoutMatch.games_a, AmericanoKnockoutMatch.games_b,
                                AmericanoKnockoutMatch.set_complete)
                         .where(AmericanoKnockoutMatch.id == 10002)).one() == (None, None, False)


@pytest.mark.parametrize("model", MODELS[1:])
def test_every_child_rejects_missing_event(graph, model):
    values = values_for(model) | {"event_id": 999}
    if model is AmericanoZone:
        values["label"] = "A"
    with pytest.raises(IntegrityError, match="FOREIGN KEY"), graph.begin_nested():
        insert(graph, model, **values)


def test_postgresql_compilation_keeps_generated_event_id_text_enums_and_named_cycle():
    # Compilation only: no PostgreSQL engine, connection or DDL execution.
    dialect = postgresql.dialect()
    event_ddl = str(CreateTable(AmericanoEvent.__table__).compile(dialect=dialect))
    assert "SERIAL" in event_ddl
    assert "VARCHAR" in event_ddl
    assert "'quarterfinal', 'semifinal', 'final'" in event_ddl
    # AddConstraint installs a DDL rule on its constraint; compile a private copy.
    metadata = MetaData()
    for table in TABLES:
        table.to_metadata(metadata)
    champion_fk = next(fk for fk in metadata.tables["americano_events"].foreign_key_constraints
                       if fk.name == "fk_americano_events_champion")
    assert "FOREIGN KEY(id, champion_registration_id)" in str(
        AddConstraint(champion_fk).compile(dialect=dialect))
    for table in TABLES:
        assert "CREATE TABLE americano_" in str(CreateTable(table).compile(dialect=dialect))
