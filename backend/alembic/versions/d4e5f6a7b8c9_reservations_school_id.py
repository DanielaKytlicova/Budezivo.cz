"""Add nullable reservations.school_id (reliable School link for safe purge & stats).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-07

Idempotent. FK ON DELETE SET NULL (deleting a school never deletes reservations).
Backfill is conservative: a reservation gets a school_id ONLY when there is exactly
ONE school with a matching name WITHIN THE SAME INSTITUTION. Ambiguous rows (0 or
>1 matches) are left NULL on purpose and never matched across institutions.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE reservations ADD COLUMN IF NOT EXISTS school_id UUID")

    # FK (SET NULL) — guarded so re-running does not error.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_reservations_school_id'
            ) THEN
                ALTER TABLE reservations
                    ADD CONSTRAINT fk_reservations_school_id
                    FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_reservations_school_id ON reservations(school_id)")

    # Conservative, unambiguous, same-institution backfill.
    op.execute("""
        UPDATE reservations r
        SET school_id = s.id
        FROM schools s
        WHERE r.school_id IS NULL
          AND s.institution_id = r.institution_id
          AND s.name = r.school_name
          AND (
              SELECT COUNT(*) FROM schools s2
              WHERE s2.institution_id = r.institution_id
                AND s2.name = r.school_name
          ) = 1
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_reservations_school_id")
    op.execute("ALTER TABLE reservations DROP CONSTRAINT IF EXISTS fk_reservations_school_id")
    op.execute("ALTER TABLE reservations DROP COLUMN IF EXISTS school_id")
