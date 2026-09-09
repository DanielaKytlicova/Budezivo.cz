import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOKING_PAGE = ROOT / "frontend" / "src" / "pages" / "public" / "BookingPage.js"


class PublicProgramDisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = BOOKING_PAGE.read_text(encoding="utf-8")

    def test_program_description_preserves_plain_text_line_breaks(self):
        self.assertIn(
            'className="text-gray-600 mb-4 whitespace-pre-line"',
            self.source,
        )
        self.assertNotIn(
            "dangerouslySetInnerHTML={{ __html: program.description_cs }}",
            self.source,
        )

    def test_public_list_filters_programs_to_current_validity_period(self):
        self.assertIn("const isProgramCurrentlyValid = (program", self.source)
        self.assertIn("(!startDate || startDate <= today)", self.source)
        self.assertIn("(!endDate || endDate >= today)", self.source)
        self.assertIn(
            "const currentlyValidPrograms = allPrograms.filter(program => isProgramCurrentlyValid(program));",
            self.source,
        )
        self.assertIn("setPrograms(currentlyValidPrograms);", self.source)

    def test_preselected_program_uses_the_same_validity_filter(self):
        self.assertIn(
            "const preselected = currentlyValidPrograms.find(p => p.id === preselectedProgramId);",
            self.source,
        )
        self.assertNotIn(
            "const preselected = allPrograms.find(p => p.id === preselectedProgramId);",
            self.source,
        )


if __name__ == "__main__":
    unittest.main()
