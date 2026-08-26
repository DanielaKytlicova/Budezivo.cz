import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AvailabilityBlockRangeProgramTests(unittest.TestCase):
    def test_backend_accepts_date_range_and_multiple_programs(self):
        source = (ROOT / "routes" / "unified_availability.py").read_text(encoding="utf-8")

        self.assertIn("date_from: Optional[str]", source)
        self.assertIn("date_to: Optional[str]", source)
        self.assertIn("program_ids: Optional[List[str]]", source)
        self.assertIn("def _iter_dates", source)
        self.assertIn("for scope_uuid in scope_uuids:", source)
        self.assertIn("for exception_date in dates:", source)

    def test_frontend_program_block_dialog_has_range_and_program_picker(self):
        source = (ROOT.parent / "frontend" / "src" / "pages" / "admin" / "UnifiedAvailabilityPage.js").read_text(encoding="utf-8")

        self.assertIn("date_from", source)
        self.assertIn("date_to", source)
        self.assertIn("programBlockProgramIds", source)
        self.assertIn("pblock-date-from", source)
        self.assertIn("pblock-date-to", source)
        self.assertIn("pblock-programs-trigger", source)
        self.assertIn("program_ids: programBlockProgramIds", source)


if __name__ == "__main__":
    unittest.main()
