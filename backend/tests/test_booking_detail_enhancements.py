from pathlib import Path
import sys
import unittest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.google_calendar_helpers import build_export_event_body


ROOT = Path(__file__).resolve().parents[2]
BOOKINGS_PAGE = (ROOT / "frontend/src/pages/admin/BookingsPage.js").read_text(encoding="utf-8")
PUBLIC_BOOKING_PAGE = (ROOT / "frontend/src/pages/public/BookingPage.js").read_text(encoding="utf-8")
CALENDAR_UTILS = (ROOT / "frontend/src/components/calendar/calendarUtils.js").read_text(encoding="utf-8")
BOOKING_ROUTES = (ROOT / "backend/routes/bookings.py").read_text(encoding="utf-8")


class BookingDetailEnhancementTests(unittest.TestCase):
    def test_public_program_card_renders_every_target_group(self):
        self.assertIn("...(program.target_groups || [])", PUBLIC_BOOKING_PAGE)
        self.assertIn(".map(({ group, label })", PUBLIC_BOOKING_PAGE)
        self.assertIn("key={group}", PUBLIC_BOOKING_PAGE)

    def test_confirmed_booking_can_be_cancelled_with_typed_guard(self):
        self.assertIn('data-testid="cancel-confirmed-booking-modal"', BOOKINGS_PAGE)
        self.assertIn('data-testid="cancel-confirmation-input"', BOOKINGS_PAGE)
        self.assertIn("toLocaleLowerCase('cs-CZ') !== 'zrušit'", BOOKINGS_PAGE)
        self.assertIn('data-testid="confirm-cancellation"', BOOKINGS_PAGE)

    def test_confirmation_response_is_sent_with_status_update(self):
        self.assertIn('data-testid="toggle-confirmation-response"', BOOKINGS_PAGE)
        self.assertIn('data-testid="confirmation-response"', BOOKINGS_PAGE)
        self.assertIn("confirmation_response: status === 'confirmed'", BOOKINGS_PAGE)
        self.assertIn("confirmation_response=(payload.confirmation_response", BOOKING_ROUTES)

    def test_calendar_deep_links_include_class(self):
        self.assertIn("booking.age_or_class && `Třída: ${booking.age_or_class}`", CALENDAR_UTILS)

    def test_connected_calendar_export_includes_class(self):
        body = build_export_event_body(
            booking_id="booking-1",
            institution_id="institution-1",
            user_id="user-1",
            program_name="Program",
            status="confirmed",
            date_str="2026-10-20",
            time_block="09:00-10:00",
            duration=60,
            institution_name="Instituce",
            room_name=None,
            school_name="ZŠ Test",
            group_type="school",
            age_or_class="4. A",
            num_students=24,
            admin_base_url="https://www.budezivo.cz",
        )

        self.assertIn("Třída: 4. A", body["description"])


if __name__ == "__main__":
    unittest.main()
