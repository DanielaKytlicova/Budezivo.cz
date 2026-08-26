from pathlib import Path
import unittest


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "9e0f1a2b3c4d_add_reservation_model_parity_columns.py"
)
SOURCE = MIGRATION.read_text(encoding="utf-8")


class ReservationModelParityMigrationTests(unittest.TestCase):
    def test_migration_extends_current_head(self):
        self.assertIn('revision = "9e0f1a2b3c4d"', SOURCE)
        self.assertIn('down_revision = "8d9e0f1a2b3c"', SOURCE)

    def test_adds_reservation_columns_read_by_model(self):
        for marker in [
            "ADD COLUMN IF NOT EXISTS assignment_source TEXT",
            "ADD COLUMN IF NOT EXISTS assignment_reason TEXT",
            "ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN DEFAULT FALSE",
            "ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ",
            "ADD COLUMN IF NOT EXISTS terms_accepted_text_version TEXT DEFAULT 'v1'",
            "ADD COLUMN IF NOT EXISTS visit_reminder_sent_at TIMESTAMPTZ",
            "ADD COLUMN IF NOT EXISTS visit_reminder_last_attempt_at TIMESTAMPTZ",
            "ADD COLUMN IF NOT EXISTS visit_reminder_error TEXT",
        ]:
            self.assertIn(marker, SOURCE)


if __name__ == "__main__":
    unittest.main()
