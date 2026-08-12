"""add event registration deadlines

Revision ID: 2d3e4f5a6b7c
Revises: 1c2d3e4f5a6b
"""
from alembic import op


revision = "2d3e4f5a6b7c"
down_revision = "1c2d3e4f5a6b"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE events
            ADD COLUMN IF NOT EXISTS registration_deadline TIMESTAMPTZ
    """)
    op.execute("""
        ALTER TABLE event_dates
            ADD COLUMN IF NOT EXISTS registration_deadline_override TIMESTAMPTZ
    """)


def downgrade():
    op.execute("ALTER TABLE event_dates DROP COLUMN IF EXISTS registration_deadline_override")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS registration_deadline")
