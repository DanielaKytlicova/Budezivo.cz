from pathlib import Path
import ast
import hashlib
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROUTE = (ROOT / "routes/google_calendar.py").read_text()
MODEL = (ROOT / "database/models.py").read_text()
MIGRATION = (ROOT / "alembic/versions/b7c8d9e0f1a2_google_export_calendar.py").read_text()
FRONTEND = (ROOT.parent / "frontend/src/components/calendar/ReservationSyncDialog.jsx").read_text()


class GoogleExportCalendarTests(unittest.TestCase):
    def test_export_uses_dedicated_calendar_and_is_idempotent(self):
        self.assertIn("google_export_calendar_id = Column(Text, nullable=True)", MODEL)
        self.assertIn("async def _ensure_export_calendar(", ROUTE)
        self.assertIn("if stored_id:", ROUTE)
        self.assertIn("/calendars/{quote(calendar_id, safe='')}/events", ROUTE)
        self.assertIn("google_calendar_id=export_calendar_id", ROUTE)
        self.assertNotIn("CALENDAR_EVENTS_URI", ROUTE)
        self.assertIn("has_export_calendar_scope", ROUTE)

    def test_oauth_requests_calendar_creation_scope(self):
        helpers = (ROOT / "services/google_calendar_helpers.py").read_text()
        tree = ast.parse(helpers)
        scopes_assignment = next(
            node for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "SCOPES" for target in node.targets)
        )
        self.assertEqual(
            ast.literal_eval(scopes_assignment.value),
            [
                "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
                "https://www.googleapis.com/auth/calendar.freebusy",
                "https://www.googleapis.com/auth/calendar.app.created",
            ],
        )
        self.assertIn("https://www.googleapis.com/auth/calendar.app.created", helpers)
        self.assertIn("https://www.googleapis.com/auth/calendar.calendarlist.readonly", helpers)
        self.assertIn("https://www.googleapis.com/auth/calendar.freebusy", helpers)
        self.assertNotIn("https://www.googleapis.com/auth/calendar.readonly", helpers)
        self.assertNotIn("https://www.googleapis.com/auth/calendar.events\"", helpers)
        self.assertNotIn("https://www.googleapis.com/auth/userinfo.email", helpers)

    def test_oauth_does_not_fetch_unused_google_identity(self):
        self.assertNotIn("USERINFO_URI", ROUTE)
        self.assertNotIn("userinfo failed", ROUTE)
        self.assertIn("has_required_google_scopes(granted_scopes)", ROUTE)

    def test_migration_is_nullable_and_non_destructive(self):
        self.assertIn("ADD COLUMN IF NOT EXISTS google_export_calendar_id TEXT", MIGRATION)
        self.assertNotIn("UPDATE user_calendar_integrations", MIGRATION)

    def test_primary_events_are_not_deleted_by_new_disconnect_cleanup(self):
        self.assertIn('exp.google_calendar_id != "primary"', ROUTE)
        self.assertIn('link.google_calendar_id != "primary"', ROUTE)

    def test_ui_shows_dedicated_export_calendar(self):
        self.assertIn('data-testid="google-export-calendar"', FRONTEND)
        self.assertIn("status.export_calendar_id", FRONTEND)

    def test_enabling_export_backfills_existing_reservations(self):
        self.assertIn("if data.export_enabled is True:", ROUTE)
        self.assertIn("export_stats = await _export_reservations(db, integration)", ROUTE)
        self.assertIn('"export": export_stats', ROUTE)

    def test_import_uses_freebusy_without_private_event_titles(self):
        self.assertIn("/freeBusy", ROUTE)
        self.assertIn("FREEBUSY_WINDOW_DAYS = 90", ROUTE)
        self.assertIn("while window_start < end_date", ROUTE)
        self.assertIn('"busy"', ROUTE)
        self.assertIn('"Obsazeno v Google kalendáři"', ROUTE)
        self.assertNotIn('title = ev.get("summary")', ROUTE)

    def test_export_is_one_way_and_never_mutates_reservations_from_google(self):
        self.assertIn('"source": "budezivo"', (ROOT / "services/google_calendar_helpers.py").read_text())
        self.assertNotIn("Reservation.date =", ROUTE)
        self.assertNotIn("Reservation.time_block =", ROUTE)

    def test_calendar_move_deletes_only_the_event_recorded_in_export_mapping(self):
        self.assertIn("if link.google_calendar_id != export_calendar_id:", ROUTE)
        self.assertIn(
            "token, link.google_calendar_id, link.google_event_id", ROUTE
        )
        self.assertIn("continue", ROUTE)
        self.assertNotIn('calendar_id="primary"', ROUTE)

    def test_export_creation_uses_a_stable_google_event_id(self):
        tree = ast.parse(ROUTE)
        helper = next(
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_google_export_event_id"
        )
        self.assertIn("hashlib.sha256", ast.unparse(helper))
        namespace = {"hashlib": hashlib, "PROVIDER": "google"}
        exec(compile(ast.Module(body=[helper], type_ignores=[]), "<helper>", "exec"), namespace)
        event_id = namespace["_google_export_event_id"]("user-1", "booking-1")
        self.assertEqual(event_id, namespace["_google_export_event_id"]("user-1", "booking-1"))
        self.assertNotEqual(event_id, namespace["_google_export_event_id"]("user-1", "booking-2"))
        self.assertRegex(event_id, r"^[0-9a-v]{5,1024}$")
        self.assertIn(
            "body, deterministic_event_id",
            ROUTE,
        )
        self.assertIn("resp.status_code == 409 and event_id", ROUTE)

    def test_export_sync_is_serialized_before_calendar_reconciliation(self):
        lock = ROUTE.index("func.pg_advisory_xact_lock")
        refresh = ROUTE.index("await db.refresh(integration)", lock)
        reconcile = ROUTE.index("await _ensure_export_calendar(", refresh)
        final_commit = ROUTE.index("await db.commit()", reconcile)
        self.assertLess(lock, refresh)
        self.assertLess(refresh, reconcile)
        self.assertLess(reconcile, final_commit)
