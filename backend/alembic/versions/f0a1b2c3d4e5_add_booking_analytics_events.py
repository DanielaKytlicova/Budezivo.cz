"""add booking analytics events

Revision ID: f0a1b2c3d4e5
Revises: e4f5a6b7c8d9
Create Date: 2026-08-31 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f0a1b2c3d4e5"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "booking_analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("institutions.id", ondelete="CASCADE")),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("programs.id", ondelete="SET NULL")),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reservations.id", ondelete="SET NULL")),
        sa.Column("session_id", sa.Text()),
        sa.Column("reason", sa.Text()),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.create_index("idx_booking_analytics_created_at", "booking_analytics_events", ["created_at"])
    op.create_index("idx_booking_analytics_event_type", "booking_analytics_events", ["event_type"])
    op.create_index("idx_booking_analytics_institution", "booking_analytics_events", ["institution_id"])
    op.create_index("idx_booking_analytics_program", "booking_analytics_events", ["program_id"])
    op.create_index("idx_booking_analytics_session", "booking_analytics_events", ["session_id"])
    op.create_index("idx_booking_analytics_reservation", "booking_analytics_events", ["reservation_id"])


def downgrade() -> None:
    op.drop_index("idx_booking_analytics_reservation", table_name="booking_analytics_events")
    op.drop_index("idx_booking_analytics_session", table_name="booking_analytics_events")
    op.drop_index("idx_booking_analytics_program", table_name="booking_analytics_events")
    op.drop_index("idx_booking_analytics_institution", table_name="booking_analytics_events")
    op.drop_index("idx_booking_analytics_event_type", table_name="booking_analytics_events")
    op.drop_index("idx_booking_analytics_created_at", table_name="booking_analytics_events")
    op.drop_table("booking_analytics_events")
