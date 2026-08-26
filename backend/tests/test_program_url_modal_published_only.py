import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODAL = ROOT / "frontend" / "src" / "components" / "admin" / "ProgramUrlModal.js"


class ProgramUrlModalPublishedOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MODAL.read_text(encoding="utf-8")

    def test_modal_only_offers_public_programs(self):
        self.assertIn("const publicPrograms = Array.isArray(programs)", self.source)
        self.assertIn("p.status === 'active' && p.is_published", self.source)
        self.assertIn("{publicPrograms.map(program => (", self.source)
        self.assertNotIn("programs.filter(p => p.status === 'active').map", self.source)

    def test_unpublished_program_url_is_not_generated(self):
        self.assertIn("const program = publicPrograms.find(p => p.id === programId);", self.source)
        self.assertIn("Nejdřív program zveřejněte", self.source)


if __name__ == "__main__":
    unittest.main()
