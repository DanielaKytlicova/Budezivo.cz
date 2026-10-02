import os
import sys
import unicodedata
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from config.email_config import EmailType, get_sender_for_email_type
from templates.emails import get_template


RESERVATION_DATA = {
    "institution_name": "Galerie Test",
    "institution_email": "info@example.test",
    "institution_phone": "+420 600 111 222",
    "institution_address": "Testovaci 1, Praha",
    "program_name": "Atelier svetla",
    "program_pricing_info": "120 Kc / zak",
    "reservation_date": "24. 08. 2026",
    "reservation_time": "09:00-10:00",
    "school_name": "ZS Testovaci",
    "children_count": 18,
    "teachers_count": 2,
    "teacher_name": "Jana Novakova",
    "teacher_email": "jana@example.test",
    "teacher_phone": "+420 600 222 333",
    "cancellation_reason": "Nemoc ve tride",
    "rejection_reason": "Kapacita je obsazena",
    "booking_url": "https://www.budezivo.cz/booking/test",
    "google_calendar_url": "https://calendar.google.com/test",
    "outlook_calendar_url": "https://outlook.live.com/test",
    "original_date": "23. 08. 2026",
    "original_time": "10:00-11:00",
}

EVENT_DATA = {
    "institution_name": "Galerie Test",
    "event_name": "Vecerni komentovana prohlidka",
    "applicant_name": "Jan Novak",
    "date_label": "24. 08. 2026, 17:00",
    "status": "confirmed",
    "price": 240,
    "currency": "Kc",
    "variable_symbol": "20260001",
    "payment_relevant": True,
    "is_free": False,
    "payment_method": "qr",
    "account_number": "123456789",
    "bank_code": "0800",
    "account_name": "Galerie Test",
}


def ascii_text(value):
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


class PilotTransactionalEmailTemplateTests(unittest.TestCase):
    def assert_template_renders(self, template_name, data, expected_text):
        rendered = get_template(template_name, data)
        for key in ("subject", "html", "text"):
            self.assertIn(key, rendered)
            self.assertTrue(rendered[key].strip(), f"{template_name} {key} is empty")

        combined = "\n".join(rendered.values())
        self.assertIn(expected_text, ascii_text(combined))
        self.assertNotIn("{{", combined)
        self.assertNotIn("}}", combined)
        self.assertNotIn("None", combined)

    def test_reservation_lifecycle_templates_render(self):
        for template_name, expected_text in (
            ("reservation_confirmed", "Rezervace potvrzena"),
            ("reservation_updated", "Rezervace byla aktualizovana"),
            ("reservation_cancelled", "Rezervace byla zrusena"),
            ("reservation_rescheduled", "Termin rezervace byl zmenen"),
            ("reservation_reminder_teacher", "Pripominka rezervace"),
        ):
            with self.subTest(template_name=template_name):
                self.assert_template_renders(template_name, RESERVATION_DATA, expected_text)

    def test_confirmation_has_no_unsolicited_arrival_instruction(self):
        rendered = get_template("reservation_confirmed", RESERVATION_DATA)

        self.assertNotIn("Dostavte se prosím 10 minut", rendered["html"])
        self.assertNotIn("V případě nemoci nás kontaktujte 2 dny předem", rendered["html"])
        self.assertNotIn("Dostavte se prosím 10 minut", rendered["text"])

    def test_saved_program_template_is_used_only_for_confirmation(self):
        routes = (BACKEND_ROOT / "routes/bookings.py").read_text()
        creation_flow = routes.split("async def create_public_booking", 1)[1].split(
            '@router.get("", response_model=List[Booking])', 1
        )[0]
        status_flow = routes.split("async def update_booking_status", 1)[1].split(
            '@router.put("/{booking_id}")', 1
        )[0]

        self.assertNotIn("find_by_program", creation_flow)
        self.assertIn("email_template = await template_repo.find_by_program", status_flow)
        self.assertIn("email_template=email_template", status_flow)

        mailing_ui = (
            BACKEND_ROOT.parent / "frontend/src/components/admin/ProgramMailingTab.jsx"
        ).read_text()
        send_test = mailing_ui.split("const handleSendTest", 1)[1].split(
            "if (loading)", 1
        )[0]
        self.assertLess(
            send_test.index("axios.put"),
            send_test.index("email-template/test"),
        )

    def test_public_event_templates_render(self):
        for template_name, expected_text in (
            ("event_application_confirmation", "Registrace byla potvrzena"),
            ("event_payment_reminder", "Pripomenuti platby"),
        ):
            with self.subTest(template_name=template_name):
                self.assert_template_renders(template_name, EVENT_DATA, expected_text)

    def test_teacher_reminder_does_not_ask_for_confirmed_participant_count(self):
        rendered = get_template("reservation_reminder_teacher", RESERVATION_DATA)

        for content in (rendered["html"], rendered["text"]):
            self.assertNotIn("potvrzený počet účastníků", content)
        self.assertIn("Dostavte se 10 minut před začátkem", rendered["html"])

    def test_forgot_password_response_does_not_disclose_registered_accounts(self):
        auth_source = (BACKEND_ROOT / "routes/auth.py").read_text()
        page_source = (BACKEND_ROOT.parent / "frontend/src/pages/public/ForgotPasswordPage.js").read_text()
        translations = (BACKEND_ROOT.parent / "frontend/src/i18n/cs.json").read_text()
        public_message = 'return {"message": "If email exists, password reset link has been sent"}'

        self.assertEqual(auth_source.count(public_message), 2)
        self.assertIn("auth.forgotPassword.success", page_source)
        self.assertIn("Pokud účet s tímto e-mailem existuje", translations)

    def test_reservation_sender_mapping_uses_reservation_sender(self):
        for email_type in (
            EmailType.RESERVATION_CREATED_TEACHER,
            EmailType.RESERVATION_CREATED_INSTITUTION,
            EmailType.RESERVATION_CONFIRMED,
            EmailType.RESERVATION_REJECTED,
            EmailType.RESERVATION_UPDATED,
            EmailType.RESERVATION_CANCELLED,
            EmailType.RESERVATION_REMINDER_TEACHER,
            EmailType.RESERVATION_REMINDER_INSTITUTION,
        ):
            with self.subTest(email_type=email_type.value):
                sender = get_sender_for_email_type(email_type)
                self.assertIn("reservations@budezivo.cz", sender)


if __name__ == "__main__":
    unittest.main()
