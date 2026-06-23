"""add institution_join_requests

Revision ID: 4a03e6106002
Revises: c93b07e1d8f2
Create Date: 2026-06-04 13:25:47

Phase 83 — institution duplicate protection + join-request workflow.

Pure additive migration: creates a single new table ``institution_join_requests``
and its supporting indexes. Spurious autogenerate noise (JSONB↔JSON type
oscillations, NOT NULL adjustments on pre-existing columns, etc.) was stripped
out so this migration does NOT touch any existing table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a03e6106002'
down_revision: Union[str, Sequence[str], None] = 'c93b07e1d8f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the institution_join_requests table (Phase 83)."""
    op.create_table(
        'institution_join_requests',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('institution_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False,
                  server_default=sa.text("'pending'::text")),
        sa.Column('assigned_role', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_join_req_email', 'institution_join_requests',
                    ['email'], unique=False)
    op.create_index('idx_join_req_institution', 'institution_join_requests',
                    ['institution_id'], unique=False)
    op.create_index('idx_join_req_status', 'institution_join_requests',
                    ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_join_req_status', table_name='institution_join_requests')
    op.drop_index('idx_join_req_institution', table_name='institution_join_requests')
    op.drop_index('idx_join_req_email', table_name='institution_join_requests')
    op.drop_table('institution_join_requests')
