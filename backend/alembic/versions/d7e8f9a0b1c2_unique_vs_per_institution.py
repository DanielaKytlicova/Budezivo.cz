"""unique variable_symbol per institution (event_applications)

Revision ID: d7e8f9a0b1c2
Revises: 4a03e6106002
Create Date: 2026-06-12 21:30:00

Security/data-integrity hardening: a partial UNIQUE index on
(institution_id, variable_symbol) for event_applications. Payment lookups and
manual/QR bank-transfer reconciliation match per-tenant by VS, so a duplicate
VS inside one institution could mis-link a payment to the wrong application.

Partial index (WHERE variable_symbol IS NOT NULL) so rows without a VS are not
constrained. The application layer already generates a collision-free VS; this
index is the hard DB-level guarantee.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, Sequence[str], None] = '4a03e6106002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_event_applications_inst_vs
        ON event_applications (institution_id, variable_symbol)
        WHERE variable_symbol IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_event_applications_inst_vs")
