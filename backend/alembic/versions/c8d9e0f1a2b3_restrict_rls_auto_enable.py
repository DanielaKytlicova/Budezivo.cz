"""Restrict direct execution of the automatic RLS event-trigger helper."""

from typing import Sequence, Union

from alembic import op


revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regprocedure('public.rls_auto_enable()') IS NOT NULL THEN
                REVOKE EXECUTE ON FUNCTION public.rls_auto_enable()
                    FROM PUBLIC, anon, authenticated;
            END IF;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regprocedure('public.rls_auto_enable()') IS NOT NULL THEN
                GRANT EXECUTE ON FUNCTION public.rls_auto_enable()
                    TO PUBLIC, anon, authenticated;
            END IF;
        END;
        $$;
        """
    )
