"""add archive_custom_text to programs

Revision ID: a47c891fc3e2
Revises: 94b721cab60e
Create Date: 2026-04-28 20:30:00.000000

Free-form curatorial note that gets rendered into the archive PDF as the
``Poznámka`` section. Editable from the archive page edit dialog.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a47c891fc3e2'
down_revision: Union[str, Sequence[str], None] = '94b721cab60e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('programs', sa.Column('archive_custom_text', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('programs', 'archive_custom_text')
