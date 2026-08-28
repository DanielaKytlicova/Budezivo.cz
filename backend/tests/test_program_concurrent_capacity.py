import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class ProgramConcurrentCapacityTests(unittest.TestCase):
    def test_schema_model_and_migration_define_safe_default_limit(self):
        self.assertIn("max_concurrent_bookings = Column(Integer, default=1)", read("database/models.py"))
        self.assertIn("max_concurrent_bookings: Optional[int] = 1", read("models/schemas.py"))
        migration = read("alembic/versions/5a6b7c8d9e0f_program_concurrent_capacity.py")
        self.assertIn("ADD COLUMN IF NOT EXISTS max_concurrent_bookings INTEGER", migration)
        self.assertIn('down_revision = "4f5a6b7c8d9e"', migration)

        default_migration = read("alembic/versions/c2d3e4f5a6b7_default_program_concurrent_limit.py")
        self.assertIn("ALTER TABLE programs ALTER COLUMN max_concurrent_bookings SET DEFAULT 1", default_migration)
        backfill_migration = read("alembic/versions/d3e4f5a6b7c8_backfill_program_concurrent_limit.py")
        self.assertIn("UPDATE programs SET max_concurrent_bookings = 1 WHERE max_concurrent_bookings IS NULL", backfill_migration)

    def test_booking_collision_enforces_capacity_with_self_exclusion(self):
        source = read("services/collision_service.py")
        self.assertIn("def program_concurrent_limit(program)", source)
        self.assertIn("def concurrent_capacity_reached", source)
        self.assertIn("async def count_overlapping_program_reservations", source)
        self.assertIn("exclude_reservation_id: Optional[str] = None", source)
        self.assertIn("Reservation.id != uuid.UUID(exclude_reservation_id)", source)
        self.assertIn("await check_program_concurrent_capacity", source)
        self.assertIn("if str(res.program_id) == str(program.id):\n                continue", source)

    def test_availability_uses_capacity_instead_of_always_blocking_same_program(self):
        service = read("services/availability_service.py")
        self.assertNotIn("Check own-program bookings first (always blocks", service)
        self.assertIn("concurrent_limit = program_concurrent_limit(program)", service)
        self.assertIn("overlapping_same_program >= concurrent_limit", service)

        route = read("routes/availability.py")
        self.assertIn("def _slot_capacity_reached", route)
        self.assertIn("max_concurrent_bookings", route)
        self.assertIn("slot_reaches_capacity", route)

    def test_admin_program_ui_exposes_limit(self):
        programs_page = read("../frontend/src/pages/admin/ProgramsPage.js")
        collision_tab = read("../frontend/src/components/admin/ProgramCollisionTab.js")
        self.assertIn("max_concurrent_bookings", programs_page)
        self.assertIn("Souběžné rezervace stejného programu", collision_tab)
        self.assertIn("program-concurrent-capacity-input", collision_tab)


if __name__ == "__main__":
    unittest.main()
