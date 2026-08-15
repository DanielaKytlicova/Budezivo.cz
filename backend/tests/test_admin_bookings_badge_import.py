from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class AdminBookingsBadgeImportTests(unittest.TestCase):
    def test_bookings_page_imports_badge_for_status_and_lecturer_labels(self):
        source = (ROOT / "frontend/src/pages/admin/BookingsPage.js").read_text()
        self.assertIn("import { Badge } from '../../components/ui/badge';", source)
        self.assertIn("<Badge className={variants[status] || 'bg-gray-100 text-gray-800'}>", source)
        self.assertIn('<Badge variant="outline" className="text-xs">', source)


if __name__ == "__main__":
    unittest.main()
