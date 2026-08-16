import unittest
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
EVENTS = BACKEND / "routes/events.py"
EXPORT_SERVICE = BACKEND / "services/export_service.py"


class ApplicationPdfLogoSourceTests(unittest.TestCase):
    def test_pdf_routes_pass_logo_url_to_generator(self):
        source = EVENTS.read_text()
        self.assertIn("async def _application_pdf_institution_data(", source)
        self.assertIn("select(ThemeSetting).where(ThemeSetting.institution_id == inst_uuid)", source)
        self.assertIn('"logo_url": logo_url', source)
        self.assertEqual(source.count("institution_data = await _application_pdf_institution_data(db, inst_uuid)"), 2)
        self.assertEqual(source.count("institution_data,\n        _to_dict(pay_settings)"), 2)

    def test_pdf_logo_resolver_handles_absolute_api_urls(self):
        source = EXPORT_SERVICE.read_text()
        self.assertIn("def _storage_logo_path_from_url(", source)
        self.assertIn("parsed = urlparse(value)", source)
        self.assertIn('prefix = "/api/settings/logo/"', source)
        self.assertIn("storage_path = _storage_logo_path_from_url(value)", source)


if __name__ == "__main__":
    unittest.main()
