"""add Resend delivery states

Revision ID: 1c2d3e4f5a6b
Revises: 486a61019955
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '1c2d3e4f5a6b'
down_revision = '486a61019955'
branch_labels = None
depends_on = None


def upgrade():
    for table in ('contacts', 'school_contacts'):
        op.add_column(table, sa.Column('deliverability_status', sa.Text(), nullable=False, server_default='unknown'))
        op.add_column(table, sa.Column('deliverability_reason', sa.Text(), nullable=True))
        op.add_column(table, sa.Column('deliverability_updated_at', sa.DateTime(timezone=True), nullable=True))

    op.add_column('mailing_campaign_recipients', sa.Column('delivery_status', sa.Text(), nullable=False, server_default='unknown'))
    op.add_column('mailing_campaign_recipients', sa.Column('delivery_event_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'resend_webhook_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('svix_id', sa.Text(), nullable=False),
        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('provider_email_id', sa.Text(), nullable=True),
        sa.Column('recipient_email', sa.Text(), nullable=True),
        sa.Column('event_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('svix_id'),
    )
    op.create_index('idx_resend_webhook_provider_email', 'resend_webhook_events', ['provider_email_id'])
    op.create_index('idx_resend_webhook_recipient', 'resend_webhook_events', ['recipient_email'])


def downgrade():
    op.drop_index('idx_resend_webhook_recipient', table_name='resend_webhook_events')
    op.drop_index('idx_resend_webhook_provider_email', table_name='resend_webhook_events')
    op.drop_table('resend_webhook_events')
    op.drop_column('mailing_campaign_recipients', 'delivery_event_at')
    op.drop_column('mailing_campaign_recipients', 'delivery_status')
    for table in ('school_contacts', 'contacts'):
        op.drop_column(table, 'deliverability_updated_at')
        op.drop_column(table, 'deliverability_reason')
        op.drop_column(table, 'deliverability_status')
