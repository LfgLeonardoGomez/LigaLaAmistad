"""add season predictions

Revision ID: d5f92b1c0a47
Revises: c4e81a70df26
Create Date: 2026-08-19 18:05:00.000000

Written by hand, like the rest.

Two tables rather than one: the window is what makes the poll a prediction
instead of an open-ended survey, and the results cannot be revealed until it
closes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # SQLModel columns render as sqlmodel.sql.sqltypes.AutoString


# revision identifiers, used by Alembic.
revision: str = 'd5f92b1c0a47'
down_revision: Union[str, Sequence[str], None] = 'c4e81a70df26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'prediction_windows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('opens_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closes_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('window_id', sa.Integer(), nullable=False),
        sa.Column('zone_id', sa.Integer(), nullable=False),
        sa.Column('voter_key', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('first_team_id', sa.Integer(), nullable=False),
        sa.Column('second_team_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['window_id'], ['prediction_windows.id'], ),
        sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ),
        sa.ForeignKeyConstraint(['first_team_id'], ['teams.id'], ),
        sa.ForeignKeyConstraint(['second_team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'window_id', 'zone_id', 'voter_key', name='uq_predictions_window_zone_voter'
        ),
    )
    op.create_index(op.f('ix_predictions_window_id'), 'predictions', ['window_id'])
    op.create_index(op.f('ix_predictions_zone_id'), 'predictions', ['zone_id'])
    op.create_index(op.f('ix_predictions_voter_key'), 'predictions', ['voter_key'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_predictions_voter_key'), table_name='predictions')
    op.drop_index(op.f('ix_predictions_zone_id'), table_name='predictions')
    op.drop_index(op.f('ix_predictions_window_id'), table_name='predictions')
    op.drop_table('predictions')
    op.drop_table('prediction_windows')
