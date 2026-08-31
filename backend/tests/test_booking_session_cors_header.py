import unittest
from pathlib import Path


class BookingSessionCorsHeaderTests(unittest.TestCase):
    def test_booking_session_header_is_allowed_by_cors(self):
        main_source = Path(__file__).resolve().parents[1].joinpath("main.py").read_text(encoding="utf-8")
        self.assertIn('"X-Booking-Session-Id"', main_source)
        self.assertIn('allow_headers=["Authorization", "Content-Type", "Accept", "X-Booking-Session-Id"]', main_source)


if __name__ == "__main__":
    unittest.main()
