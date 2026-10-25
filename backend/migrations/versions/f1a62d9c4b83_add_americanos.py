"""Add the eight isolated Americano tables.

Revision ID: f1a62d9c4b83
Revises: e8a3c015f9b2

Handwritten additive plan: no league objects, data changes, runtime model imports
or PostgreSQL enum types. The event/champion cycle is added after registration
exists and removed before dropping tables. Defaults remain application-owned,
matching the existing metadata. Execution requires a separately authorized trial.
"""

from alembic import op
import sqlalchemy as sa


revision: str = "f1a62d9c4b83"
down_revision: str = "e8a3c015f9b2"
branch_labels = None
depends_on = None


def _base():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    ]


def _enum(name, *values):
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def _event_fk(table):
    return sa.ForeignKeyConstraint(
        ["event_id"], ["americano_events.id"], name=f"fk_americano_{table}_event",
    )


def _scoped_fk(table, field, target):
    return sa.ForeignKeyConstraint(
        ["event_id", field], [f"americano_{target}.event_id", f"americano_{target}.id"],
        name=f"fk_americano_{table}_{field}",
    )


def upgrade() -> None:
    op.create_table(
        "americano_events", *_base(),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("state", _enum("ck_americano_events_state", "draft", "groups", "review", "playoffs", "completed"), nullable=False),
        sa.Column("zone_count", sa.Integer(), nullable=False),
        sa.Column("start_stage", _enum("ck_americano_events_start_stage", "quarterfinal", "semifinal", "final"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("groups_revision", sa.Integer(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmation_key", sa.String(length=36), nullable=True),
        sa.Column("confirmed_source_revision", sa.Integer(), nullable=True),
        sa.Column("champion_registration_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_americano_events_name"),
        sa.CheckConstraint("zone_count IN (1, 2)", name="ck_americano_events_zone_count"),
        sa.CheckConstraint("revision >= 1", name="ck_americano_events_revision"),
        sa.CheckConstraint("groups_revision >= 0", name="ck_americano_events_groups_revision"),
        sa.CheckConstraint("confirmed_source_revision >= 0", name="ck_americano_events_confirmed_revision"),
    )
    op.create_table(
        "americano_zones", *_base(),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("label", _enum("ck_americano_zones_label", "A", "B"), nullable=False),
        _event_fk("zones"),
        sa.UniqueConstraint("event_id", "id", name="uq_americano_zones_event_id"),
        sa.UniqueConstraint("event_id", "label", name="uq_americano_zones_label"),
    )
    op.create_table(
        "americano_registrations", *_base(),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=True),
        sa.Column("player1_name", sa.String(), nullable=False),
        sa.Column("player2_name", sa.String(), nullable=False),
        sa.Column("registration_order", sa.Integer(), nullable=False),
        _event_fk("registrations"), _scoped_fk("registrations", "zone_id", "zones"),
        sa.UniqueConstraint("event_id", "id", name="uq_americano_registrations_event_id"),
        sa.UniqueConstraint("event_id", "registration_order", name="uq_americano_registrations_order"),
        sa.CheckConstraint("registration_order >= 1", name="ck_americano_registrations_order"),
        sa.CheckConstraint("length(trim(player1_name)) > 0", name="ck_americano_registrations_name1"),
        sa.CheckConstraint("length(trim(player2_name)) > 0", name="ck_americano_registrations_name2"),
    )
    op.create_index("ix_americano_registrations_event_zone", "americano_registrations", ["event_id", "zone_id"])
    op.create_foreign_key(
        "fk_americano_events_champion", "americano_events", "americano_registrations",
        ["id", "champion_registration_id"], ["event_id", "id"],
    )
    op.create_table(
        "americano_rounds", *_base(),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
        _event_fk("rounds"),
        sa.UniqueConstraint("event_id", "id", name="uq_americano_rounds_event_id"),
        sa.UniqueConstraint("event_id", "number", name="uq_americano_rounds_number"),
        sa.CheckConstraint("number >= 1", name="ck_americano_rounds_number"),
    )
    op.create_table(
        "americano_group_matches", *_base(),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("round_id", sa.Integer(), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.Column("registration_a_id", sa.Integer(), nullable=False),
        sa.Column("registration_b_id", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("games_a", sa.Integer(), nullable=True),
        sa.Column("games_b", sa.Integer(), nullable=True),
        _event_fk("group_matches"), _scoped_fk("group_matches", "round_id", "rounds"),
        _scoped_fk("group_matches", "zone_id", "zones"),
        _scoped_fk("group_matches", "registration_a_id", "registrations"),
        _scoped_fk("group_matches", "registration_b_id", "registrations"),
        sa.UniqueConstraint("event_id", "registration_a_id", "registration_b_id", name="uq_americano_group_matches_pair"),
        sa.UniqueConstraint("round_id", "display_order", name="uq_americano_group_matches_order"),
        sa.CheckConstraint("registration_a_id < registration_b_id", name="ck_americano_group_matches_canonical_pair"),
        sa.CheckConstraint("display_order >= 1", name="ck_americano_group_matches_order"),
        sa.CheckConstraint(
            "(games_a IS NULL AND games_b IS NULL) OR "
            "(games_a IS NOT NULL AND games_b IS NOT NULL "
            "AND games_a BETWEEN 0 AND 9 AND games_b BETWEEN 0 AND 9 "
            "AND games_a = CAST(games_a AS INTEGER) AND games_b = CAST(games_b AS INTEGER))",
            name="ck_americano_group_matches_scores",
        ),
    )
    op.create_index("ix_americano_group_matches_event_round", "americano_group_matches", ["event_id", "round_id"])
    for suffix in ("tie_resolutions", "qualifier_snapshots"):
        snapshot = suffix == "qualifier_snapshots"
        extra = [
            sa.Column("player1_name", sa.String(), nullable=False),
            sa.Column("player2_name", sa.String(), nullable=False),
            sa.Column("points_half_units", sa.Integer(), nullable=False),
            sa.Column("games_diff", sa.Integer(), nullable=False),
            sa.CheckConstraint("points_half_units >= 0 AND points_half_units = CAST(points_half_units AS INTEGER)", name="ck_americano_qualifier_snapshots_points"),
            sa.CheckConstraint("length(trim(player1_name)) > 0", name="ck_americano_qualifier_snapshots_name1"),
            sa.CheckConstraint("length(trim(player2_name)) > 0", name="ck_americano_qualifier_snapshots_name2"),
        ] if snapshot else []
        op.create_table(
            f"americano_{suffix}", *_base(),
            sa.Column("event_id", sa.Integer(), nullable=False),
            sa.Column("zone_id", sa.Integer(), nullable=False),
            sa.Column("source_groups_revision", sa.Integer(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("registration_id", sa.Integer(), nullable=False),
            *extra,
            _event_fk(suffix), _scoped_fk(suffix, "zone_id", "zones"),
            _scoped_fk(suffix, "registration_id", "registrations"),
            sa.UniqueConstraint("event_id", "zone_id", "position", name=f"uq_americano_{suffix}_seed"),
            sa.UniqueConstraint("event_id", "registration_id", name=f"uq_americano_{suffix}_pair"),
            sa.CheckConstraint("position >= 1", name=f"ck_americano_{suffix}_position"),
            sa.CheckConstraint("source_groups_revision >= 0", name=f"ck_americano_{suffix}_revision"),
        )
    op.create_table(
        "americano_knockout_matches", *_base(),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("stage", _enum("ck_americano_knockout_matches_stage", "quarterfinal", "semifinal", "final"), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("registration_a_id", sa.Integer(), nullable=True),
        sa.Column("registration_b_id", sa.Integer(), nullable=True),
        sa.Column("games_a", sa.Integer(), nullable=True),
        sa.Column("games_b", sa.Integer(), nullable=True),
        sa.Column("set_complete", sa.Boolean(), nullable=False),
        sa.Column("next_match_id", sa.Integer(), nullable=True),
        sa.Column("next_side", _enum("ck_americano_knockout_matches_side", "a", "b"), nullable=True),
        sa.Column("winner_registration_id", sa.Integer(), nullable=True),
        _event_fk("knockout_matches"),
        _scoped_fk("knockout_matches", "registration_a_id", "registrations"),
        _scoped_fk("knockout_matches", "registration_b_id", "registrations"),
        _scoped_fk("knockout_matches", "winner_registration_id", "registrations"),
        _scoped_fk("knockout_matches", "next_match_id", "knockout_matches"),
        sa.UniqueConstraint("event_id", "id", name="uq_americano_knockout_matches_event_id"),
        sa.UniqueConstraint("event_id", "stage", "slot", name="uq_americano_knockout_matches_slot"),
        sa.UniqueConstraint("event_id", "next_match_id", "next_side", name="uq_americano_knockout_matches_destination"),
        sa.CheckConstraint("slot >= 1", name="ck_americano_knockout_matches_slot"),
        sa.CheckConstraint("registration_a_id != registration_b_id", name="ck_americano_knockout_matches_distinct_pair"),
        sa.CheckConstraint(
            "(stage = 'final' AND next_match_id IS NULL AND next_side IS NULL) OR "
            "(stage != 'final' AND next_match_id IS NOT NULL AND next_side IS NOT NULL "
            "AND next_match_id != id)", name="ck_americano_knockout_matches_destination",
        ),
        sa.CheckConstraint(
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


def downgrade() -> None:
    op.drop_constraint("fk_americano_events_champion", "americano_events", type_="foreignkey")
    op.drop_table("americano_knockout_matches")
    op.drop_table("americano_qualifier_snapshots")
    op.drop_table("americano_tie_resolutions")
    op.drop_index("ix_americano_group_matches_event_round", table_name="americano_group_matches")
    op.drop_table("americano_group_matches")
    op.drop_table("americano_rounds")
    op.drop_index("ix_americano_registrations_event_zone", table_name="americano_registrations")
    op.drop_table("americano_registrations")
    op.drop_table("americano_zones")
    op.drop_table("americano_events")
