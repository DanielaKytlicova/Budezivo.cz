import unittest

from services.resend_delivery import delivery_update_from_payload


class ResendWebhookPayloadTests(unittest.TestCase):
    def test_delivered_event_normalizes_provider_and_recipient(self):
        update = delivery_update_from_payload({
            "type": "email.delivered",
            "created_at": "2026-08-11T10:15:30Z",
            "data": {
                "email_id": "email_123",
                "to": [" ŠKOLA@example.cz "],
            },
        })

        self.assertIsNotNone(update)
        self.assertEqual(update["event_type"], "email.delivered")
        self.assertEqual(update["status"], "delivered")
        self.assertEqual(update["provider_email_id"], "email_123")
        self.assertEqual(update["recipient_email"], "škola@example.cz")
        self.assertIsNotNone(update["event_at"].tzinfo)
        self.assertIsNone(update["reason"])

    def test_hard_bounce_is_permanent_failure(self):
        update = delivery_update_from_payload({
            "type": "email.bounced",
            "data": {
                "id": "email_456",
                "to": "bounce@example.cz",
                "bounce": {
                    "type": "Permanent",
                    "message": "Mailbox does not exist",
                },
            },
        })

        self.assertEqual(update["status"], "bounced_hard")
        self.assertEqual(update["provider_email_id"], "email_456")
        self.assertEqual(update["recipient_email"], "bounce@example.cz")
        self.assertEqual(update["reason"], "Mailbox does not exist")

    def test_transient_bounce_is_soft_failure(self):
        update = delivery_update_from_payload({
            "type": "email.bounced",
            "data": {
                "email_id": "email_789",
                "to": ["delay@example.cz"],
                "bounce": {
                    "type": "Transient",
                    "message": "Mailbox temporarily unavailable",
                },
            },
        })

        self.assertEqual(update["status"], "bounced_soft")
        self.assertEqual(update["reason"], "Mailbox temporarily unavailable")

    def test_complained_and_suppressed_have_user_visible_reasons(self):
        complained = delivery_update_from_payload({
            "type": "email.complained",
            "data": {"email_id": "email_spam", "to": ["spam@example.cz"]},
        })
        suppressed = delivery_update_from_payload({
            "type": "email.suppressed",
            "data": {"email_id": "email_blocked", "to": ["blocked@example.cz"]},
        })

        self.assertEqual(complained["status"], "complained")
        self.assertIn("spam", complained["reason"])
        self.assertEqual(suppressed["status"], "suppressed")
        self.assertIn("suppression", suppressed["reason"])

    def test_unknown_event_is_ignored(self):
        self.assertIsNone(delivery_update_from_payload({
            "type": "email.opened",
            "data": {"email_id": "email_opened", "to": ["reader@example.cz"]},
        }))

    def test_missing_or_unexpected_recipient_shape_does_not_crash(self):
        update = delivery_update_from_payload({
            "type": "email.failed",
            "created_at": "not-a-date",
            "data": {
                "email_id": "email_failed",
                "to": {"email": "broken@example.cz"},
                "reason": "Provider failure",
            },
        })

        self.assertEqual(update["status"], "failed")
        self.assertIsNone(update["recipient_email"])
        self.assertEqual(update["reason"], "Provider failure")
        self.assertIsNotNone(update["event_at"])


if __name__ == "__main__":
    unittest.main()
