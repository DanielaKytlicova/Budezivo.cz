import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOKINGS_ROUTE = ROOT / "backend" / "routes" / "bookings.py"
BOOKING_PAGE = ROOT / "frontend" / "src" / "pages" / "public" / "BookingPage.js"


class PublicBookingSubmitErrorDetailTests(unittest.TestCase):
    def test_school_contact_sets_deliverability_status_explicitly(self):
        source = BOOKINGS_ROUTE.read_text(encoding="utf-8")
        public_create = source.split("async def create_public_booking(", 1)[1]
        school_contact_block = public_create[
            public_create.index("db.add(SchoolContact("):
            public_create.index("await db.commit()", public_create.index("db.add(SchoolContact("))
        ]

        self.assertIn('deliverability_status="unknown"', school_contact_block)

    def test_public_booking_frontend_extracts_fastapi_validation_detail(self):
        source = BOOKING_PAGE.read_text(encoding="utf-8")

        self.assertIn("const bookingApiErrorMessage = (detail) =>", source)
        self.assertIn("Array.isArray(detail)", source)
        self.assertIn("BOOKING_API_FIELD_LABELS", source)
        self.assertIn("toast.error(bookingApiErrorMessage(d));", source)


if __name__ == "__main__":
    unittest.main()
