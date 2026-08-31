import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from templates.emails import reservation_confirmed, reservation_created_teacher


RESERVATION_DATA = {
    "institution_name": "Oblastni galerie",
    "institution_email": "rezervace@oblastnigalerie.test",
    "institution_phone": "+420 600 111 222",
    "institution_address": "Testovaci 1",
    "program_name": "Cteme obrazy",
    "reservation_date": "1. 9. 2026",
    "reservation_time": "09:00-10:00",
    "school_name": "ZS Test",
    "children_count": 18,
    "teachers_count": 2,
    "teacher_name": "Jana Novakova",
}


class ReservationEmailInstitutionContactFooterTests(unittest.TestCase):
    def assert_footer_uses_institution_contact(self, rendered):
        self.assertIn("kontaktujte instituci na", rendered["html"])
        self.assertIn("mailto:rezervace@oblastnigalerie.test", rendered["html"])
        self.assertIn("kontaktujte instituci na rezervace@oblastnigalerie.test", rendered["text"])
        self.assertNotIn("kontaktujte nás na info@budezivo.cz", rendered["html"])
        self.assertNotIn("kontaktujte nás na info@budezivo.cz", rendered["text"])

    def test_reservation_created_teacher_footer_uses_institution_contact(self):
        self.assert_footer_uses_institution_contact(reservation_created_teacher(RESERVATION_DATA))

    def test_reservation_confirmed_footer_uses_institution_contact(self):
        self.assert_footer_uses_institution_contact(reservation_confirmed(RESERVATION_DATA))


if __name__ == "__main__":
    unittest.main()
