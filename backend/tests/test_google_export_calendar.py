from pathlib import Path
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
        self.assertIn("https://www.googleapis.com/auth/calendar.app.created", helpers)

    def test_migration_is_nullable_and_non_destructive(self):
        self.assertIn("ADD COLUMN IF NOT EXISTS google_export_calendar_id TEXT", MIGRATION)
        self.assertNotIn("UPDATE user_calendar_integrations", MIGRATION)

    def test_primary_events_are_not_deleted_by_new_disconnect_cleanup(self):
        self.assertIn('exp.google_calendar_id != "primary"', ROUTE)
        self.assertIn('link.google_calendar_id != "primary"', ROUTE)

    def test_ui_shows_dedicated_export_calendar(self):
        self.assertIn('data-testid="google-export-calendar"', FRONTEND)
        self.assertIn("status.export_calendar_id", FRONTEND)
