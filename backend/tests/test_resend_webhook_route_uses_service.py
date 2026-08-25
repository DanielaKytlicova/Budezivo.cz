import unittest
from pathlib import Path


ROUTE = Path(__file__).resolve().parents[1] / "routes/resend_webhooks.py"


class ResendWebhookRouteUsesServiceTests(unittest.TestCase):
    def test_route_delegates_persistence_to_delivery_service(self):
        source = ROUTE.read_text()
        route_body = source[source.index("@router.post"):]

        self.assertIn("apply_delivery_update", source)
        self.assertIn('return await apply_delivery_update(db, delivery_update, headers["svix-id"])', route_body)
        self.assertNotIn("ResendWebhookEvent(", route_body)
        self.assertNotIn("MailingCampaignRecipient", route_body)
        self.assertNotIn("PERMANENT_SUPPRESSION", route_body)


if __name__ == "__main__":
    unittest.main()
