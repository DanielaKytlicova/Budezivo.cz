"""Merge the calendar import and booking analytics migration heads.

This revision intentionally performs no schema or data operation. It only
allows the deployment command ``alembic upgrade head`` to advance both
existing migration branches together.
"""
from typing import Sequence, Union


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = (
    "a6b7c8d9e0f1",
    "f0a1b2c3d4e5",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
