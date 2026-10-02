import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class BookingCalendarMonthPerformanceTests(unittest.TestCase):
    def test_month_calendar_does_not_call_daily_availability_endpoint_per_day(self):
        text = (ROOT / "backend/routes/availability.py").read_text()
        calendar_section = text.split('@router.get("/calendar/{institution_id}/{year}/{month}")', 1)[1]
        self.assertNotIn(
            "get_program_availability(institution_id, program_id, date_str, db)",
            calendar_section,
        )

    def test_month_calendar_uses_batched_reservations_and_exceptions(self):
        text = (ROOT / "backend/routes/availability.py").read_text()
        self.assertIn("reservations_by_date = defaultdict(list)", text)
        self.assertIn("exceptions_by_date = defaultdict(list)", text)
        self.assertIn("preview_snapshot.reservations_by_date.items()", text)
        self.assertIn("preview_snapshot.exceptions_by_date.items()", text)

    def test_month_calendar_uses_one_batched_preview_snapshot(self):
        text = (ROOT / "backend/routes/availability.py").read_text()
        calendar_section = text.split('@router.get("/calendar/{institution_id}/{year}/{month}")', 1)[1]
        self.assertEqual(calendar_section.count("AvailabilityPreviewSnapshot.load("), 1)
        loop_section = calendar_section.split("# Build calendar", 1)[1]
        self.assertIn("preview_snapshot.is_blocked(date_str, slot)", loop_section)
        self.assertIn("not await _slot_has_assignable_main_lecturer(", loop_section)
        self.assertIn("preview_snapshot,", loop_section)


if __name__ == "__main__":
    unittest.main()
