from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HomepageDemoAvailabilityTests(unittest.TestCase):
    def test_demo_availability_is_database_independent_and_has_free_and_booked_slots(self):
        source = (ROOT / "backend/routes/availability.py").read_text(encoding="utf-8")
        demo_block = source.split('if institution_id == "demo":', 1)[1].split(
            "# Get program to check its time blocks", 1
        )[0]
        self.assertIn('"status": "available"', demo_block)
        self.assertIn('"status": "booked"', demo_block)
        self.assertNotIn("ProgramRepositorySupabase", demo_block)

    def test_demo_waitlist_does_not_write_a_real_entry(self):
        source = (ROOT / "backend/routes/waitlist.py").read_text(encoding="utf-8")
        demo_block = source.split('if data.institution_id == "demo":', 1)[1].split(
            "# Validate program exists", 1
        )[0]
        self.assertIn('"demo": True', demo_block)
        self.assertNotIn("db.add", demo_block)


if __name__ == "__main__":
    unittest.main()
