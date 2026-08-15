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
        self.assertIn("select(Reservation).where(and_(", text)
        self.assertIn("select(AvailabilityException).where(and_(", text)


if __name__ == "__main__":
    unittest.main()
