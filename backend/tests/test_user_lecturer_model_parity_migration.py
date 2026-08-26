from pathlib import Path
import unittest


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "a0b1c2d3e4f5_add_user_lecturer_model_parity_columns.py"
)
SOURCE = MIGRATION.read_text(encoding="utf-8")


class UserLecturerModelParityMigrationTests(unittest.TestCase):
    def test_migration_extends_current_head(self):
        self.assertIn('revision = "a0b1c2d3e4f5"', SOURCE)
        self.assertIn('down_revision = "9e0f1a2b3c4d"', SOURCE)

    def test_adds_lecturer_columns_read_by_model(self):
        for marker in [
            "ADD COLUMN IF NOT EXISTS lecturer_mode TEXT NOT NULL DEFAULT 'main'",
            "ADD COLUMN IF NOT EXISTS preferred_age_groups JSONB DEFAULT '[]'::jsonb",
            "ADD COLUMN IF NOT EXISTS supported_program_ids JSONB DEFAULT '[]'::jsonb",
            "ADD COLUMN IF NOT EXISTS learning_program_ids JSONB DEFAULT '[]'::jsonb",
            "ADD COLUMN IF NOT EXISTS admin_note TEXT",
            "ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN DEFAULT FALSE",
        ]:
            self.assertIn(marker, SOURCE)


if __name__ == "__main__":
    unittest.main()
