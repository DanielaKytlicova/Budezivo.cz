"""add Resend delivery states

Revision ID: 1c2d3e4f5a6b
Revises: c93b07e1d8f2
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '1c2d3e4f5a6b'
down_revision = 'c93b07e1d8f2'
branch_labels = None
depends_on = None


def upgrade():
    for table in ('contacts', 'school_contacts'):
        op.execute(f"""
            ALTER TABLE IF EXISTS {table}
                ADD COLUMN IF NOT EXISTS deliverability_status TEXT NOT NULL DEFAULT 'unknown',
                ADD COLUMN IF NOT EXISTS deliverability_reason TEXT,
                ADD COLUMN IF NOT EXISTS deliverability_updated_at TIMESTAMPTZ
        """)

    op.execute("""
        ALTER TABLE IF EXISTS mailing_campaign_recipients
            ADD COLUMN IF NOT EXISTS delivery_status TEXT NOT NULL DEFAULT 'unknown',
            ADD COLUMN IF NOT EXISTS delivery_event_at TIMESTAMPTZ
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS resend_webhook_events (
            id UUID PRIMARY KEY,
            svix_id TEXT NOT NULL UNIQUE,
            event_type TEXT NOT NULL,
            provider_email_id TEXT,
            recipient_email TEXT,
            event_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_resend_webhook_provider_email
        ON resend_webhook_events (provider_email_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_resend_webhook_recipient
        ON resend_webhook_events (recipient_email)
    """)

def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_resend_webhook_recipient")
    op.execute("DROP INDEX IF EXISTS idx_resend_webhook_provider_email")
    op.execute("DROP TABLE IF EXISTS resend_webhook_events")
    op.execute("""
        ALTER TABLE IF EXISTS mailing_campaign_recipients
            DROP COLUMN IF EXISTS delivery_event_at,
            DROP COLUMN IF EXISTS delivery_status
    """)
    for table in ('school_contacts', 'contacts'):
        op.execute(f"""
            ALTER TABLE IF EXISTS {table}
                DROP COLUMN IF EXISTS deliverability_updated_at,
                DROP COLUMN IF EXISTS deliverability_reason,
                DROP COLUMN IF EXISTS deliverability_status
        """)
