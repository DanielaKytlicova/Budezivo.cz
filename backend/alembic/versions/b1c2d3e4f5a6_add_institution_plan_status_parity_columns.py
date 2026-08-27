"""add institution plan status parity columns

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-08-27 22:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Institution model columns missing from historical billing migration."""
    op.add_column(
        "institutions",
        sa.Column("plan_status", sa.Text(), nullable=False, server_default="active"),
    )
    op.add_column("institutions", sa.Column("plan_activated_by", sa.Text(), nullable=True))
    op.add_column("institutions", sa.Column("plan_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("institutions", sa.Column("plan_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove Institution model parity columns."""
    op.drop_column("institutions", "plan_updated_at")
    op.drop_column("institutions", "plan_expires_at")
    op.drop_column("institutions", "plan_activated_by")
    op.drop_column("institutions", "plan_status")
