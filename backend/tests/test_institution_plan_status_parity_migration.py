import pathlib
import unittest


MIGRATION = pathlib.Path(
    "backend/alembic/versions/b1c2d3e4f5a6_add_institution_plan_status_parity_columns.py"
)


class InstitutionPlanStatusParityMigrationTests(unittest.TestCase):
    def test_migration_adds_missing_institution_plan_columns(self):
        source = MIGRATION.read_text()

        for marker in (
            "ADD COLUMN IF NOT EXISTS plan_status",
            "ADD COLUMN IF NOT EXISTS plan_activated_by",
            "ADD COLUMN IF NOT EXISTS plan_expires_at",
            "ADD COLUMN IF NOT EXISTS plan_updated_at",
            "DEFAULT 'active'",
            'down_revision: Union[str, Sequence[str], None] = "a0b1c2d3e4f5"',
        ):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
