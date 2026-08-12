import unittest

from scripts import regression_core_seed


class RegressionCoreSeedTests(unittest.TestCase):
    def test_expected_seed_tables_cover_core_flow(self):
        expected = regression_core_seed.expected_seed_counts()
        self.assertEqual(expected["institutions"], 1)
        self.assertEqual(expected["users"], 2)
        self.assertEqual(expected["programs"], 1)
        self.assertEqual(expected["reservations"], 1)
        self.assertEqual(expected["events"], 1)
        self.assertEqual(expected["event_dates"], 1)
        self.assertEqual(expected["mailing_campaigns"], 1)

    def test_generated_password_is_runtime_only(self):
        one = regression_core_seed.generated_admin_password()
        two = regression_core_seed.generated_admin_password()
        self.assertNotEqual(one, two)
        self.assertGreaterEqual(len(one), 20)
        self.assertTrue(one.startswith("Rg-"))

    def test_admin_email_is_test_domain(self):
        self.assertTrue(regression_core_seed.ADMIN_EMAIL.endswith("@example.test"))
        self.assertTrue(regression_core_seed.CASHIER_EMAIL.endswith("@example.test"))
        self.assertTrue(regression_core_seed.SCHOOL_EMAIL.endswith("@example.test"))


if __name__ == "__main__":
    unittest.main()
