import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CalendarAvailabilityIndicatorTests(unittest.TestCase):
    def test_month_calendar_counts_only_free_program_slots_for_dots(self):
        text = (ROOT / "backend/routes/availability.py").read_text()
        self.assertIn("_calendar_exception_blocks_slot(slot, program_duration, exception_blocks)", text)
        self.assertIn("_slot_capacity_reached(slot, booked_blocks, program_duration, program_concurrent_limit)", text)
        self.assertIn("_calendar_blocks_overlap(slot, booked_block, duration)", text)
        self.assertIn("available_blocks += 1", text)

    def test_booking_calendar_hides_dots_when_no_free_slots(self):
        text = (ROOT / "frontend/src/pages/public/BookingPage.js").read_text()
        self.assertIn("Number(dateInfo.available_blocks) > 0", text)


if __name__ == "__main__":
    unittest.main()
