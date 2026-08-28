from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PilotEventsUrlAndMailingPreviewTests(unittest.TestCase):
    def test_public_events_page_filters_single_event_url(self):
        source = (ROOT / "frontend/src/pages/public/PublicEventsPage.js").read_text()

        self.assertIn("new URLSearchParams(window.location.search).get('event')", source)
        self.assertIn("loadedEvents.filter(ev => ev.id === eventId)", source)

    def test_mailing_preview_school_email_fallback_matches_contact_shape(self):
        source = (ROOT / "backend/services/mailing_service.py").read_text()

        self.assertIn('school_contacts = [{', source)
        self.assertIn('"email": school.email', source)
        self.assertNotIn("FakeContact", source)


if __name__ == "__main__":
    unittest.main()
