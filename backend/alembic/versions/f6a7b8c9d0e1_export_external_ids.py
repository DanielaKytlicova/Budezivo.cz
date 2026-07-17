"""Generalise calendar_event_exports for non-Google providers (external ids).

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-09

Idempotent. Adds provider-agnostic external_calendar_id / external_event_id used by
the Microsoft export. Existing Google export rows are untouched (they keep using
google_calendar_id / google_event_id).
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE calendar_event_exports ADD COLUMN IF NOT EXISTS external_calendar_id TEXT")
    op.execute("ALTER TABLE calendar_event_exports ADD COLUMN IF NOT EXISTS external_event_id TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE calendar_event_exports DROP COLUMN IF EXISTS external_event_id")
    op.execute("ALTER TABLE calendar_event_exports DROP COLUMN IF EXISTS external_calendar_id")
