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

    def test_event_applications_offer_payment_filter_and_cash_quick_action(self):
        source = (ROOT / "frontend/src/pages/admin/EventsPage.js").read_text()

        self.assertIn('application-payment-filter-awaiting', source)
        self.assertIn("const MARK_PAID_ROLES = ['admin', 'spravce', 'ucetni', 'pokladni']", source)
        self.assertIn("app.payment_method === 'cash'", source)
        self.assertIn('data-testid={`quick-mark-paid-${app.id}`}', source)
        self.assertIn("updateApplicationStatus(app.id, null, 'paid')", source)


if __name__ == "__main__":
    unittest.main()
