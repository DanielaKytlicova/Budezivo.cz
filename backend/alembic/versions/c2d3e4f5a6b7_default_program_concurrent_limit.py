"""default program concurrent booking limit

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-08-28 09:45:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make new programs default to one same-program booking per slot."""
    op.execute("ALTER TABLE programs ALTER COLUMN max_concurrent_bookings SET DEFAULT 1")


def downgrade() -> None:
    """Restore unlimited default for new programs."""
    op.execute("ALTER TABLE programs ALTER COLUMN max_concurrent_bookings DROP DEFAULT")
