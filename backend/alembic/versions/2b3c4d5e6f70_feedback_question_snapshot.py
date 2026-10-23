"""Preserve feedback question wording without rewriting historical answers."""
from alembic import op

revision = '2b3c4d5e6f70'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE feedbacks ADD COLUMN IF NOT EXISTS questions_snapshot JSON NULL')


def downgrade():
    # Keep historical wording on application rollback. No data destruction.
    pass
