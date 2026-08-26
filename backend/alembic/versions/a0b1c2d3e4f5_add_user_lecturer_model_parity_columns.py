"""add user lecturer model parity columns

Revision ID: a0b1c2d3e4f5
Revises: 9e0f1a2b3c4d
"""
from alembic import op


revision = "a0b1c2d3e4f5"
down_revision = "9e0f1a2b3c4d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS lecturer_mode TEXT NOT NULL DEFAULT 'main'")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_age_groups JSONB DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS supported_program_ids JSONB DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS learning_program_ids JSONB DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS admin_note TEXT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN DEFAULT FALSE")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS terms_accepted")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS admin_note")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS learning_program_ids")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS supported_program_ids")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS preferred_age_groups")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS lecturer_mode")
