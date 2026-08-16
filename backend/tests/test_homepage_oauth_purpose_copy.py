import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class HomepageOAuthPurposeCopyTests(unittest.TestCase):
    def test_homepage_explains_app_purpose_for_google_review(self):
        text = (ROOT / "frontend/src/pages/public/HomePage.js").read_text()
        self.assertIn('data-testid="oauth-purpose-section"', text)
        self.assertIn("Rezervační a provozní systém pro kulturní instituce", text)
        self.assertIn("spravovat vzdělávací programy", text)
        self.assertIn("školní rezervace", text)

    def test_homepage_explains_google_calendar_connection(self):
        text = (ROOT / "frontend/src/pages/public/HomePage.js").read_text()
        self.assertIn('data-testid="oauth-calendar-purpose"', text)
        self.assertIn("Proč se aplikace připojuje ke kalendáři", text)
        self.assertIn("Google Kalendář", text)
        self.assertIn("hlídat kolize rezervací", text)
        self.assertIn('to="/gdpr"', text)
        self.assertIn('to="/terms"', text)

    def test_homepage_places_oauth_explanation_after_calendar_integration(self):
        text = (ROOT / "frontend/src/pages/public/HomePage.js").read_text()
        calendar_index = text.index("Kalendáře, které už používáte")
        purpose_index = text.index('data-testid="oauth-purpose-section"')
        faq_index = text.index("{t('faq.title')}")
        self.assertLess(calendar_index, purpose_index)
        self.assertLess(purpose_index, faq_index)


if __name__ == "__main__":
    unittest.main()
