"""Add selected courts and per-match assignments without regenerating fixtures.

Revision ID: a2c37e91d046
Revises: f1a62d9c4b83
"""

from alembic import op
import sqlalchemy as sa

revision: str = "a2c37e91d046"
down_revision: str = "f1a62d9c4b83"
branch_labels = None
depends_on = None


def upgrade():
    # Existing events keep their six-court capacity and original rounds/results.
    op.add_column("americano_events", sa.Column("court_mask", sa.Integer(), nullable=False, server_default="63"))
    op.add_column("americano_group_matches", sa.Column("court_number", sa.Integer(), nullable=True))
    op.add_column("americano_knockout_matches", sa.Column("court_number", sa.Integer(), nullable=True))
    op.execute("UPDATE americano_group_matches SET court_number = display_order")
    op.execute("UPDATE americano_knockout_matches SET court_number = ((slot - 1) % 6) + 1")
    with op.batch_alter_table("americano_events") as batch:
        batch.create_check_constraint("ck_americano_events_courts", "court_mask BETWEEN 1 AND 63")
    with op.batch_alter_table("americano_group_matches") as batch:
        batch.create_check_constraint("ck_americano_group_matches_court", "court_number BETWEEN 1 AND 6")
        batch.create_unique_constraint("uq_americano_group_matches_court", ["round_id", "court_number"])
    with op.batch_alter_table("americano_knockout_matches") as batch:
        batch.create_check_constraint("ck_americano_knockout_matches_court", "court_number BETWEEN 1 AND 6")


def downgrade():
    with op.batch_alter_table("americano_knockout_matches") as batch:
        batch.drop_constraint("ck_americano_knockout_matches_court", type_="check")
        batch.drop_column("court_number")
    with op.batch_alter_table("americano_group_matches") as batch:
        batch.drop_constraint("uq_americano_group_matches_court", type_="unique")
        batch.drop_constraint("ck_americano_group_matches_court", type_="check")
        batch.drop_column("court_number")
    with op.batch_alter_table("americano_events") as batch:
        batch.drop_constraint("ck_americano_events_courts", type_="check")
        batch.drop_column("court_mask")
