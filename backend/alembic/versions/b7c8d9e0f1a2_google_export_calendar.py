"""Store the dedicated Google Calendar used for Budeživo reservation exports."""
from typing import Sequence, Union

from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE user_calendar_integrations "
        "ADD COLUMN IF NOT EXISTS google_export_calendar_id TEXT"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE user_calendar_integrations "
        "DROP COLUMN IF EXISTS google_export_calendar_id"
    )
