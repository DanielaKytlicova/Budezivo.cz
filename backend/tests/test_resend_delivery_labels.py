import unittest

from services.resend_delivery import delivery_status_label


class ResendDeliveryLabelsTests(unittest.TestCase):
    def test_known_delivery_status_labels_are_czech_user_labels(self):
        self.assertEqual(delivery_status_label("delivered"), "Doručeno")
        self.assertEqual(delivery_status_label("bounced_hard"), "Nedoručeno")
        self.assertEqual(delivery_status_label("complained"), "Označeno jako spam")

    def test_unknown_delivery_status_has_safe_fallback(self):
        self.assertEqual(delivery_status_label(None), "Neznámý stav")
        self.assertEqual(delivery_status_label("something-new"), "Neznámý stav")


if __name__ == "__main__":
    unittest.main()
