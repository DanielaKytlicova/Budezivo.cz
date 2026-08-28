from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PROGRAMS_PAGE = ROOT / "frontend" / "src" / "pages" / "admin" / "ProgramsPage.js"


class ProgramRequiredDescriptionUiTests(unittest.TestCase):
    def test_description_uses_same_required_field_error_ui(self):
        source = PROGRAMS_PAGE.read_text(encoding="utf-8")

        self.assertIn("description_cs: 'Vyplňte popis programu.'", source)
        self.assertIn("errors.description_cs = PROGRAM_REQUIRED_FIELD_ERRORS.description_cs", source)
        self.assertIn("clearFieldError('description_cs')", source)
        self.assertIn("fieldErrors.description_cs ? FIELD_ERROR_CLASS : ''", source)
        self.assertIn("aria-invalid={Boolean(fieldErrors.description_cs)}", source)
        self.assertIn("<FieldError message={fieldErrors.description_cs} />", source)

    def test_api_validation_errors_are_mapped_to_visible_program_fields(self):
        source = PROGRAMS_PAGE.read_text(encoding="utf-8")

        self.assertIn("Array.isArray(detail)", source)
        self.assertIn("PROGRAM_REQUIRED_FIELD_ERRORS[field]", source)
        self.assertIn("setFieldErrors(prev => ({ ...prev, ...apiFieldErrors }))", source)
        self.assertIn("toast.error('Zkontrolujte zvýrazněná pole.')", source)


if __name__ == "__main__":
    unittest.main()
