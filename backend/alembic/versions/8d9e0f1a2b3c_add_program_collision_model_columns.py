"""add program collision model columns

Revision ID: 8d9e0f1a2b3c
Revises: 7c8d9e0f1a2b
"""
from alembic import op


revision = "8d9e0f1a2b3c"
down_revision = "7c8d9e0f1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS allow_parallel BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS collision_lecturer_ids JSON DEFAULT '[]'::json")


def downgrade() -> None:
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS collision_lecturer_ids")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS allow_parallel")
