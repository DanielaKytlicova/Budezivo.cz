"""Institution-scoped marketing subscriptions and unsubscribe feedback.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'marketing_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('subscribed', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('unsubscribed_at', sa.DateTime(timezone=True)),
        sa.Column('resubscribed_at', sa.DateTime(timezone=True)),
        sa.Column('unsubscribe_reason', sa.Text()),
        sa.Column('unsubscribe_comment', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('uq_marketing_subscription_inst_email', 'marketing_subscriptions', ['institution_id', 'email'], unique=True)
    op.create_index('idx_marketing_subscription_status', 'marketing_subscriptions', ['institution_id', 'subscribed'])


def downgrade() -> None:
    op.drop_table('marketing_subscriptions')
