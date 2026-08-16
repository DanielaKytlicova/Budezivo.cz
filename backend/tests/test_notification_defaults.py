import unittest
from pathlib import Path


PREFS = Path(__file__).resolve().parents[1] / "services/notification_preferences.py"


class NotificationDefaultsTests(unittest.TestCase):
    def test_customer_notifications_default_to_enabled(self):
        source = PREFS.read_text()
        block = source[source.index("CUSTOMER_NOTIF_KEYS = {"):source.index("ADMIN_NOTIF_KEYS = {")]

        for key in (
            "reservation_created",
            "reservation_confirmed",
            "reservation_cancelled",
            "visit_reminder",
            "event_registration_received",
            "event_registration_confirmed",
            "event_registration_cancelled",
        ):
            self.assertIn(f'"{key}": True', block)

    def test_event_registration_receipt_is_forced_on(self):
        source = PREFS.read_text()

        self.assertIn('customer["event_registration_received"] = True', source)
        self.assertIn("never be disabled", source)


if __name__ == "__main__":
    unittest.main()
