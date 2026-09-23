from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ContactsDirectorySeparationTests(unittest.TestCase):
    def test_default_contacts_directory_excludes_school_reservation_source(self):
        service = (ROOT / "backend/services/contact_service.py").read_text(encoding="utf-8")
        self.assertIn("Contact.primary_source.is_(None)", service)
        self.assertIn("Contact.primary_source != 'skolni_rezervace'", service)
        self.assertIn("source_filter == 'all'", service)

    def test_contacts_stats_use_the_same_personal_contact_scope(self):
        routes = (ROOT / "backend/routes/contacts.py").read_text(encoding="utf-8")
        self.assertIn("Contact.primary_source.is_(None)", routes)
        self.assertIn("Contact.primary_source != 'skolni_rezervace'", routes)


if __name__ == "__main__":
    unittest.main()
