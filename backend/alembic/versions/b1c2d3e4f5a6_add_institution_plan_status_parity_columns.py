"""add institution plan status parity columns

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-08-27 22:25:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Institution model columns missing from historical billing migration."""
    op.execute(
        "ALTER TABLE institutions "
        "ADD COLUMN IF NOT EXISTS plan_status TEXT NOT NULL DEFAULT 'active'"
    )
    op.execute("ALTER TABLE institutions ADD COLUMN IF NOT EXISTS plan_activated_by TEXT")
    op.execute("ALTER TABLE institutions ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMPTZ")
    op.execute("ALTER TABLE institutions ADD COLUMN IF NOT EXISTS plan_updated_at TIMESTAMPTZ")


def downgrade() -> None:
    """Remove Institution model parity columns."""
    op.drop_column("institutions", "plan_updated_at")
    op.drop_column("institutions", "plan_expires_at")
    op.drop_column("institutions", "plan_activated_by")
    op.drop_column("institutions", "plan_status")
