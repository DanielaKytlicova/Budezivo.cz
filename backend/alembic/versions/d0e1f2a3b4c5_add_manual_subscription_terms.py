"""Add manually managed institution subscription terms.

Revision ID: d0e1f2a3b4c5
Revises: c8d9e0f1a2b3, d9e0f1a2b3c4
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = (
    "c8d9e0f1a2b3",
    "d9e0f1a2b3c4",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE institutions
            ADD COLUMN IF NOT EXISTS subscription_price_amount INTEGER,
            ADD COLUMN IF NOT EXISTS subscription_currency TEXT NOT NULL DEFAULT 'CZK',
            ADD COLUMN IF NOT EXISTS subscription_billing_cycle TEXT,
            ADD COLUMN IF NOT EXISTS subscription_period_start TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS subscription_period_end TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS subscription_due_days INTEGER NOT NULL DEFAULT 30,
            ADD COLUMN IF NOT EXISTS subscription_renewal_mode TEXT NOT NULL DEFAULT 'manual',
            ADD COLUMN IF NOT EXISTS subscription_consent_status TEXT NOT NULL DEFAULT 'pending',
            ADD COLUMN IF NOT EXISTS subscription_billing_email TEXT,
            ADD COLUMN IF NOT EXISTS subscription_copy_email TEXT,
            ADD COLUMN IF NOT EXISTS subscription_payment_status TEXT NOT NULL DEFAULT 'not_invoiced',
            ADD COLUMN IF NOT EXISTS subscription_amount_paid INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS subscription_invoice_number TEXT;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE institutions
            DROP COLUMN IF EXISTS subscription_invoice_number,
            DROP COLUMN IF EXISTS subscription_amount_paid,
            DROP COLUMN IF EXISTS subscription_payment_status,
            DROP COLUMN IF EXISTS subscription_copy_email,
            DROP COLUMN IF EXISTS subscription_billing_email,
            DROP COLUMN IF EXISTS subscription_consent_status,
            DROP COLUMN IF EXISTS subscription_renewal_mode,
            DROP COLUMN IF EXISTS subscription_due_days,
            DROP COLUMN IF EXISTS subscription_period_end,
            DROP COLUMN IF EXISTS subscription_period_start,
            DROP COLUMN IF EXISTS subscription_billing_cycle,
            DROP COLUMN IF EXISTS subscription_currency,
            DROP COLUMN IF EXISTS subscription_price_amount;
        """
    )
