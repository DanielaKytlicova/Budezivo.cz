from pathlib import Path
import unittest


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "6b7c8d9e0f1a_add_availability_tables.py"
)
SOURCE = MIGRATION.read_text(encoding="utf-8")


class AvailabilityTablesMigrationTests(unittest.TestCase):
    def test_migration_extends_capacity_head(self):
        self.assertIn('revision = "6b7c8d9e0f1a"', SOURCE)
        self.assertIn('down_revision = "5a6b7c8d9e0f"', SOURCE)

    def test_creates_all_availability_tables_idempotently(self):
        for table_name in (
            "lecturer_availability",
            "lecturer_time_off",
            "availability_exceptions",
        ):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table_name}", SOURCE)

    def test_creates_service_indexes(self):
        for index_name in (
            "idx_lecturer_avail_lecturer",
            "idx_lecturer_avail_institution",
            "idx_lecturer_timeoff_lecturer",
            "idx_lecturer_timeoff_institution",
            "idx_avail_exc_scope",
            "idx_avail_exc_institution",
        ):
            self.assertIn(index_name, SOURCE)


if __name__ == "__main__":
    unittest.main()
