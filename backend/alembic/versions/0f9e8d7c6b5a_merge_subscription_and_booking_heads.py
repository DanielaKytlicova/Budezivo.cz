"""Merge subscription and program booking migration heads.

Revision ID: 0f9e8d7c6b5a
Revises: d0e1f2a3b4c5, f2a3b4c5d6e7

This migration intentionally performs no schema operation. Both parent
migrations remain responsible for their own additive changes; this revision
only restores one canonical Alembic head for deployment.
"""

from typing import Sequence, Union


revision: str = "0f9e8d7c6b5a"
down_revision: Union[str, Sequence[str], None] = (
    "d0e1f2a3b4c5",
    "f2a3b4c5d6e7",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
