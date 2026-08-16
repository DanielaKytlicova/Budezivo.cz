import unittest
from pathlib import Path


SETTINGS_PAGE = Path(__file__).resolve().parents[2] / "frontend/src/pages/admin/SettingsPage.js"


class NotificationSettingsUiTests(unittest.TestCase):
    def test_mandatory_notification_switch_is_visibly_on_and_explained(self):
        source = SETTINGS_PAGE.read_text()

        self.assertIn("Povinné", source)
        self.assertIn("disabled:opacity-100", source)
        self.assertIn("checked={mandatory ? true : !!checked}", source)
        self.assertIn("if (!mandatory) onChange(value);", source)
        self.assertIn("event_registration_received", source)


if __name__ == "__main__":
    unittest.main()
