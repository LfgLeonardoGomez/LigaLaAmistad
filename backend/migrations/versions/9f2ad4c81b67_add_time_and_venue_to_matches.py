"""add time and venue to matches

Revision ID: 9f2ad4c81b67
Revises: 3b7e1c4a92d5
Create Date: 2026-08-18 10:00:00.000000

Written by hand, like the previous one. Autogenerate compares the models
against whichever database it is pointed at, and running it on the SQLite test
database would also emit a diff for the Postgres-only pieces of the schema (the
native enums, the timezone-aware timestamps).

Both columns are nullable and there is no backfill: the matches already loaded
have neither a time nor a venue agreed, and that is a valid state.

The enum type is created explicitly instead of being left to `add_column`.
`create_table` emits the `CREATE TYPE` on its own, `add_column` does not, so
without this line the upgrade would fail on Postgres with "type match_venue
does not exist". On SQLite `create()` is a no-op, since there the enum is a
VARCHAR with a check constraint.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f2ad4c81b67'
down_revision: Union[str, Sequence[str], None] = '3b7e1c4a92d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The values, not the member names: the API and the front end speak these.
match_venue = sa.Enum(
    'boss_padel',
    'cofam',
    'arena',
    'indoor',
    'padelon',
    'punto_de_oro',
    'otro',
    name='match_venue',
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    match_venue.create(bind, checkfirst=True)
    op.add_column('matches', sa.Column('time', sa.Time(), nullable=True))
    op.add_column('matches', sa.Column('venue', match_venue, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('matches', 'venue')
    op.drop_column('matches', 'time')
    match_venue.drop(op.get_bind(), checkfirst=True)
