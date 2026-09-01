"""Add explicit external calendar selection and disable implicit imports."""
from typing import Sequence, Union
from alembic import op

revision: str = 'a6b7c8d9e0f1'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("ALTER TABLE user_calendar_integrations ADD COLUMN IF NOT EXISTS availability_calendar_id TEXT")
    op.execute("ALTER TABLE user_calendar_integrations ALTER COLUMN import_enabled SET DEFAULT FALSE")
    op.execute("""
        UPDATE user_calendar_integrations
        SET import_enabled = FALSE
        WHERE import_enabled = TRUE
          AND availability_calendar_id IS NULL
          AND provider IN ('google', 'microsoft')
    """)

def downgrade() -> None:
    op.execute("ALTER TABLE user_calendar_integrations ALTER COLUMN import_enabled SET DEFAULT TRUE")
    op.execute("ALTER TABLE user_calendar_integrations DROP COLUMN IF EXISTS availability_calendar_id")
