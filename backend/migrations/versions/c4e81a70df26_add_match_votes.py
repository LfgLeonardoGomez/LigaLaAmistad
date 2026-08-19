"""add match votes

Revision ID: c4e81a70df26
Revises: 9f2ad4c81b67
Create Date: 2026-08-19 12:10:00.000000

Written by hand, like the rest: autogenerate would also emit a diff for the
Postgres-only pieces of the initial schema.

The unique constraint on (match_id, voter_key) is the whole anti-stuffing
mechanism. Without it a device could vote as many times as it liked, and the
service could no longer treat a second vote as moving the first one.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # SQLModel columns render as sqlmodel.sql.sqltypes.AutoString


# revision identifiers, used by Alembic.
revision: str = 'c4e81a70df26'
down_revision: Union[str, Sequence[str], None] = '9f2ad4c81b67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'match_votes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('voter_key', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('match_id', 'voter_key', name='uq_match_votes_match_voter'),
    )
    op.create_index(op.f('ix_match_votes_match_id'), 'match_votes', ['match_id'])
    op.create_index(op.f('ix_match_votes_voter_key'), 'match_votes', ['voter_key'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_match_votes_voter_key'), table_name='match_votes')
    op.drop_index(op.f('ix_match_votes_match_id'), table_name='match_votes')
    op.drop_table('match_votes')
