from pathlib import Path
import unittest


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "7c8d9e0f1a2b_add_program_model_parity_columns.py"
)
SOURCE = MIGRATION.read_text(encoding="utf-8")


class ProgramModelParityMigrationTests(unittest.TestCase):
    def test_migration_extends_availability_head(self):
        self.assertIn('revision = "7c8d9e0f1a2b"', SOURCE)
        self.assertIn('down_revision = "6b7c8d9e0f1a"', SOURCE)

    def test_adds_program_columns_read_by_model(self):
        for column_name in (
            "pricing_info",
            "image_url",
            "archived_at",
            "archive_reason",
            "age_categories",
            "subject_tags",
            "is_in_catalog",
        ):
            self.assertIn(f"ADD COLUMN IF NOT EXISTS {column_name}", SOURCE)

    def test_array_and_boolean_defaults_match_model_expectations(self):
        self.assertIn("age_categories TEXT[] DEFAULT '{}'::text[]", SOURCE)
        self.assertIn("subject_tags TEXT[] DEFAULT '{}'::text[]", SOURCE)
        self.assertIn("is_in_catalog BOOLEAN NOT NULL DEFAULT FALSE", SOURCE)


if __name__ == "__main__":
    unittest.main()
