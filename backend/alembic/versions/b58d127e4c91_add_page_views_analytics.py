"""add page_views (traffic analytics)

Revision ID: b58d127e4c91
Revises: a47c891fc3e2
Create Date: 2026-04-28 21:00:00.000000

Lightweight traffic analytics — records anonymized visits so a Superadmin
can see daily page-view counts and top paths without relying on a 3rd-party
analytics service.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b58d127e4c91'
down_revision: Union[str, Sequence[str], None] = 'a47c891fc3e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'page_views',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('ip_hash', sa.Text(), nullable=False),
        sa.Column('user_agent', sa.Text()),
        sa.Column('session_id', sa.Text(), nullable=False),
        sa.Column('referrer', sa.Text()),
    )
    op.create_index('idx_page_views_created_at', 'page_views', ['created_at'])
    op.create_index('idx_page_views_session', 'page_views', ['session_id'])
    op.create_index('idx_page_views_path', 'page_views', ['path'])


def downgrade() -> None:
    op.drop_index('idx_page_views_path', table_name='page_views')
    op.drop_index('idx_page_views_session', table_name='page_views')
    op.drop_index('idx_page_views_created_at', table_name='page_views')
    op.drop_table('page_views')
