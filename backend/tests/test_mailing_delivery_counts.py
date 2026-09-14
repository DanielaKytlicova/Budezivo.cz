import unittest

from services.resend_delivery import campaign_delivery_counts


class MailingDeliveryCountsTests(unittest.TestCase):
    def test_resend_acceptance_is_not_counted_as_delivery(self):
        counts = campaign_delivery_counts([
            {"status": "sent", "delivery_status": "sent"},
            {"status": "sent", "delivery_status": "unknown"},
        ])

        self.assertEqual(counts["accepted_count"], 2)
        self.assertEqual(counts["delivered_count"], 0)
        self.assertEqual(counts["awaiting_delivery_count"], 2)

    def test_async_results_replace_misleading_success_count(self):
        recipients = [
            *({"status": "sent", "delivery_status": "delivered"} for _ in range(330)),
            *({"status": "sent", "delivery_status": "bounced_hard"} for _ in range(10)),
            {"status": "sent", "delivery_status": "suppressed"},
        ]

        counts = campaign_delivery_counts(recipients)

        self.assertEqual(counts["accepted_count"], 341)
        self.assertEqual(counts["delivered_count"], 330)
        self.assertEqual(counts["delivery_failed_count"], 11)
        self.assertEqual(counts["awaiting_delivery_count"], 0)

    def test_skipped_and_immediate_failures_are_kept_separate(self):
        counts = campaign_delivery_counts([
            {"status": "failed", "delivery_status": "unknown"},
            {"status": "skipped", "delivery_status": "unknown"},
            {"status": "sent", "delivery_status": "bounced_soft"},
        ])

        self.assertEqual(counts["delivery_failed_count"], 1)
        self.assertEqual(counts["skipped_count"], 1)
        self.assertEqual(counts["awaiting_delivery_count"], 1)


if __name__ == "__main__":
    unittest.main()
