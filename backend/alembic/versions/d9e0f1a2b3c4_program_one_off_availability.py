"""Add isolated, date-specific program availability without changing schedules."""
from alembic import op

revision = "d9e0f1a2b3c4"
down_revision = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE program_one_off_availability (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
            program_id UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            created_by UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_program_one_off_slot UNIQUE
                (institution_id, program_id, date, start_time, end_time),
            CONSTRAINT ck_program_one_off_time CHECK (
                start_time ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'
                AND end_time ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'
                AND end_time > start_time
            )
        )
    """)
    op.execute("CREATE INDEX idx_program_one_off_date ON program_one_off_availability (institution_id, program_id, date)")
    # Access is exclusively through the tenant-scoped backend, not Supabase clients.
    op.execute("ALTER TABLE program_one_off_availability ENABLE ROW LEVEL SECURITY")


def downgrade():
    op.execute("DROP TABLE program_one_off_availability")
