"""multi-lecturer support: programs.required_lecturers + reservations.assigned_lecturer_ids

Revision ID: e3f4a5b6c7d8
Revises: d7e8f9a0b1c2
Create Date: 2026-06-12 22:00:00

Additive only:
- programs.required_lecturers INTEGER NOT NULL DEFAULT 1
  (>1 enforces "N qualified lecturers must be free" at booking time).
- reservations.assigned_lecturer_ids JSONB DEFAULT '[]'
  (holds every assigned lecturer; the main one stays in assigned_lecturer_id).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, Sequence[str], None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE programs ADD COLUMN IF NOT EXISTS required_lecturers INTEGER NOT NULL DEFAULT 1"
    )
    op.execute(
        "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS assigned_lecturer_ids JSONB DEFAULT '[]'::jsonb"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE reservations DROP COLUMN IF EXISTS assigned_lecturer_ids")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS required_lecturers")
