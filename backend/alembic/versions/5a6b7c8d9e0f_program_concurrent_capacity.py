"""add per-program concurrent booking capacity

Revision ID: 5a6b7c8d9e0f
Revises: 4f5a6b7c8d9e
"""
from alembic import op


revision = "5a6b7c8d9e0f"
down_revision = "4f5a6b7c8d9e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE programs
        ADD COLUMN IF NOT EXISTS max_concurrent_bookings INTEGER
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS max_concurrent_bookings")
