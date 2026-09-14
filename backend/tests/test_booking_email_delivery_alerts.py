from pathlib import Path
import unittest

from services.resend_delivery import transactional_delivery_alert


ROOT = Path(__file__).resolve().parents[2]


class BookingEmailDeliveryAlertTests(unittest.TestCase):
    def test_permanent_failure_for_current_address_creates_alert(self):
        alert = transactional_delivery_alert(
            [{
                "recipient_email": "teacher@example.cz",
                "status": "bounced_hard",
                "error_message": "Mailbox does not exist",
            }],
            " Teacher@Example.cz ",
        )

        self.assertEqual(alert["status"], "bounced_hard")

    def test_temporary_delay_does_not_create_alert(self):
        alert = transactional_delivery_alert(
            [{"recipient_email": "teacher@example.cz", "status": "bounced_soft"}],
            "teacher@example.cz",
        )

        self.assertIsNone(alert)

    def test_failure_for_old_address_does_not_mark_corrected_address(self):
        alert = transactional_delivery_alert(
            [{"recipient_email": "old@example.cz", "status": "suppressed"}],
            "new@example.cz",
        )

        self.assertIsNone(alert)

    def test_booking_ui_shows_detail_and_list_warnings(self):
        source = (ROOT / "frontend/src/pages/admin/BookingsPage.js").read_text()

        self.assertIn('data-testid="booking-email-delivery-alert"', source)
        self.assertIn('data-testid="verify-booking-email-btn"', source)
        self.assertIn('data-testid={`booking-email-alert-${booking.id}`}', source)
        self.assertIn("Ověřit nebo opravit e-mail", source)

    def test_transactional_status_is_kept_out_of_campaign_counts(self):
        source = (ROOT / "backend/services/resend_delivery.py").read_text()

        self.assertIn("select(EmailLog).where(EmailLog.email_id == provider_email_id)", source)
        self.assertIn("matched_transactional", source)
        self.assertNotIn("matched_logs", source[source.index("def campaign_delivery_counts"):source.index("def parse_datetime")])


if __name__ == "__main__":
    unittest.main()
