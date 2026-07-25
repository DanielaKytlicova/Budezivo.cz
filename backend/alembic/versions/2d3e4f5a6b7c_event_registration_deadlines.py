"""add event registration deadlines

Revision ID: 2d3e4f5a6b7c
Revises: 1c2d3e4f5a6b
"""
from alembic import op
import sqlalchemy as sa


revision = "2d3e4f5a6b7c"
down_revision = "1c2d3e4f5a6b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "events",
        sa.Column("registration_deadline", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "event_dates",
        sa.Column(
            "registration_deadline_override",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("event_dates", "registration_deadline_override")
    op.drop_column("events", "registration_deadline")
