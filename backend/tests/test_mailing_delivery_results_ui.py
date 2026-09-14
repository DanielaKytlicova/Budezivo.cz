from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class MailingDeliveryResultsUiTests(unittest.TestCase):
    def test_campaign_detail_separates_provider_acceptance_from_delivery(self):
        source = (ROOT / "frontend/src/pages/admin/MailingsPage.js").read_text()

        self.assertIn("{c.accepted_count}", source)
        self.assertIn("Přijato Resendem", source)
        self.assertIn("{c.delivered_count}", source)
        self.assertIn("Doručeno", source)
        self.assertIn("{c.delivery_failed_count}", source)
        self.assertIn("Nedoručeno", source)
        self.assertIn("{c.awaiting_delivery_count}", source)
        self.assertIn("Přijetí Resendem ještě neznamená doručení příjemci", source)

    def test_lecturer_profile_navigation_is_named_availability(self):
        for relative_path in (
            "frontend/src/components/layout/AdminLayout.js",
            "frontend/src/pages/admin/SettingsPage.js",
        ):
            source = (ROOT / relative_path).read_text()
            self.assertIn("label: 'Dostupnost'", source)
            self.assertNotIn("label: 'Lektorský profil'", source)


if __name__ == "__main__":
    unittest.main()
