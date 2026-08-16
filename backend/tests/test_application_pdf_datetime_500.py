import unittest
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
EVENTS = BACKEND / "routes/events.py"
EXPORT_SERVICE = BACKEND / "services/export_service.py"


class ApplicationPdfDatetimeTests(unittest.TestCase):
    def test_format_date_accepts_datetime_objects(self):
        source = EXPORT_SERVICE.read_text()
        self.assertIn("def _format_date(value: Any) -> str:", source)
        self.assertIn("isinstance(value, datetime)", source)
        self.assertIn("text = str(value)", source)

    def test_pdf_endpoint_retries_without_optional_sections(self):
        source = EVENTS.read_text()
        self.assertEqual(source.count("Application PDF generation failed, retrying without optional sections"), 2)
        self.assertEqual(source.count('{"name": institution_data.get("name", "Instituce")}'), 2)
        self.assertEqual(source.count("buffer = generate_pdf_confirmation("), 4)
        self.assertEqual(source.count("_to_dict(pay_settings) if pay_settings else None"), 2)


if __name__ == "__main__":
    unittest.main()
