import json
import unittest

from scripts import regression_resend_delivery_smoke


class RegressionResendDeliverySmokeTests(unittest.TestCase):
    def test_expected_checks_are_declared(self):
        checks = regression_resend_delivery_smoke.expected_checks()
        self.assertIn("recipient_marked_bounced", checks)
        self.assertIn("school_contact_marked_invalid", checks)
        self.assertIn("duplicate_is_idempotent", checks)

    def test_payload_uses_test_recipient_only(self):
        payload = regression_resend_delivery_smoke.bounced_payload()
        rendered = json.dumps(payload)
        self.assertIn("@example.test", rendered)
        self.assertNotIn("@budezivo.cz", rendered)

    def test_report_identifiers_do_not_contain_passwords(self):
        self.assertNotIn("password", regression_resend_delivery_smoke.PROVIDER_EMAIL_ID.lower())
        self.assertNotIn("password", regression_resend_delivery_smoke.SVIX_ID.lower())


if __name__ == "__main__":
    unittest.main()
