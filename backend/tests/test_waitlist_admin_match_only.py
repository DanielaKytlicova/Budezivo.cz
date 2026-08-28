from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "backend" / "services" / "waitlist_service.py"
ROUTE = ROOT / "backend" / "routes" / "waitlist.py"
ADMIN_PAGE = ROOT / "frontend" / "src" / "pages" / "admin" / "WaitlistPage.js"
PUBLIC_MODAL = ROOT / "frontend" / "src" / "components" / "public" / "WaitlistModal.js"


class WaitlistAdminMatchOnlyTests(unittest.TestCase):
    def test_freed_slot_hook_never_emails_teachers(self):
        source = SERVICE.read_text(encoding="utf-8")

        self.assertNotIn("EmailService", source)
        self.assertNotIn("send_email", source)
        self.assertNotIn("notify_candidates", source)
        self.assertIn("entry.status = 'matched'", source)
        self.assertIn("mark_matches_for_admin", source)

    def test_matched_status_is_manageable_in_admin_waitlist(self):
        route = ROUTE.read_text(encoding="utf-8")
        admin_page = ADMIN_PAGE.read_text(encoding="utf-8")

        self.assertIn("'matched'", route)
        self.assertIn("matched: { label: 'Uvolněný termín'", admin_page)
        self.assertIn("Kontaktovat náhradníka", admin_page)

    def test_public_waitlist_copy_does_not_promise_automatic_notification(self):
        source = PUBLIC_MODAL.read_text(encoding="utf-8")

        self.assertNotIn("dáme vám vědět", source)
        self.assertIn("instituce váš zájem uvidí", source)


if __name__ == "__main__":
    unittest.main()
