"""merge event deadline and marketing subscription heads

Revision ID: 3e4f5a6b7c8d
Revises: a7b8c9d0e1f2, 2d3e4f5a6b7c
"""
from typing import Sequence, Union


revision: str = "3e4f5a6b7c8d"
down_revision: Union[str, Sequence[str], None] = (
    "a7b8c9d0e1f2",
    "2d3e4f5a6b7c",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
