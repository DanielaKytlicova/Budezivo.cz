from pathlib import Path
import unittest

from backend.models.schemas import ProgramCreate


ROOT = Path(__file__).resolve().parents[2]


class ProgramConcurrentDefaultLimitTests(unittest.TestCase):
    def _payload(self, **overrides):
        payload = {
            "name_cs": "Test program",
            "name_en": "Test program",
            "description_cs": "Popis",
            "description_en": "Description",
            "duration": 60,
            "age_group": "schools",
            "target_group": "schools",
        }
        payload.update(overrides)
        return payload

    def test_program_create_defaults_to_single_concurrent_booking(self):
        program = ProgramCreate(**self._payload())

        self.assertEqual(program.max_concurrent_bookings, 1)

    def test_empty_concurrent_limit_still_means_unlimited_when_admin_disables_it(self):
        program = ProgramCreate(**self._payload(max_concurrent_bookings=""))

        self.assertIsNone(program.max_concurrent_bookings)

    def test_ui_new_program_default_has_limit_enabled(self):
        source = (ROOT / "frontend/src/pages/admin/ProgramsPage.js").read_text()

        self.assertIn("max_concurrent_bookings: 1", source)

    def test_database_default_is_one_for_new_program_rows(self):
        migration = (
            ROOT
            / "backend/alembic/versions/c2d3e4f5a6b7_default_program_concurrent_limit.py"
        ).read_text()

        self.assertIn(
            "ALTER TABLE programs ALTER COLUMN max_concurrent_bookings SET DEFAULT 1",
            migration,
        )


if __name__ == "__main__":
    unittest.main()
