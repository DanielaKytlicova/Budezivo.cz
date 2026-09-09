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

    def test_all_public_programs_are_visible_by_default(self):
        self.assertIn("const [validityFilter, setValidityFilter] = useState('all');", self.source)
        self.assertIn("setPrograms(allPrograms);", self.source)
        self.assertNotIn("setPrograms(currentlyValidPrograms);", self.source)

    def test_preselected_future_program_remains_available(self):
        self.assertIn(
            "const preselected = allPrograms.find(p => p.id === preselectedProgramId);",
            self.source,
        )

    def test_validity_filter_can_show_current_upcoming_or_past_programs(self):
        self.assertIn("const programValidityState = (program", self.source)
        self.assertIn("if (startDate && startDate > today) return 'upcoming';", self.source)
        self.assertIn("if (endDate && endDate < today) return 'past';", self.source)
        self.assertIn("programValidityState(p) === validityFilter", self.source)
        self.assertIn('data-testid="filter-validity"', self.source)
        self.assertIn("{ value: 'all', label: 'Všechna období' }", self.source)
        self.assertIn("{ value: 'current', label: 'Aktuálně platné' }", self.source)
        self.assertIn("{ value: 'upcoming', label: 'Budoucí programy' }", self.source)
        self.assertIn("{ value: 'past', label: 'Ukončené programy' }", self.source)
        self.assertIn("{ value: 'range', label: 'Vlastní rozsah' }", self.source)

    def test_custom_range_filters_programs_by_overlapping_validity(self):
        self.assertIn("const programOverlapsDateRange = (program", self.source)
        self.assertIn("programStart <= rangeEnd", self.source)
        self.assertIn("programEnd >= rangeStart", self.source)
        self.assertIn(
            "programOverlapsDateRange(p, validityRangeStart, validityRangeEnd)",
            self.source,
        )
        self.assertIn('data-testid="filter-validity-range"', self.source)
        self.assertIn('data-testid="filter-validity-start"', self.source)
        self.assertIn('data-testid="filter-validity-end"', self.source)


if __name__ == "__main__":
    unittest.main()
