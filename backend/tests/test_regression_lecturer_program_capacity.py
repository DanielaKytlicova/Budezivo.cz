import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "regression_lecturer_program_capacity.py"
SOURCE = SCRIPT_PATH.read_text(encoding="utf-8")


class RegressionLecturerProgramCapacityTests(unittest.TestCase):
    def test_refuses_production_database(self):
        self.assertIn('require_test_database_url(SCRIPT_NAME)', SOURCE)
        self.assertIn('configure_sqlalchemy_test_database(SCRIPT_NAME)', SOURCE)
        self.assertIn('SCRIPT_NAME = "regression_lecturer_program_capacity.py"', SOURCE)

    def test_uses_prefixed_isolated_fixtures(self):
        self.assertIn('PREFIX = "[KOLIZE TEST]"', SOURCE)
        self.assertIn('TARGET_INSTITUTION_NAME = "Galerie U Zlatého kohouta"', SOURCE)
        self.assertIn('TARGET_ADMIN_EMAIL = "galerie@budezivo.cz"', SOURCE)
        self.assertIn('DELETE FROM reservations', SOURCE)
        self.assertIn('school_name LIKE', SOURCE)

    def test_fixture_scope_matches_regression_request(self):
        spec = importlib.util.spec_from_file_location("regression_lecturer_program_capacity", SCRIPT_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        self.assertEqual(len(module.LECTURERS), 5)
        self.assertEqual(len(module.ROOMS), 4)
        self.assertEqual(len(module.PROGRAMS), 12)
        self.assertEqual(module.PROGRAMS["P01"]["limit"], 2)
        self.assertEqual(module.PROGRAMS["P02"]["limit"], 1)
        self.assertIn("P09", module.LECTURERS["L3"]["programs"])
        self.assertNotIn("P09", module.LECTURERS["L1"]["programs"])

    def test_real_services_are_exercised(self):
        self.assertIn("check_booking_collision", SOURCE)
        self.assertIn("check_lecturer_collision_for_assignment", SOURCE)
        self.assertIn("evaluate_program_slots", SOURCE)
        self.assertIn("pick_main_lecturer", SOURCE)
        self.assertIn("supported_program_ids", SOURCE)

    def test_scenarios_cover_requested_matrix(self):
        for scenario_id in [f"T{number:02d}" for number in range(1, 13)]:
            self.assertIn(f'"{scenario_id}"', SOURCE)
        self.assertIn('f"T13.{idx}"', SOURCE)
        for scenario_id in [f"T{number:02d}" for number in range(14, 19)]:
            self.assertIn(f'"{scenario_id}"', SOURCE)
        self.assertIn('"S01"', SOURCE)
        self.assertIn("unsupported_lecturer", SOURCE)
        self.assertIn("availability_exception", SOURCE)


if __name__ == "__main__":
    unittest.main()
