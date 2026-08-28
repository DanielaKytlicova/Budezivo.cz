"""allow unlimited program concurrent booking limit

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-08-28 10:35:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Keep the safe default, but allow admins to intentionally choose unlimited."""
    op.execute("ALTER TABLE programs ALTER COLUMN max_concurrent_bookings DROP NOT NULL")


def downgrade() -> None:
    """Restore non-null constraint after replacing unlimited rows with default 1."""
    op.execute("UPDATE programs SET max_concurrent_bookings = 1 WHERE max_concurrent_bookings IS NULL")
    op.execute("ALTER TABLE programs ALTER COLUMN max_concurrent_bookings SET NOT NULL")
