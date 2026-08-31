import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.email_service import EmailTemplateRenderer


class EmailTemplateVariableAliasesTests(unittest.TestCase):
    def test_program_reservation_editor_variables_are_allowed(self):
        template = """
        Dobrý den, {{contact_person}},
        Rezervace pro {{number_of_students}} žáků a {{number_of_teachers}} pedagogů.
        Program: {{program_name}}
        """

        validation = EmailTemplateRenderer.validate_template(template)

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["unknown_variables"], [])
        self.assertIn("contact_person", validation["variables"])
        self.assertIn("number_of_students", validation["variables"])
        self.assertIn("number_of_teachers", validation["variables"])


if __name__ == "__main__":
    unittest.main()
