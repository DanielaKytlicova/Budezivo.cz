from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class AdminBookingsRenderGuardV2Tests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text()

    def test_booking_page_wraps_list_and_calendar_render(self):
        source = self.read("frontend/src/pages/admin/BookingsPage.js")
        self.assertIn("const BookingsPageContent = () =>", source)
        self.assertIn('resetKey="bookings-page-root"', source)
        self.assertIn("const peers = Array.isArray(info?.peers) ? info.peers : [];", source)
        self.assertIn("const active = bookings.filter(b => b.id && b.date", source)

    def test_detail_optional_widgets_are_isolated(self):
        source = self.read("frontend/src/pages/admin/BookingsPage.js")
        self.assertIn("resetKey={`reminder-${selectedBooking.id}`}", source)
        self.assertIn("resetKey={`calendar-menu-${selectedBooking.id}`}", source)

    def test_calendar_menu_tolerates_invalid_date_data(self):
        source = self.read("frontend/src/components/calendar/calendarUtils.js")
        self.assertIn("if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(dateValue)) return null;", source)
        self.assertIn("Number.isNaN(start.getTime())", source)
        menu = self.read("frontend/src/components/calendar/AddToCalendarMenu.jsx")
        self.assertIn("if (!booking?.id) return null;", menu)
        self.assertIn("try {", menu)

    def test_calendar_view_skips_malformed_bookings(self):
        source = self.read("frontend/src/components/admin/BookingsCalendarView.jsx")
        self.assertIn("if (!booking.id || !booking.date) return;", source)
        self.assertIn("booking = {}", source)
        self.assertIn("onSelect = () => {}", source)


if __name__ == "__main__":
    unittest.main()
