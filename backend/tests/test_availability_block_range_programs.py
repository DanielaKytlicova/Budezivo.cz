import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AvailabilityBlockRangeProgramTests(unittest.TestCase):
    def test_backend_accepts_date_range_and_multiple_programs(self):
        source = (ROOT / "routes" / "unified_availability.py").read_text(encoding="utf-8")

        self.assertIn("date_from: Optional[str]", source)
        self.assertIn("date_to: Optional[str]", source)
        self.assertIn("program_ids: Optional[List[str]]", source)
        self.assertIn("repeat_weekdays: Optional[List[int]]", source)
        self.assertIn("def _iter_dates", source)
        self.assertIn("def _filter_dates_by_weekdays", source)
        self.assertIn("for scope_uuid in scope_uuids:", source)
        self.assertIn("for exception_date in dates:", source)

    def test_frontend_program_block_dialog_has_range_and_program_picker(self):
        source = (ROOT.parent / "frontend" / "src" / "pages" / "admin" / "UnifiedAvailabilityPage.js").read_text(encoding="utf-8")

        self.assertIn("date_from", source)
        self.assertIn("date_to", source)
        self.assertIn("programBlockProgramIds", source)
        self.assertIn("repeat_weekdays", source)
        self.assertIn("pblock-date-from", source)
        self.assertIn("pblock-date-to", source)
        self.assertIn("pblock-recurring-toggle", source)
        self.assertIn("pblock-weekdays", source)
        self.assertIn("pblock-programs-trigger", source)
        self.assertIn("program_ids: programBlockProgramIds", source)
        self.assertIn("repeat_weekdays: programBlockForm.recurring", source)

    def test_backend_date_range_uses_plain_calendar_days(self):
        source = (ROOT / "routes" / "unified_availability.py").read_text(encoding="utf-8")

        self.assertIn("days = (date_to - date_from).days + 1", source)
        self.assertIn("return [(date_from + timedelta(days=i)).isoformat() for i in range(days)]", source)
        self.assertNotIn(".astimezone(", source)
        self.assertNotIn("toordinal()", source)

    def test_frontend_uses_local_date_arithmetic_for_grouping(self):
        source = (ROOT.parent / "frontend" / "src" / "pages" / "admin" / "UnifiedAvailabilityPage.js").read_text(encoding="utf-8")

        self.assertIn("function shiftDateStr(dateStr, days)", source)
        self.assertIn("const nextDateStr = (dateStr) => shiftDateStr(dateStr, 1)", source)
        self.assertNotIn('new Date(`${dateStr}T00:00:00`)', source)


if __name__ == "__main__":
    unittest.main()
