import pathlib
import ast
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]


class ProgramBookingOptionsRegressionTests(unittest.TestCase):
    def test_alembic_graph_has_single_head(self):
        revisions = {}
        parent_revisions = set()
        for migration in (ROOT / "backend/alembic/versions").glob("*.py"):
            values = {}
            for node in ast.parse(migration.read_text()).body:
                name = None
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    name = node.targets[0].id
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    name = node.target.id
                if name in {"revision", "down_revision"}:
                    values[name] = ast.literal_eval(node.value)
            revision = values.get("revision")
            if revision:
                revisions[revision] = migration.name
            parents = values.get("down_revision")
            if parents:
                parent_revisions.update(parents if isinstance(parents, (tuple, list)) else [parents])
        heads = set(revisions) - parent_revisions
        self.assertEqual(heads, {"0f9e8d7c6b5a"})

    def test_hardcoded_time_note_is_removed_and_custom_note_is_gated(self):
        source = (ROOT / "frontend/src/pages/public/BookingPage.js").read_text()
        self.assertNotIn("Všechny časové bloky jsou 90 min. dlouhé", source)
        self.assertIn("booking_time_note_enabled", source)
        self.assertIn("selectedProgram.booking_time_note", source)

    def test_payment_choice_is_validated_on_server(self):
        source = (ROOT / "backend/routes/bookings.py").read_text()
        self.assertIn("allowed_payment_methods", source)
        self.assertIn("Vybraný způsob platby není pro tento program dostupný", source)
        self.assertIn("Vyplňte fakturační údaje", source)

    def test_month_calendar_checks_collisions_for_regular_slots(self):
        source = (ROOT / "backend/routes/availability.py").read_text()
        calendar = source.split("available_blocks = 0", 1)[1]
        self.assertIn("get_collision_info_for_availability", calendar)
        self.assertNotIn("if slot in extra_slot_times", calendar)

    def test_program_exception_overlay_is_independent_of_base_schedule(self):
        source = (ROOT / "frontend/src/pages/admin/UnifiedAvailabilityPage.js").read_text()
        cell_status = source.split("const getCellStatus", 1)[1].split("const handleCellClick", 1)[0]
        self.assertLess(cell_status.index("exceptions.find"), cell_status.index("weekSlots[dateStr]"))
        self.assertIn("status: 'blocked_exception'", cell_status)

    def test_reschedule_note_is_escaped_in_email(self):
        source = (ROOT / "backend/templates/emails/templates.py").read_text()
        template = source.split("def reservation_rescheduled", 1)[1].split("def reservation_reminder_teacher", 1)[0]
        self.assertIn("html_lib.escape(reschedule_note)", template)
        self.assertIn("Poznámka ke změně", template)

    def test_invite_dialog_is_scrollable(self):
        source = (ROOT / "frontend/src/pages/admin/TeamPage.js").read_text()
        invite = source.split("{/* Invite Dialog */}", 1)[1]
        self.assertIn("max-h-[90dvh] overflow-y-auto", invite)

    def test_collision_windows_include_preparation_and_cleanup(self):
        source = (ROOT / "backend/services/collision_service.py").read_text()
        overlap = source.split("def time_blocks_overlap", 1)[1].split("def reservation_lecturer_ids", 1)[0]
        self.assertIn("start_a -= max(0, preparation_a or 0)", overlap)
        self.assertIn("end_a += max(0, cleanup_a or 0)", overlap)
        self.assertIn("end_b += max(0, cleanup_b or 0)", overlap)
        tree = ast.parse(source)
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {"parse_time_block", "time_blocks_overlap"}]
        namespace = {}
        exec(compile(ast.Module(body=functions, type_ignores=[]), "collision_helpers", "exec"), namespace)
        self.assertTrue(namespace["time_blocks_overlap"]("13:00", 60, "11:30", 60, 0, 0, 0, 200))
        self.assertFalse(namespace["time_blocks_overlap"]("16:00", 60, "11:30", 60, 0, 0, 0, 200))

    def test_daily_program_limit_is_checked_by_collision_gate(self):
        source = (ROOT / "backend/services/collision_service.py").read_text()
        collision = source.split("async def check_booking_collision", 1)[1]
        self.assertIn("check_program_daily_limit", collision)
        self.assertIn("Reservation.status != \"cancelled\"", source)
        self.assertIn("Denní limit programu", source)

    def test_program_repository_persists_new_booking_settings(self):
        source = (ROOT / "backend/database/supabase_repositories.py").read_text()
        create = source.split("class ProgramRepositorySupabase", 1)[1].split("async def update", 1)[0]
        update = source.split("async def update(self, program_id", 1)[1].split("async def archive", 1)[0]
        for field in (
            "booking_time_note_enabled",
            "booking_time_note",
            "booking_payment_enabled",
            "booking_payment_required",
            "booking_payment_methods",
            "max_bookings_per_day",
        ):
            self.assertIn(field, create)
        self.assertIn("if 'max_bookings_per_day' in processed_data", update)

    def test_booking_form_and_daily_limit_follow_reservation_parameters(self):
        source = (ROOT / "frontend/src/pages/admin/ProgramsPage.js").read_text()
        settings = source.split("const renderSettingsTab", 1)[1].split("const renderProgramForm", 1)[0]
        reservation_parameters = settings.index("Parametry rezervace")
        booking_form = settings.index("Rezervační formulář")
        daily_limit = settings.index("Denní limit programu")

        self.assertLess(reservation_parameters, booking_form)
        self.assertLess(booking_form, daily_limit)


if __name__ == "__main__":
    unittest.main()
