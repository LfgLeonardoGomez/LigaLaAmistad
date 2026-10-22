"""Isolated Americano persistence; no league entities or application imports.

Foreign keys enforce event ownership. Zone membership, one appearance per round,
state transitions, snapshot immutability and the pending sports rules belong to
the transactional service, not ORM cascades or implicit relationship writes.
"""

import datetime
import enum

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKeyConstraint, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.core.models import TimestampMixin


class AmericanoEventState(str, enum.Enum):
    DRAFT = "draft"
    GROUPS = "groups"
    REVIEW = "review"
    PLAYOFFS = "playoffs"
    COMPLETED = "completed"


class AmericanoStage(str, enum.Enum):
    QUARTERFINAL = "quarterfinal"
    SEMIFINAL = "semifinal"
    FINAL = "final"


class AmericanoZoneLabel(str, enum.Enum):
    A = "A"
    B = "B"


class AmericanoSide(str, enum.Enum):
    A = "a"
    B = "b"


def _enum_column(
    members: type[enum.Enum],
    name: str,
    *,
    nullable: bool = False,
    default: enum.Enum | None = None,
) -> Column:
    """Persist G0 values in VARCHAR + named CHECK, never PostgreSQL enum types."""
    return Column(
        SAEnum(
            members,
            name=name,
            native_enum=False,
            create_constraint=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        nullable=nullable,
        default=default,
    )


def _event_fk(table: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["event_id"],
        ["americano_events.id"],
        name=f"fk_americano_{table}_event",
    )


def _scoped_fk(table: str, field: str, target: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["event_id", field],
        [f"americano_{target}.event_id", f"americano_{target}.id"],
        name=f"fk_americano_{table}_{field}",
    )


class AmericanoEvent(TimestampMixin, table=True):
    __tablename__ = "americano_events"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_americano_events_name"),
        CheckConstraint("zone_count IN (1, 2)", name="ck_americano_events_zone_count"),
        CheckConstraint("revision >= 1", name="ck_americano_events_revision"),
        CheckConstraint("groups_revision >= 0", name="ck_americano_events_groups_revision"),
        CheckConstraint(
            "confirmed_source_revision >= 0", name="ck_americano_events_confirmed_revision",
        ),
        # Break the events -> registrations -> events DDL cycle explicitly.
        # SQLite includes this inline; PostgreSQL emits a named ALTER constraint.
        ForeignKeyConstraint(
            ["id", "champion_registration_id"],
            ["americano_registrations.event_id", "americano_registrations.id"],
            name="fk_americano_events_champion",
            use_alter=True,
        ),
    )

    id: int | None = Field(
        default=None,
        primary_key=True,
        sa_column_kwargs={"autoincrement": "ignore_fk"},
    )
    name: str
    state: AmericanoEventState = Field(
        default=AmericanoEventState.DRAFT,
        sa_column=_enum_column(
            AmericanoEventState, "ck_americano_events_state", default=AmericanoEventState.DRAFT,
        ),
    )
    zone_count: int
    start_stage: AmericanoStage = Field(
        sa_column=_enum_column(AmericanoStage, "ck_americano_events_start_stage"),
    )
    revision: int = Field(default=1)
    groups_revision: int = Field(default=0)
    confirmed_at: datetime.datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    confirmation_key: str | None = Field(default=None, max_length=36)
    confirmed_source_revision: int | None = Field(default=None)
    champion_registration_id: int | None = Field(default=None)


class AmericanoZone(TimestampMixin, table=True):
    __tablename__ = "americano_zones"
    __table_args__ = (
        _event_fk("zones"),
        UniqueConstraint("event_id", "id", name="uq_americano_zones_event_id"),
        UniqueConstraint("event_id", "label", name="uq_americano_zones_label"),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_id: int
    label: AmericanoZoneLabel = Field(
        sa_column=_enum_column(AmericanoZoneLabel, "ck_americano_zones_label"),
    )


class AmericanoRegistration(TimestampMixin, table=True):
    __tablename__ = "americano_registrations"
    __table_args__ = (
        _event_fk("registrations"),
        _scoped_fk("registrations", "zone_id", "zones"),
        UniqueConstraint("event_id", "id", name="uq_americano_registrations_event_id"),
        UniqueConstraint(
            "event_id", "registration_order", name="uq_americano_registrations_order",
        ),
        CheckConstraint("registration_order >= 1", name="ck_americano_registrations_order"),
        CheckConstraint("length(trim(player1_name)) > 0", name="ck_americano_registrations_name1"),
        CheckConstraint("length(trim(player2_name)) > 0", name="ck_americano_registrations_name2"),
        Index("ix_americano_registrations_event_zone", "event_id", "zone_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_id: int
    zone_id: int | None = Field(default=None)
    player1_name: str
    player2_name: str
    registration_order: int


class AmericanoRound(TimestampMixin, table=True):
    __tablename__ = "americano_rounds"
    __table_args__ = (
        _event_fk("rounds"),
        UniqueConstraint("event_id", "id", name="uq_americano_rounds_event_id"),
        UniqueConstraint("event_id", "number", name="uq_americano_rounds_number"),
        CheckConstraint("number >= 1", name="ck_americano_rounds_number"),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_id: int
    number: int
    saved_at: datetime.datetime | None = Field(default=None, sa_type=DateTime(timezone=True))


class AmericanoGroupMatch(TimestampMixin, table=True):
    __tablename__ = "americano_group_matches"
    __table_args__ = (
        _event_fk("group_matches"),
        _scoped_fk("group_matches", "round_id", "rounds"),
        _scoped_fk("group_matches", "zone_id", "zones"),
        _scoped_fk("group_matches", "registration_a_id", "registrations"),
        _scoped_fk("group_matches", "registration_b_id", "registrations"),
        UniqueConstraint(
            "event_id", "registration_a_id", "registration_b_id",
            name="uq_americano_group_matches_pair",
        ),
        UniqueConstraint("round_id", "display_order", name="uq_americano_group_matches_order"),
        CheckConstraint(
            "registration_a_id < registration_b_id",
            name="ck_americano_group_matches_canonical_pair",
        ),
        CheckConstraint("display_order >= 1", name="ck_americano_group_matches_order"),
        CheckConstraint(
            "(games_a IS NULL AND games_b IS NULL) OR "
            "(games_a IS NOT NULL AND games_b IS NOT NULL "
            "AND games_a BETWEEN 0 AND 9 AND games_b BETWEEN 0 AND 9 "
            "AND games_a = CAST(games_a AS INTEGER) AND games_b = CAST(games_b AS INTEGER))",
            name="ck_americano_group_matches_scores",
        ),
        Index("ix_americano_group_matches_event_round", "event_id", "round_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_id: int
    round_id: int
    zone_id: int
    registration_a_id: int
    registration_b_id: int
    display_order: int
    games_a: int | None = Field(default=None)
    games_b: int | None = Field(default=None)


class AmericanoTieResolution(TimestampMixin, table=True):
    __tablename__ = "americano_tie_resolutions"
    __table_args__ = (
        _event_fk("tie_resolutions"),
        _scoped_fk("tie_resolutions", "zone_id", "zones"),
        _scoped_fk("tie_resolutions", "registration_id", "registrations"),
        UniqueConstraint(
            "event_id", "zone_id", "position", name="uq_americano_tie_resolutions_seed",
        ),
        UniqueConstraint(
            "event_id", "registration_id", name="uq_americano_tie_resolutions_pair",
        ),
        CheckConstraint("position >= 1", name="ck_americano_tie_resolutions_position"),
        CheckConstraint("source_groups_revision >= 0", name="ck_americano_tie_resolutions_revision"),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_id: int
    zone_id: int
    source_groups_revision: int
    position: int
    registration_id: int


class AmericanoQualifierSnapshot(TimestampMixin, table=True):
    __tablename__ = "americano_qualifier_snapshots"
    __table_args__ = (
        _event_fk("qualifier_snapshots"),
        _scoped_fk("qualifier_snapshots", "zone_id", "zones"),
        _scoped_fk("qualifier_snapshots", "registration_id", "registrations"),
        UniqueConstraint(
            "event_id", "zone_id", "position", name="uq_americano_qualifier_snapshots_seed",
        ),
        UniqueConstraint(
            "event_id", "registration_id", name="uq_americano_qualifier_snapshots_pair",
        ),
        CheckConstraint("position >= 1", name="ck_americano_qualifier_snapshots_position"),
        CheckConstraint(
            "source_groups_revision >= 0", name="ck_americano_qualifier_snapshots_revision",
        ),
        CheckConstraint(
            "points_half_units >= 0 AND points_half_units = CAST(points_half_units AS INTEGER)",
            name="ck_americano_qualifier_snapshots_points",
        ),
        CheckConstraint("length(trim(player1_name)) > 0", name="ck_americano_qualifier_snapshots_name1"),
        CheckConstraint("length(trim(player2_name)) > 0", name="ck_americano_qualifier_snapshots_name2"),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_id: int
    zone_id: int
    position: int
    registration_id: int
    player1_name: str
    player2_name: str
    points_half_units: int
    games_diff: int
    source_groups_revision: int


class AmericanoKnockoutMatch(TimestampMixin, table=True):
    __tablename__ = "americano_knockout_matches"
    __table_args__ = (
        _event_fk("knockout_matches"),
        _scoped_fk("knockout_matches", "registration_a_id", "registrations"),
        _scoped_fk("knockout_matches", "registration_b_id", "registrations"),
        _scoped_fk("knockout_matches", "winner_registration_id", "registrations"),
        _scoped_fk("knockout_matches", "next_match_id", "knockout_matches"),
        UniqueConstraint("event_id", "id", name="uq_americano_knockout_matches_event_id"),
        UniqueConstraint(
            "event_id", "stage", "slot", name="uq_americano_knockout_matches_slot",
        ),
        UniqueConstraint(
            "event_id", "next_match_id", "next_side",
            name="uq_americano_knockout_matches_destination",
        ),
        CheckConstraint("slot >= 1", name="ck_americano_knockout_matches_slot"),
        CheckConstraint(
            "registration_a_id != registration_b_id",
            name="ck_americano_knockout_matches_distinct_pair",
        ),
        CheckConstraint(
            "(stage = 'final' AND next_match_id IS NULL AND next_side IS NULL) OR "
            "(stage != 'final' AND next_match_id IS NOT NULL AND next_side IS NOT NULL "
            "AND next_match_id != id)",
            name="ck_americano_knockout_matches_destination",
        ),
        CheckConstraint(
            "(NOT set_complete AND games_a IS NULL AND games_b IS NULL "
            "AND winner_registration_id IS NULL) OR "
            "(set_complete AND registration_a_id IS NOT NULL AND registration_b_id IS NOT NULL "
            "AND games_a IS NOT NULL AND games_b IS NOT NULL AND winner_registration_id IS NOT NULL "
            "AND games_a >= 0 AND games_b >= 0 AND games_a != games_b "
            "AND games_a = CAST(games_a AS INTEGER) AND games_b = CAST(games_b AS INTEGER) "
            "AND ((games_a > games_b AND winner_registration_id = registration_a_id) OR "
            "(games_b > games_a AND winner_registration_id = registration_b_id)))",
            name="ck_americano_knockout_matches_result",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_id: int
    stage: AmericanoStage = Field(
        sa_column=_enum_column(AmericanoStage, "ck_americano_knockout_matches_stage"),
    )
    slot: int
    registration_a_id: int | None = Field(default=None)
    registration_b_id: int | None = Field(default=None)
    games_a: int | None = Field(default=None)
    games_b: int | None = Field(default=None)
    set_complete: bool = Field(default=False)
    next_match_id: int | None = Field(default=None)
    next_side: AmericanoSide | None = Field(
        default=None,
        sa_column=_enum_column(
            AmericanoSide, "ck_americano_knockout_matches_side", nullable=True,
        ),
    )
    winner_registration_id: int | None = Field(default=None)
