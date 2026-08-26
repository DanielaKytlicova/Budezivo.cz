from pathlib import Path
import unittest


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "8d9e0f1a2b3c_add_program_collision_model_columns.py"
)
SOURCE = MIGRATION.read_text(encoding="utf-8")


class ProgramCollisionModelColumnsMigrationTests(unittest.TestCase):
    def test_migration_extends_program_parity_head(self):
        self.assertIn('revision = "8d9e0f1a2b3c"', SOURCE)
        self.assertIn('down_revision = "7c8d9e0f1a2b"', SOURCE)

    def test_adds_collision_columns_read_by_services(self):
        self.assertIn("ADD COLUMN IF NOT EXISTS allow_parallel BOOLEAN DEFAULT FALSE", SOURCE)
        self.assertIn("ADD COLUMN IF NOT EXISTS collision_lecturer_ids JSON DEFAULT '[]'::json", SOURCE)


if __name__ == "__main__":
    unittest.main()
