import pathlib
import unittest


SCRIPT = pathlib.Path("backend/scripts/regression_public_booking_concurrency.py")


class PublicBookingConcurrencySmokeTests(unittest.TestCase):
    def test_uses_valid_email_and_test_db_guard(self):
        source = SCRIPT.read_text()

        self.assertIn("require_test_database_url(SCRIPT_NAME)", source)
        self.assertIn("public-booking-race@budezivo.cz", source)
        self.assertNotIn("example.test", source)

    def test_bypasses_only_internal_rate_limit(self):
        source = SCRIPT.read_text()

        self.assertIn("booking_routes._booking_limiter.enabled = False", source)
        self.assertIn('"10,25,50,100"', source)
        self.assertIn("active_count == limit and success == limit", source)


if __name__ == "__main__":
    unittest.main()
