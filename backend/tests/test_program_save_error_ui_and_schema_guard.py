from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PROGRAMS_PAGE = ROOT / "frontend" / "src" / "pages" / "admin" / "ProgramsPage.js"
MAIN = ROOT / "backend" / "main.py"
PROGRAM_ROUTES = ROOT / "backend" / "routes" / "programs.py"


class ProgramSaveErrorUiAndSchemaGuardTests(unittest.TestCase):
    def test_description_uses_same_required_field_error_ui(self):
        source = PROGRAMS_PAGE.read_text(encoding="utf-8")

        self.assertIn("description_cs: 'Vyplňte popis programu.'", source)
        self.assertIn("errors.description_cs = PROGRAM_REQUIRED_FIELD_ERRORS.description_cs", source)
        self.assertIn("clearFieldError('description_cs')", source)
        self.assertIn("fieldErrors.description_cs ? FIELD_ERROR_CLASS : ''", source)
        self.assertIn("aria-invalid={Boolean(fieldErrors.description_cs)}", source)
        self.assertIn("<FieldError message={fieldErrors.description_cs} />", source)

    def test_program_api_errors_are_mapped_to_visible_fields(self):
        source = PROGRAMS_PAGE.read_text(encoding="utf-8")

        self.assertIn("Array.isArray(detail)", source)
        self.assertIn("PROGRAM_REQUIRED_FIELD_ERRORS[field]", source)
        self.assertIn("detail.field && PROGRAM_REQUIRED_FIELD_ERRORS[detail.field]", source)
        self.assertIn("setFieldErrors(prev => ({ ...prev, ...apiFieldErrors }))", source)
        self.assertIn("toast.error('Zkontrolujte zvýrazněná pole.')", source)

    def test_empty_booking_opens_at_is_sent_as_null(self):
        source = PROGRAMS_PAGE.read_text(encoding="utf-8")

        self.assertIn("booking_opens_at: 'Zadejte platné datum a čas spuštění rezervací.'", source)
        self.assertIn("const dateTimeLocalToISOString = (value) => {\n  if (!value) return null;", source)
        self.assertIn("const dateTimeLocalToISOString = (value) => {\n  if (!value) return null;\n  const date = new Date(value);\n  if (isNaN(date.getTime())) return null;", source)
        self.assertIn("booking_opens_at: dateTimeLocalToISOString(formData.booking_opens_at)", source)
        self.assertNotIn("const dateTimeLocalToISOString = (value) => {\n  if (!value) return '';", source)

    def test_plan_banner_uses_real_plan_limit_and_links_to_plan_page(self):
        source = PROGRAMS_PAGE.read_text(encoding="utf-8")

        self.assertIn("setPlanStatus(response.data || null)", source)
        self.assertIn("const hasProgramLimit =", source)
        self.assertIn("planStatus?.limits?.programs_limit", source)
        self.assertIn("onClick={() => navigate('/admin/plan')}", source)
        self.assertNotIn("freeLimit = 3", source)
        self.assertNotIn("bezúplatný tarif.", source)

    def test_startup_guards_program_schema_used_by_program_save(self):
        source = MAIN.read_text(encoding="utf-8")

        for marker in (
            "ADD COLUMN IF NOT EXISTS pricing_info TEXT",
            "ADD COLUMN IF NOT EXISTS booking_opens_at TIMESTAMPTZ",
            "ADD COLUMN IF NOT EXISTS allow_parallel BOOLEAN DEFAULT FALSE",
            "ADD COLUMN IF NOT EXISTS max_concurrent_bookings INTEGER DEFAULT 1",
            "ALTER COLUMN max_concurrent_bookings DROP NOT NULL",
            "ADD COLUMN IF NOT EXISTS collision_lecturer_ids JSON DEFAULT '[]'::json",
            "ADD COLUMN IF NOT EXISTS required_lecturers INTEGER NOT NULL DEFAULT 1",
        ):
            self.assertIn(marker, source)

    def test_backend_save_error_detail_is_actionable(self):
        source = PROGRAM_ROUTES.read_text(encoding="utf-8")

        self.assertIn("def _program_save_error_detail", source)
        self.assertIn("UndefinedColumnError", source)
        self.assertIn("neaktuálnímu schématu databáze", source)
        self.assertIn("raise HTTPException(status_code=400, detail=_program_save_error_detail(exc))", source)


if __name__ == "__main__":
    unittest.main()
