import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOKINGS_ROUTE = ROOT / "backend" / "routes" / "bookings.py"


class PublicBookingTransactionLockTests(unittest.TestCase):
    def test_public_booking_does_not_commit_between_collision_check_and_insert(self):
        source = BOOKINGS_ROUTE.read_text(encoding="utf-8")
        public_create = source.split("async def create_public_booking(", 1)[1]
        locked_section = public_create[
            public_create.index("collision_error = await check_booking_collision("):
            public_create.index("booking = await booking_repo.create(")
        ]

        self.assertIn("update(School)", locked_section)
        self.assertIn("school_id = None", locked_section)
        self.assertNotIn("db.add(School(", locked_section)
        self.assertNotIn("school_repo.increment_booking_count", locked_section)
        self.assertNotIn("school_repo.create", locked_section)
        self.assertNotIn("await db.commit()", locked_section)

    def test_school_contact_is_best_effort_after_booking_commit(self):
        source = BOOKINGS_ROUTE.read_text(encoding="utf-8")
        public_create = source.split("async def create_public_booking(", 1)[1]

        self.assertLess(
            public_create.index("booking = await booking_repo.create("),
            public_create.index("db.add(SchoolContact("),
        )
        self.assertIn("await db.rollback()", public_create)

    def test_new_school_crm_write_is_best_effort_after_booking_commit(self):
        source = BOOKINGS_ROUTE.read_text(encoding="utf-8")
        public_create = source.split("async def create_public_booking(", 1)[1]
        crm_section = public_create[
            public_create.index("if not school and booking_data.contact_email:"):
            public_create.index("# Phase 76", public_create.index("if not school and booking_data.contact_email:"))
        ]

        self.assertLess(
            public_create.index("booking = await booking_repo.create("),
            public_create.index("db.add(School("),
        )
        self.assertIn("db.add(School(", crm_section)
        self.assertIn("db.add(SchoolContact(", crm_section)
        self.assertIn("deliverability_status=\"unknown\"", crm_section)
        self.assertIn("update(Reservation)", crm_section)
        self.assertIn("except Exception as e:", crm_section)
        self.assertIn("await db.rollback()", crm_section)


if __name__ == "__main__":
    unittest.main()
