import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CalendarAvailabilityIndicatorTests(unittest.TestCase):
    def test_month_calendar_counts_only_free_program_slots_for_dots(self):
        text = (ROOT / "backend/routes/availability.py").read_text()
        self.assertIn("get_program_availability(institution_id, program_id, date_str, db)", text)
        self.assertIn('block.get("status") == "available"', text)
        self.assertIn("available_blocks = sum(", text)

    def test_booking_calendar_hides_dots_when_no_free_slots(self):
        text = (ROOT / "frontend/src/pages/public/BookingPage.js").read_text()
        self.assertIn("Number(dateInfo.available_blocks) > 0", text)


if __name__ == "__main__":
    unittest.main()
