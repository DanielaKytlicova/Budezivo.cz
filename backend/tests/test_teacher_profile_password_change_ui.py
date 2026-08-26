import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PAGE = ROOT / "frontend" / "src" / "pages" / "admin" / "MyProfilePage.js"


class TeacherProfilePasswordChangeUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PROFILE_PAGE.read_text(encoding="utf-8")

    def test_teacher_profile_contains_password_change_form(self):
        self.assertIn('data-testid="profile-password-section"', self.source)
        self.assertIn('data-testid="profile-password-current-input"', self.source)
        self.assertIn('data-testid="profile-password-new-input"', self.source)
        self.assertIn('data-testid="profile-password-confirm-input"', self.source)
        self.assertIn('data-testid="profile-change-password-button"', self.source)

    def test_teacher_profile_uses_authenticated_change_password_endpoint(self):
        self.assertIn("axios.post(`${API}/auth/change-password`", self.source)
        self.assertIn("current_password: pwdCurrent", self.source)
        self.assertIn("new_password: pwdNew", self.source)
        self.assertIn("withCredentials: true", self.source)

    def test_teacher_profile_password_validation_matches_settings(self):
        self.assertIn("Heslo musí mít alespoň 8 znaků, velké i malé písmeno a číslici.", self.source)
        self.assertIn("Nové heslo a jeho potvrzení se neshodují.", self.source)
        self.assertIn("Zkontrolujte zvýrazněná pole.", self.source)
        self.assertIn("FIELD_ERROR_CLASS", self.source)


if __name__ == "__main__":
    unittest.main()
