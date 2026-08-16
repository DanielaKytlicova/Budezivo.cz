import unittest
from pathlib import Path


EXPORT_SERVICE = Path(__file__).resolve().parents[1] / "services/export_service.py"


class ApplicationPdfLayoutLogoTests(unittest.TestCase):
    def setUp(self):
        self.source = EXPORT_SERVICE.read_text()

    def test_application_pdf_tables_use_wrapping_paragraph_cells(self):
        self.assertIn("def _pdf_cell(", self.source)
        self.assertIn("escape(str(value)).replace", self.source)
        self.assertIn("_pdf_kv_rows(applicant_rows", self.source)
        self.assertIn("colWidths=[55*mm, 115*mm]", self.source)

    def test_application_pdf_header_can_include_institution_logo(self):
        self.assertIn("def _resolve_institution_logo_image(", self.source)
        self.assertIn('value.startswith("/api/settings/logo/")', self.source)
        self.assertIn("from services.storage_service import get_object", self.source)
        self.assertIn("def _build_confirmation_header(", self.source)
        self.assertIn("elements.extend(_build_confirmation_header(institution, styles))", self.source)

    def test_logo_failure_does_not_block_pdf_generation(self):
        self.assertIn("Institution logo render failed", self.source)
        self.assertIn("return [name_para, Spacer(1, 2*mm)]", self.source)


if __name__ == "__main__":
    unittest.main()
