"""add program model parity columns

Revision ID: 7c8d9e0f1a2b
Revises: 6b7c8d9e0f1a
"""
from alembic import op


revision = "7c8d9e0f1a2b"
down_revision = "6b7c8d9e0f1a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS pricing_info TEXT")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS image_url TEXT")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS archive_reason TEXT")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS age_categories TEXT[] DEFAULT '{}'::text[]")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS subject_tags TEXT[] DEFAULT '{}'::text[]")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS is_in_catalog BOOLEAN NOT NULL DEFAULT FALSE")


def downgrade() -> None:
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS is_in_catalog")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS subject_tags")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS age_categories")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS archive_reason")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS archived_at")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS image_url")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS pricing_info")
