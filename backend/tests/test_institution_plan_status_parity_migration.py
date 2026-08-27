import pathlib
import unittest


MIGRATION = pathlib.Path(
    "backend/alembic/versions/b1c2d3e4f5a6_add_institution_plan_status_parity_columns.py"
)


class InstitutionPlanStatusParityMigrationTests(unittest.TestCase):
    def test_migration_adds_missing_institution_plan_columns(self):
        source = MIGRATION.read_text()

        for marker in (
            '"plan_status"',
            '"plan_activated_by"',
            '"plan_expires_at"',
            '"plan_updated_at"',
            'server_default="active"',
            'down_revision: Union[str, Sequence[str], None] = "a0b1c2d3e4f5"',
        ):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
