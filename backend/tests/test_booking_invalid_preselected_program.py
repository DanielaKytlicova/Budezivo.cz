import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOKING_PAGE = ROOT / "frontend" / "src" / "pages" / "public" / "BookingPage.js"


class BookingInvalidPreselectedProgramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = BOOKING_PAGE.read_text(encoding="utf-8")

    def test_booking_page_waits_for_program_validation_before_calendar_step(self):
        self.assertIn("const [step, setStep] = useState(1);", self.source)
        self.assertIn("Program z odkazu už není dostupný. Vyberte prosím jiný program.", self.source)
        self.assertIn("setFormData(prev => ({ ...prev, program_id: '' }));", self.source)
        self.assertIn("fetchCalendar(currentYear, currentMonth);", self.source)

    def test_time_blocks_are_loaded_with_validated_program_id(self):
        self.assertIn("const fetchTimeBlocks = async (date, programIdOverride = null)", self.source)
        self.assertIn("const programId = programIdOverride || formData.program_id;", self.source)
        self.assertIn("Nejprve vyberte program.", self.source)
        self.assertIn("await fetchTimeBlocks(date, programId);", self.source)


if __name__ == "__main__":
    unittest.main()
