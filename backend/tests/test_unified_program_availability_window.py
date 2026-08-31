import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AVAILABILITY_SERVICE = ROOT / "services" / "availability_service.py"
BOOKING_WINDOW_SERVICE = ROOT / "services" / "program_booking_window.py"


class UnifiedProgramAvailabilityWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.availability_source = AVAILABILITY_SERVICE.read_text(encoding="utf-8")
        cls.window_source = BOOKING_WINDOW_SERVICE.read_text(encoding="utf-8")

    def test_unified_program_slots_use_shared_booking_window_guard(self):
        self.assertIn(
            "from services.program_booking_window import program_booking_window_message",
            self.availability_source,
        )
        self.assertIn("window_reason = program_booking_window_message(", self.availability_source)
        self.assertIn('"status": STATUS_OUTSIDE_BASE', self.availability_source)

        guard_index = self.availability_source.index(
            "window_reason = program_booking_window_message("
        )
        day_index = self.availability_source.index("day_name = days[date_obj.weekday()]")
        expansion_index = self.availability_source.index("# Expand time blocks")

        self.assertLess(guard_index, day_index)
        self.assertLess(guard_index, expansion_index)

    def test_shared_window_covers_public_program_boundaries(self):
        self.assertIn("booking_opens_message(program, now)", self.window_source)
        self.assertIn("min_days_before_booking", self.window_source)
        self.assertIn("max_days_before_booking", self.window_source)
        self.assertIn('get("start_date")', self.window_source)
        self.assertIn('get("end_date")', self.window_source)


if __name__ == "__main__":
    unittest.main()
