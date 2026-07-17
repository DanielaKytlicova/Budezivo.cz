"""Revocable hashed ICS feed tokens (calendar_feed_tokens).

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-08

Idempotent. Does NOT touch existing exports/integrations. Old deterministic HMAC
feed URLs stop being accepted for subscription feeds (security fix); the app hands
out fresh revocable tokens on demand.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS calendar_feed_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            feed_type TEXT NOT NULL,
            entity_id UUID,
            scope TEXT NOT NULL DEFAULT 'institution',
            token_hash TEXT NOT NULL UNIQUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            revoked_at TIMESTAMPTZ,
            last_used_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_calendar_feed_tokens_owner ON calendar_feed_tokens(institution_id, user_id, feed_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_calendar_feed_tokens_hash ON calendar_feed_tokens(token_hash)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS calendar_feed_tokens")
