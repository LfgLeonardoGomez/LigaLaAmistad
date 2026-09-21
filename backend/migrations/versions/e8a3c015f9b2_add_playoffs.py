"""add playoffs

Revision ID: e8a3c015f9b2
Revises: d5f92b1c0a47
Create Date: 2026-09-21 12:00:00.000000

Written by hand, like the rest: autogenerate would also emit a diff for the
Postgres-only pieces of the existing schema.

Two tables. `playoff_seeds` is the one-time snapshot of each zone's
group-stage standing the bracket is drawn from. `playoff_matches` is the
bracket itself: 19 fixed nodes wired to each other, each one backed by an
ordinary `matches` row only once both of its sides are known. Nothing about
sets, results or scoring is duplicated here — that is the whole point of
reusing `matches` instead of giving playoffs their own copy of that logic.

The enum types are declared up front and dropped explicitly in `downgrade`.
`create_table` emits their `CREATE TYPE` on its own, the same as it already
does for `team_status`/`match_status` in the initial schema, but neither of
those is ever dropped on the way back down — this migration's `downgrade`
does drop its own, so rolling it back does not leave two orphaned enum types
behind in Postgres.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8a3c015f9b2'
down_revision: Union[str, Sequence[str], None] = 'd5f92b1c0a47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

playoff_round = sa.Enum(
    'round_1', 'round_2', 'quarterfinal', 'semifinal', 'final',
    name='playoff_round',
)
playoff_match_status = sa.Enum(
    'pending', 'bye',
    name='playoff_match_status',
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'playoff_seeds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('zone_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('zone_id', 'position', name='uq_playoff_seeds_zone_position'),
        sa.UniqueConstraint('team_id', name='uq_playoff_seeds_team'),
    )
    op.create_index(op.f('ix_playoff_seeds_zone_id'), 'playoff_seeds', ['zone_id'])
    op.create_index(op.f('ix_playoff_seeds_team_id'), 'playoff_seeds', ['team_id'])

    op.create_table(
        'playoff_matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('round', playoff_round, nullable=False),
        sa.Column('slot', sa.Integer(), nullable=False),
        sa.Column('team_a_id', sa.Integer(), nullable=True),
        sa.Column('team_b_id', sa.Integer(), nullable=True),
        sa.Column('match_id', sa.Integer(), nullable=True),
        sa.Column('next_match_id', sa.Integer(), nullable=True),
        sa.Column('next_side', sa.String(length=1), nullable=True),
        sa.Column('status', playoff_match_status, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['team_a_id'], ['teams.id'], ),
        sa.ForeignKeyConstraint(['team_b_id'], ['teams.id'], ),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
        sa.ForeignKeyConstraint(['next_match_id'], ['playoff_matches.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('round', 'slot', name='uq_playoff_matches_round_slot'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('playoff_matches')
    op.drop_index(op.f('ix_playoff_seeds_team_id'), table_name='playoff_seeds')
    op.drop_index(op.f('ix_playoff_seeds_zone_id'), table_name='playoff_seeds')
    op.drop_table('playoff_seeds')
    playoff_match_status.drop(op.get_bind(), checkfirst=True)
    playoff_round.drop(op.get_bind(), checkfirst=True)
