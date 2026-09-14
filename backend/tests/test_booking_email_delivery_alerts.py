from pathlib import Path
import unittest
import uuid

from database.models import ResendWebhookEvent
from database.supabase_repositories import EmailLogRepositorySupabase
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
        self.assertIn("{ key: 'email_delivery', label: 'Nedoručené e-maily' }", source)
        self.assertIn("filtered = filtered.filter(b => b.email_delivery_alert)", source)
        self.assertIn("Ověřit nebo opravit e-mail", source)

    def test_transactional_status_is_kept_out_of_campaign_counts(self):
        source = (ROOT / "backend/services/resend_delivery.py").read_text()

        self.assertIn("select(EmailLog).where(EmailLog.email_id == provider_email_id)", source)
        self.assertIn("matched_transactional", source)
        self.assertNotIn("matched_logs", source[source.index("def campaign_delivery_counts"):source.index("def parse_datetime")])


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeSession:
    def __init__(self, existing_event):
        self.existing_event = existing_event
        self.added = None

    async def execute(self, _statement):
        return _ScalarResult(self.existing_event)

    def add(self, value):
        self.added = value

    async def commit(self):
        pass

    async def refresh(self, _value):
        pass


class EmailLogWebhookRaceTests(unittest.IsolatedAsyncioTestCase):
    async def test_email_log_recovers_bounce_received_before_log_creation(self):
        session = _FakeSession(ResendWebhookEvent(event_type="email.bounced"))
        repository = EmailLogRepositorySupabase(session)

        await repository.create({
            "institution_id": str(uuid.uuid4()),
            "program_id": str(uuid.uuid4()),
            "reservation_id": str(uuid.uuid4()),
            "recipient_email": "bounced@resend.dev",
            "subject": "reservation_created_customer",
            "status": "sent",
            "email_id": "provider-message-id",
        })

        self.assertEqual(session.added.status, "bounced_hard")
        self.assertEqual(session.added.error_message, "Nedoručeno")


if __name__ == "__main__":
    unittest.main()
