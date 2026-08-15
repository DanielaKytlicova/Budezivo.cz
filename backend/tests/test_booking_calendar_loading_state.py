import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class BookingCalendarLoadingStateTests(unittest.TestCase):
    def test_preselected_program_skips_unfiltered_initial_calendar(self):
        text = (ROOT / "frontend/src/pages/public/BookingPage.js").read_text()
        self.assertIn("if (!preselectedProgramId)", text)
        self.assertIn("fetchCalendar(currentYear, currentMonth);", text)

    def test_calendar_fetch_has_loading_state(self):
        text = (ROOT / "frontend/src/pages/public/BookingPage.js").read_text()
        self.assertIn("const [calendarLoading, setCalendarLoading] = useState(false)", text)
        self.assertIn("setCalendarLoading(true)", text)
        self.assertIn("setCalendarLoading(false)", text)
        self.assertIn("Načítám dostupnost termínů", text)
        self.assertIn("opacity-35 pointer-events-none", text)


if __name__ == "__main__":
    unittest.main()
