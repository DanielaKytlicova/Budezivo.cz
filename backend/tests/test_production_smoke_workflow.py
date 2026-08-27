from pathlib import Path
import unittest


class ProductionSmokeWorkflowTests(unittest.TestCase):
    def test_pilot_booking_path_is_checked_by_scheduled_smoke(self):
        workflow = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "production-smoke.yml"
        source = workflow.read_text(encoding="utf-8")

        self.assertIn("PILOT_BOOKING_PATHS", source)
        self.assertIn("/booking/af54b91e-1ff2-456c-a5e4-565d8369e557", source)
        self.assertIn("program=63c8bdb1-0e09-4a8b-bc2e-7e15e091c151", source)


if __name__ == "__main__":
    unittest.main()
