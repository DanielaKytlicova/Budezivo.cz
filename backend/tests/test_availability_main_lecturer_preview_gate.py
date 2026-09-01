import asyncio
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[2]
AVAILABILITY_ROUTE = ROOT / "backend" / "routes" / "availability.py"
BOOKINGS_ROUTE = ROOT / "backend" / "routes" / "bookings.py"

spec = importlib.util.spec_from_file_location("availability_route", AVAILABILITY_ROUTE)
availability_route = importlib.util.module_from_spec(spec)
spec.loader.exec_module(availability_route)


class AvailabilityMainLecturerPreviewGateTests(unittest.TestCase):
    def test_program_without_lecturer_collision_skips_main_lecturer_gate(self):
        with patch.object(availability_route, "pick_main_lecturer", new=AsyncMock()) as pick:
            available = asyncio.run(
                availability_route._slot_has_assignable_main_lecturer(
                    object(),
                    "11111111-1111-1111-1111-111111111111",
                    SimpleNamespace(collision_resources=[]),
                    "2026-09-01",
                    "10:00-11:00",
                )
            )

        self.assertTrue(available)
        pick.assert_not_called()

    def test_program_with_lecturer_collision_uses_booking_assignment_gate(self):
        with patch.object(availability_route, "pick_main_lecturer", new=AsyncMock(return_value=None)) as pick:
            available = asyncio.run(
                availability_route._slot_has_assignable_main_lecturer(
                    object(),
                    "11111111-1111-1111-1111-111111111111",
                    SimpleNamespace(collision_resources=["lecturer"]),
                    "2026-09-01",
                    "10:00-11:00",
                )
            )

        self.assertFalse(available)
        pick.assert_awaited_once()

    def test_public_day_availability_hides_slots_without_main_lecturer(self):
        source = AVAILABILITY_ROUTE.read_text(encoding="utf-8")
        day_section = source.split('@router.get("/availability/{institution_id}/{program_id}/{date}")', 1)[1]
        day_section = day_section.split('@router.get("/calendar/{institution_id}/{year}/{month}")', 1)[0]

        self.assertIn("from services.lecturer_assignment_service import pick_main_lecturer", source)
        self.assertIn("async def _slot_has_assignable_main_lecturer", source)
        self.assertIn("not await _slot_has_assignable_main_lecturer(", day_section)
        self.assertIn('block["status"] = "unavailable"', day_section)

    def test_public_month_calendar_counts_only_slots_with_main_lecturer(self):
        source = AVAILABILITY_ROUTE.read_text(encoding="utf-8")
        calendar_section = source.split('@router.get("/calendar/{institution_id}/{year}/{month}")', 1)[1]

        self.assertIn("not await _slot_has_assignable_main_lecturer(", calendar_section)
        self.assertIn("available_blocks += 1", calendar_section)
        self.assertIn("has_availability = available_blocks > 0", calendar_section)

    def test_public_booking_submit_still_uses_same_assignment_gate(self):
        source = BOOKINGS_ROUTE.read_text(encoding="utf-8")
        public_create = source.split("async def create_public_booking(", 1)[1]

        self.assertIn("resolved = await _resolve_main_lecturer(", public_create)
        self.assertIn("pick_main_lecturer(", source)
        self.assertLess(
            public_create.index("collision_error = await check_booking_collision("),
            public_create.index("resolved = await _resolve_main_lecturer("),
        )


if __name__ == "__main__":
    unittest.main()
