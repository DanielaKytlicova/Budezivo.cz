"""add program booking opens at

Revision ID: 4f5a6b7c8d9e
Revises: 3e4f5a6b7c8d
"""
from alembic import op


revision = "4f5a6b7c8d9e"
down_revision = "3e4f5a6b7c8d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE programs
        ADD COLUMN IF NOT EXISTS booking_opens_at TIMESTAMPTZ
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS booking_opens_at")
