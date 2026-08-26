"""add reservation model parity columns

Revision ID: 9e0f1a2b3c4d
Revises: 8d9e0f1a2b3c
"""
from alembic import op


revision = "9e0f1a2b3c4d"
down_revision = "8d9e0f1a2b3c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE reservations ADD COLUMN IF NOT EXISTS assignment_source TEXT")
    op.execute("ALTER TABLE reservations ADD COLUMN IF NOT EXISTS assignment_reason TEXT")
    op.execute("ALTER TABLE reservations ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE reservations ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ")
    op.execute("ALTER TABLE reservations ADD COLUMN IF NOT EXISTS terms_accepted_text_version TEXT DEFAULT 'v1'")
    op.execute("ALTER TABLE reservations ADD COLUMN IF NOT EXISTS visit_reminder_sent_at TIMESTAMPTZ")
    op.execute("ALTER TABLE reservations ADD COLUMN IF NOT EXISTS visit_reminder_last_attempt_at TIMESTAMPTZ")
    op.execute("ALTER TABLE reservations ADD COLUMN IF NOT EXISTS visit_reminder_error TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE reservations DROP COLUMN IF EXISTS visit_reminder_error")
    op.execute("ALTER TABLE reservations DROP COLUMN IF EXISTS visit_reminder_last_attempt_at")
    op.execute("ALTER TABLE reservations DROP COLUMN IF EXISTS visit_reminder_sent_at")
    op.execute("ALTER TABLE reservations DROP COLUMN IF EXISTS terms_accepted_text_version")
    op.execute("ALTER TABLE reservations DROP COLUMN IF EXISTS terms_accepted_at")
    op.execute("ALTER TABLE reservations DROP COLUMN IF EXISTS terms_accepted")
    op.execute("ALTER TABLE reservations DROP COLUMN IF EXISTS assignment_reason")
    op.execute("ALTER TABLE reservations DROP COLUMN IF EXISTS assignment_source")
