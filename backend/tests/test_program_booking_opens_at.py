import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


class ProgramBookingOpensAtTests(unittest.TestCase):
    def test_database_and_migration_define_booking_opens_at(self):
        model = (BACKEND / "database" / "models.py").read_text(encoding="utf-8")
        migration = (BACKEND / "alembic" / "versions" / "4f5a6b7c8d9e_program_booking_opens_at.py").read_text(encoding="utf-8")

        self.assertIn("booking_opens_at = Column(DateTime(timezone=True))", model)
        self.assertIn("ADD COLUMN IF NOT EXISTS booking_opens_at TIMESTAMPTZ", migration)

    def test_repository_persists_booking_opens_at(self):
        repo = (BACKEND / "database" / "supabase_repositories.py").read_text(encoding="utf-8")

        self.assertIn("def _parse_program_datetime", repo)
        self.assertIn("booking_opens_at = self._parse_program_datetime", repo)
        self.assertIn("booking_opens_at=booking_opens_at", repo)
        self.assertIn("processed_data['booking_opens_at'] = self._parse_program_datetime", repo)

    def test_public_availability_waits_until_booking_opens(self):
        availability = (BACKEND / "routes" / "availability.py").read_text(encoding="utf-8")
        programs = (BACKEND / "routes" / "programs.py").read_text(encoding="utf-8")

        self.assertIn('program.get("booking_opens_at")', availability)
        self.assertIn("def _program_validity_datetime", availability)
        self.assertIn("now < booking_opens_at", availability)
        self.assertIn('"booking_opens_at"', programs)

    def test_admin_program_form_has_booking_opens_toggle(self):
        page = (FRONTEND / "src" / "pages" / "admin" / "ProgramsPage.js").read_text(encoding="utf-8")

        self.assertIn("booking_opens_at: ''", page)
        self.assertIn("Přidat spuštění rezervací", page)
        self.assertIn("program-booking-opens-toggle", page)
        self.assertIn("program-booking-opens-at", page)
        self.assertIn('type="datetime-local"', page)
        self.assertIn("dateTimeLocalToISOString(formData.booking_opens_at)", page)
        self.assertIn("Program bude zveřejněný, ale volné termíny", page)


if __name__ == "__main__":
    unittest.main()
