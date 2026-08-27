import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AVAILABILITY_ROUTE = ROOT / "routes" / "availability.py"


class AvailabilityDateGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = AVAILABILITY_ROUTE.read_text(encoding="utf-8")

    def test_day_availability_uses_same_program_date_window_as_calendar(self):
        self.assertIn("def _date_allowed_by_program_booking_window", self.source)
        self.assertIn('program.get("status") != "active" or not program.get("is_published")', self.source)
        self.assertIn("min_days_before_booking", self.source)
        self.assertIn("max_days_before_booking", self.source)
        self.assertIn("_program_validity_date(program.get(\"start_date\"))", self.source)
        self.assertIn("_program_validity_date(program.get(\"end_date\"))", self.source)

    def test_program_window_is_checked_before_creating_time_blocks(self):
        guard = "if not _date_allowed_by_program_booking_window(program, date_obj, datetime.now(timezone.utc)):"
        guard_index = self.source.index(guard)
        expansion_index = self.source.index("# Expand time windows into individual slots")
        self.assertLess(guard_index, expansion_index)


if __name__ == "__main__":
    unittest.main()
