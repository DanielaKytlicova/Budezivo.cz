import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CalendarImportSelectionTests(unittest.TestCase):
    def test_integration_has_separate_nullable_import_calendar(self):
        model = (ROOT / "backend/database/models.py").read_text()
        migration = (ROOT / "backend/alembic/versions/a6b7c8d9e0f1_calendar_import_selection.py").read_text()
        self.assertIn("availability_calendar_id = Column(Text, nullable=True)", model)
        self.assertIn("ADD COLUMN IF NOT EXISTS availability_calendar_id TEXT", migration)

    def test_import_is_disabled_without_explicit_calendar(self):
        model = (ROOT / "backend/database/models.py").read_text()
        migration = (ROOT / "backend/alembic/versions/a6b7c8d9e0f1_calendar_import_selection.py").read_text()
        self.assertIn("default=False, server_default='false'", model)
        self.assertIn("availability_calendar_id IS NULL", migration)
        self.assertIn("SET import_enabled = FALSE", migration)

    def test_google_import_uses_selected_calendar_but_export_keeps_primary(self):
        source = (ROOT / "backend/routes/google_calendar.py").read_text()
        self.assertIn("users/me/calendarList", source)
        self.assertIn("integration.availability_calendar_id", source)
        self.assertIn("quote(integration.availability_calendar_id, safe='')", source)
        self.assertIn("CALENDAR_EVENTS_URI = f\"{CALENDAR_API_BASE}/calendars/primary/events\"", source)

    def test_disabled_external_blocks_are_removed_and_ignored_by_collision(self):
        google = (ROOT / "backend/routes/google_calendar.py").read_text()
        microsoft = (ROOT / "backend/routes/microsoft_calendar.py").read_text()
        collision = (ROOT / "backend/services/collision_service.py").read_text()
        self.assertIn("AvailabilityBlock.source == SOURCE", google)
        self.assertIn('AvailabilityBlock.source == "outlook"', microsoft)
        self.assertIn("AvailabilityBlock.source.notin_(['google', 'outlook'])", collision)
        self.assertIn("UserCalendarIntegration.import_enabled == True", collision)

    def test_outlook_does_not_fallback_to_unspecified_calendar(self):
        source = (ROOT / "backend/routes/microsoft_calendar.py").read_text()
        self.assertIn("/me/calendars/{quote(integration.availability_calendar_id, safe='')}/calendarView", source)
        self.assertNotIn('fallback_url = f"{GRAPH_BASE}/me/events"', source)

    def test_frontend_requires_explicit_calendar_before_enabling_import(self):
        source = (ROOT / "frontend/src/pages/admin/LecturerAvailabilityPage.js").read_text()
        self.assertIn("Nejprve vyberte kalendář pro kontrolu dostupnosti.", source)
        self.assertIn('data-testid="google-calendar-selector"', source)
        self.assertIn('data-testid="outlook-calendar-selector"', source)
        self.assertIn("availability_calendar_id", source)


if __name__ == "__main__":
    unittest.main()
