"""Google Calendar two-way sync: integration sync-mode flags + exported event links.

Revision ID: f1a2b3c4d5e6
Revises: e3f4a5b6c7d8
Create Date: 2026-07-20

Idempotent: uses IF NOT EXISTS so it can run safely against an already-patched DB.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Per-user sync-mode flags on the existing calendar integration row.
    op.execute("""
        ALTER TABLE user_calendar_integrations
            ADD COLUMN IF NOT EXISTS import_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS export_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS auto_sync_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS needs_reconnect BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS granted_scopes TEXT
    """)

    # 2) Mapping of Budeživo reservations -> exported provider calendar events.
    op.execute("""
        CREATE TABLE IF NOT EXISTS calendar_event_exports (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            booking_id UUID NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
            provider TEXT NOT NULL DEFAULT 'google',
            google_calendar_id TEXT,
            google_event_id TEXT,
            last_synced_at TIMESTAMPTZ,
            sync_status TEXT DEFAULT 'pending',
            sync_error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    # One exported event per (provider, user, booking) — prevents duplicates.
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_calendar_event_exports_provider_user_booking
            ON calendar_event_exports (provider, user_id, booking_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_calendar_event_exports_inst
            ON calendar_event_exports (institution_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS calendar_event_exports")
    op.execute("""
        ALTER TABLE user_calendar_integrations
            DROP COLUMN IF EXISTS import_enabled,
            DROP COLUMN IF EXISTS export_enabled,
            DROP COLUMN IF EXISTS auto_sync_enabled,
            DROP COLUMN IF EXISTS needs_reconnect,
            DROP COLUMN IF EXISTS granted_scopes
    """)
