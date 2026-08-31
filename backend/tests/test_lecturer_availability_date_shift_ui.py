import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LECTURER_PAGE = ROOT.parent / "frontend" / "src" / "pages" / "admin" / "LecturerAvailabilityPage.js"


class LecturerAvailabilityDateShiftUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = LECTURER_PAGE.read_text(encoding="utf-8")

    def test_personal_time_off_uses_date_only_comparison(self):
        self.assertIn("function dateOnly(value)", self.source)
        self.assertIn("dateOnly(o.specific_date) === dateStr", self.source)
        self.assertIn("const startDate = dateOnly(t.start_date)", self.source)
        self.assertIn("const endDate = dateOnly(t.end_date || t.start_date)", self.source)
        self.assertIn("return startDate <= dateStr && endDate >= dateStr", self.source)

    def test_external_calendar_blocks_do_not_slice_utc_date(self):
        self.assertIn("const bDate = dateOnly(b.start_time)", self.source)
        self.assertNotIn("new Date(b.start_time).toISOString().slice(0, 10)", self.source)


if __name__ == "__main__":
    unittest.main()
