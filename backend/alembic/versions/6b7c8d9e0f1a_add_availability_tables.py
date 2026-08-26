"""add availability tables

Revision ID: 6b7c8d9e0f1a
Revises: 5a6b7c8d9e0f
"""
from alembic import op


revision = "6b7c8d9e0f1a"
down_revision = "5a6b7c8d9e0f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS lecturer_availability (
            id UUID PRIMARY KEY,
            lecturer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
            day_of_week INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            is_recurring BOOLEAN DEFAULT TRUE,
            specific_date TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_lecturer_avail_lecturer
        ON lecturer_availability (lecturer_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_lecturer_avail_institution
        ON lecturer_availability (institution_id)
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS lecturer_time_off (
            id UUID PRIMARY KEY,
            lecturer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            reason TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_lecturer_timeoff_lecturer
        ON lecturer_time_off (lecturer_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_lecturer_timeoff_institution
        ON lecturer_time_off (institution_id)
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS availability_exceptions (
            id UUID PRIMARY KEY,
            institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
            scope_type TEXT NOT NULL,
            scope_id UUID NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            reason TEXT,
            created_by UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_avail_exc_scope
        ON availability_exceptions (scope_type, scope_id, date)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_avail_exc_institution
        ON availability_exceptions (institution_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS availability_exceptions")
    op.execute("DROP TABLE IF EXISTS lecturer_time_off")
    op.execute("DROP TABLE IF EXISTS lecturer_availability")
