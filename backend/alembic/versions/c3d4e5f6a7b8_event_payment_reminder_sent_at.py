"""Add payment_reminder_sent_at to event_applications (payment reminders).

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-06

Idempotent: uses IF NOT EXISTS.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE event_applications
            ADD COLUMN IF NOT EXISTS payment_reminder_sent_at TIMESTAMPTZ
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE event_applications DROP COLUMN IF EXISTS payment_reminder_sent_at")
