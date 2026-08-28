"""backfill program concurrent booking limit

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-08-28 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Treat existing unset program limits as the safe default of one booking."""
    op.execute("UPDATE programs SET max_concurrent_bookings = 1 WHERE max_concurrent_bookings IS NULL")


def downgrade() -> None:
    """No-op: previous intentional unlimited settings cannot be distinguished."""
    pass
