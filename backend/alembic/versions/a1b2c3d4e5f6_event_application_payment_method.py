"""Add payment_method to event_applications (supports free events).

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-07-25

Idempotent: uses IF NOT EXISTS.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE event_applications
            ADD COLUMN IF NOT EXISTS payment_method TEXT
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE event_applications DROP COLUMN IF EXISTS payment_method")
