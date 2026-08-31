import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LecturerTimeOffRecurringBlocksTests(unittest.TestCase):
    def test_backend_time_off_accepts_weekday_filter(self):
        schema_source = (ROOT / "models" / "schemas.py").read_text(encoding="utf-8")
        route_source = (ROOT / "routes" / "lecturer_availability.py").read_text(encoding="utf-8")

        self.assertIn("repeat_weekdays: Optional[List[int]]", schema_source)
        self.assertIn("def _iter_date_range", route_source)
        self.assertIn("def _filter_dates_by_weekdays", route_source)
        self.assertIn("data.repeat_weekdays", route_source)
        self.assertIn("for block_date in dates:", route_source)
        self.assertIn("start_date=block_date", route_source)
        self.assertIn("end_date=block_date", route_source)

    def test_frontend_time_off_dialog_has_recurring_controls(self):
        source = (
            ROOT.parent
            / "frontend"
            / "src"
            / "pages"
            / "admin"
            / "LecturerAvailabilityPage.js"
        ).read_text(encoding="utf-8")

        self.assertIn("recurring: false", source)
        self.assertIn("repeat_weekdays: []", source)
        self.assertIn("toggleTimeOffWeekday", source)
        self.assertIn("timeoff-recurring-toggle", source)
        self.assertIn("timeoff-weekdays", source)
        self.assertIn("repeat_weekdays: timeOffForm.recurring", source)
        self.assertIn("Vyberte alespoň jeden den opakování.", source)


if __name__ == "__main__":
    unittest.main()
