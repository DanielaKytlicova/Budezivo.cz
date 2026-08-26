import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class ProgramAvailabilityExceptionSummaryTests(unittest.TestCase):
    def test_program_view_lists_regular_availability_and_grouped_blocks(self):
        source = read("../frontend/src/pages/admin/UnifiedAvailabilityPage.js")
        self.assertIn("Pravidelná dostupnost programu", source)
        self.assertIn("Programové blokace / výjimky", source)
        self.assertIn("allProgramExceptions", source)
        self.assertIn("groupProgramExceptions", source)
        self.assertIn("program-exception-group", source)
        self.assertIn("availability-unified/exceptions?scope_type=program", source)

    def test_program_summary_is_rendered_below_calendar(self):
        source = read("../frontend/src/pages/admin/UnifiedAvailabilityPage.js")

        self.assertIn("const renderAvailabilitySummary = () =>", source)
        self.assertIn("{renderAvailabilitySummary()}", source)
        calendar_index = source.index('data-testid="program-week-calendar"')
        summary_render_index = source.index("{renderAvailabilitySummary()}")

        self.assertLess(calendar_index, summary_render_index)

    def test_program_blocks_are_enforced_by_collision_service(self):
        collision_source = read("services/collision_service.py")
        availability_source = read("services/availability_service.py")
        unified_route_source = read("routes/unified_availability.py")

        self.assertIn("check_exception_blocks_slot", collision_source)
        self.assertIn("scope_type=data.scope_type", unified_route_source)
        self.assertIn("program_ids", unified_route_source)
        self.assertIn("get_program_exceptions", availability_source)
        self.assertIn("STATUS_BLOCKED_EXCEPTION", availability_source)


if __name__ == "__main__":
    unittest.main()
