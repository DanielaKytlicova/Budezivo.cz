import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOKINGS = ROOT / "frontend" / "src" / "pages" / "admin" / "BookingsPage.js"
CALENDAR = ROOT / "frontend" / "src" / "components" / "admin" / "BookingsCalendarView.jsx"


class BookingsPageWhiteScreenGuardTests(unittest.TestCase):
    def test_bookings_page_normalizes_backend_array_like_values(self):
        src = BOOKINGS.read_text()
        self.assertIn("const normalizeIdList", src)
        self.assertIn("const normalizeBooking", src)
        self.assertIn("response.data.map(normalizeBooking)", src)
        self.assertIn("const assignedLecturerIds = normalizeIdList", src)
        self.assertIn("assignedLecturerIds.map", src)

    def test_detail_modal_has_render_error_boundary(self):
        src = BOOKINGS.read_text()
        self.assertIn("class BookingsPageErrorBoundary", src)
        self.assertIn("bookings-render-error", src)
        self.assertIn("resetKey={selectedBooking?.id || 'no-booking'}", src)

    def test_calendar_view_guards_optional_inputs(self):
        src = CALENDAR.read_text()
        self.assertIn("bookings = []", src)
        self.assertIn("safeBookings", src)
        self.assertIn("safeCollisionIndex", src)
        self.assertIn("safeCollisionIndex.has(booking.id)", src)


if __name__ == "__main__":
    unittest.main()
