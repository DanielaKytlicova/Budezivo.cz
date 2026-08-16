import unittest
from pathlib import Path


EVENTS_ROUTE = Path(__file__).resolve().parents[1] / "routes/events.py"


class EventRegistrationConfirmationEmailTests(unittest.TestCase):
    def test_registration_receipt_is_sent_without_notification_preference_gate(self):
        source = EVENTS_ROUTE.read_text()
        start = source.index("# Confirmation email")
        end = source.index('    return resp', start)
        block = source[start:end]

        self.assertIn("email_valid", block)
        self.assertIn("await trigger_event_application_confirmation(", block)
        self.assertNotIn("event_registration_received", block)
        self.assertNotIn("notification_settings", block)


if __name__ == "__main__":
    unittest.main()
