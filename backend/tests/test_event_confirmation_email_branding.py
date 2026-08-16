import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "backend/templates/emails/templates.py"
EVENTS = ROOT / "backend/routes/events.py"


class EventConfirmationEmailBrandingTests(unittest.TestCase):
    def test_relative_logo_urls_are_made_absolute_for_email_clients(self):
        source = TEMPLATES.read_text()

        self.assertIn("def _absolute_logo_url(", source)
        self.assertIn("https://api.budezivo.cz", source)
        self.assertIn('value.startswith("/api/")', source)

    def test_event_confirmation_email_uses_light_logo_header(self):
        source = TEMPLATES.read_text()

        self.assertIn("prefer_light_logo_header", source)
        self.assertIn('header_bg = "#FFFFFF" if prefer_light_logo_header else theme["secondary_color"]', source)
        self.assertIn("border-bottom: 1px solid #E2E8F0", source)

    def test_event_registration_passes_institution_logo_to_template(self):
        source = EVENTS.read_text()

        self.assertIn('institution_logo_url = getattr(institution, "logo_url", None)', source)
        self.assertIn('"institution_logo_url": institution_logo_url', source)
        self.assertIn('"prefer_light_logo_header": True', source)


if __name__ == "__main__":
    unittest.main()
