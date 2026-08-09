import unittest

from services.notification_preferences import normalize_notifications


class NotificationPreferencesTest(unittest.TestCase):
    def test_fresh_institution_only_enables_new_reservation_alert(self):
        settings = normalize_notifications(None)

        self.assertTrue(settings["admin"]["new_reservation"])
        self.assertTrue(settings["customer"]["event_registration_received"])
        self.assertFalse(settings["customer"]["reservation_created"])
        self.assertFalse(settings["customer"]["reservation_confirmed"])
        self.assertFalse(settings["customer"]["reservation_cancelled"])
        self.assertFalse(settings["customer"]["visit_reminder"])
        self.assertFalse(settings["admin"]["reservation_cancelled"])

    def test_mandatory_event_receipt_cannot_be_disabled(self):
        settings = normalize_notifications({
            "customer": {"event_registration_received": False},
        })

        self.assertTrue(settings["customer"]["event_registration_received"])

    def test_explicit_existing_choices_are_preserved(self):
        settings = normalize_notifications({
            "customer": {
                "reservation_created": True,
                "visit_reminder": True,
            },
            "admin": {
                "new_reservation": False,
                "reservation_cancelled": True,
                "recipient_user_ids": ["first", "second"],
            },
        })

        self.assertTrue(settings["customer"]["reservation_created"])
        self.assertTrue(settings["customer"]["visit_reminder"])
        self.assertFalse(settings["admin"]["new_reservation"])
        self.assertTrue(settings["admin"]["reservation_cancelled"])
        self.assertEqual(
            settings["admin"]["recipient_user_ids"],
            ["first", "second"],
        )


if __name__ == "__main__":
    unittest.main()
