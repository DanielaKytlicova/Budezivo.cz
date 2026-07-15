"""Two-level payment methods (institution allowed_methods + event allowed_payment_methods).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-05

Idempotent: uses IF NOT EXISTS + guarded backfills.

Backfill rules:
- institution_payment_settings.payment_mode -> allowed_methods:
    'both'    -> ["qr", "gateway"]
    'gateway' -> ["gateway"]
    else      -> ["qr"]
  (cash is NEVER auto-enabled)
- existing PAID events inherit their institution's allowed_methods.
- free events keep NULL (no methods).
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Institution-level allowed methods
    op.execute("""
        ALTER TABLE institution_payment_settings
            ADD COLUMN IF NOT EXISTS allowed_methods JSONB
    """)
    op.execute("""
        UPDATE institution_payment_settings
        SET allowed_methods = CASE
            WHEN payment_mode = 'both' THEN '["qr", "gateway"]'::jsonb
            WHEN payment_mode = 'gateway' THEN '["gateway"]'::jsonb
            ELSE '["qr"]'::jsonb
        END
        WHERE allowed_methods IS NULL
    """)

    # 2) Event-level allowed methods
    op.execute("""
        ALTER TABLE events
            ADD COLUMN IF NOT EXISTS allowed_payment_methods JSONB
    """)
    op.execute("""
        UPDATE events e
        SET allowed_payment_methods = COALESCE(ps.allowed_methods, '["qr"]'::jsonb)
        FROM institution_payment_settings ps
        WHERE ps.institution_id = e.institution_id
          AND COALESCE(e.price, 0) > 0
          AND e.allowed_payment_methods IS NULL
    """)

    # 3) Manual-payment audit fields on applications
    op.execute("""
        ALTER TABLE event_applications
            ADD COLUMN IF NOT EXISTS paid_marked_by_email TEXT
    """)
    op.execute("""
        ALTER TABLE event_applications
            ADD COLUMN IF NOT EXISTS paid_marked_at TIMESTAMPTZ
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE event_applications DROP COLUMN IF EXISTS paid_marked_at")
    op.execute("ALTER TABLE event_applications DROP COLUMN IF EXISTS paid_marked_by_email")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS allowed_payment_methods")
    op.execute("ALTER TABLE institution_payment_settings DROP COLUMN IF EXISTS allowed_methods")
