"""add configurable program booking options

Revision ID: f2a3b4c5d6e7
Revises: e0f1a2b3c4d5
"""

from alembic import op
import sqlalchemy as sa


revision = "f2a3b4c5d6e7"
down_revision = "e0f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("programs", sa.Column("booking_time_note_enabled", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("programs", sa.Column("booking_time_note", sa.Text(), nullable=True))
    op.add_column("programs", sa.Column("booking_payment_enabled", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("programs", sa.Column("booking_payment_required", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("programs", sa.Column("booking_payment_methods", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False))
    op.add_column("programs", sa.Column("max_bookings_per_day", sa.Integer(), nullable=True))
    op.add_column("reservations", sa.Column("payment_method", sa.Text(), nullable=True))
    op.add_column("reservations", sa.Column("invoice_details", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("reservations", "invoice_details")
    op.drop_column("reservations", "payment_method")
    op.drop_column("programs", "booking_payment_methods")
    op.drop_column("programs", "max_bookings_per_day")
    op.drop_column("programs", "booking_payment_required")
    op.drop_column("programs", "booking_payment_enabled")
    op.drop_column("programs", "booking_time_note")
    op.drop_column("programs", "booking_time_note_enabled")
