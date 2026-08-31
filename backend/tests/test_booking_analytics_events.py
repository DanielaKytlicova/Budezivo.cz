import unittest
from pathlib import Path

from services.booking_analytics import (
    classify_booking_blocked,
    classify_booking_failed,
    record_booking_event,
    safe_metadata,
    safe_session_id,
)


ROOT = Path(__file__).resolve().parents[1]


class FakeFailingDb:
    def __init__(self):
        self.added = []
        self.rolled_back = False

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        raise RuntimeError("analytics storage is temporarily unavailable")

    async def rollback(self):
        self.rolled_back = True


class BookingAnalyticsEventTests(unittest.IsolatedAsyncioTestCase):
    def test_safe_metadata_strips_pii(self):
        clean = safe_metadata({
            "contact_email": "teacher@example.com",
            "school_name": "Sensitive school",
            "status_code": 500,
            "error_type": "IntegrityError",
        })
        self.assertEqual(clean, {"status_code": 500, "error_type": "IntegrityError"})

    def test_session_id_is_anonymous_shape_only(self):
        self.assertEqual(safe_session_id("abc12345-xyz"), "abc12345-xyz")
        self.assertIsNone(safe_session_id("teacher@example.com"))

    def test_blocked_and_failed_are_classified_separately(self):
        self.assertEqual(
            classify_booking_blocked({"code": "ROOM_TAKEN", "source": "room"}),
            "room_conflict",
        )
        self.assertEqual(
            classify_booking_blocked("Kapacita souběžných rezervací programu je vyčerpaná"),
            "program_concurrency_limit",
        )
        self.assertEqual(
            classify_booking_blocked("Rezervace tohoto programu se spustí až 01.09.2026 08:00."),
            "booking_not_open_yet",
        )
        self.assertEqual(classify_booking_failed({"field": "date"}, 400), "validation_error")
        self.assertEqual(classify_booking_failed({}, 500), "server_error")

    async def test_analytics_write_failure_is_non_blocking(self):
        db = FakeFailingDb()
        recorded = await record_booking_event(
            db,
            "booking_completed",
            institution_id="not-a-uuid",
            program_id="not-a-uuid",
            session_id="session-12345",
            metadata={"contact_name": "Do not store", "status": "pending"},
        )
        self.assertFalse(recorded)
        self.assertTrue(db.rolled_back)

    def test_backend_route_records_minimal_public_booking_events(self):
        source = (ROOT / "routes" / "bookings.py").read_text(encoding="utf-8")
        self.assertIn('"booking_blocked"', source)
        self.assertIn('"booking_failed"', source)
        self.assertIn('"booking_completed"', source)
        self.assertIn('"reservation_created"', source)
        self.assertIn("BOOKING_SESSION_HEADER", source)
        self.assertNotIn("await record_booking_event", source)

    def test_frontend_tracks_anonymous_session_without_pii_payload(self):
        source = (ROOT.parent / "frontend" / "src" / "pages" / "public" / "BookingPage.js").read_text(encoding="utf-8")
        self.assertIn("budezivo_booking_session_", source)
        self.assertIn("booking_started", source)
        self.assertIn("booking_submit_attempted", source)
        self.assertIn("X-Booking-Session-Id", source)
        self.assertNotIn("analytics/booking-event`, formData", source)


if __name__ == "__main__":
    unittest.main()
