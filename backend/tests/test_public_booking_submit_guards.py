import unittest
from pathlib import Path


class PublicBookingSubmitGuardTests(unittest.TestCase):
    def setUp(self):
        self.source = Path("backend/routes/bookings.py").read_text(encoding="utf-8")
        self.frontend = Path("frontend/src/pages/public/BookingPage.js").read_text(encoding="utf-8")

    def test_public_booking_validates_program_window_before_write(self):
        public_create = self.source.split("async def create_public_booking(", 1)[1]
        self.assertIn("input_error = _public_booking_input_error(program, booking_data)", public_create)
        self.assertLess(
            public_create.index("input_error = _public_booking_input_error(program, booking_data)"),
            public_create.index("collision_error = await check_booking_collision("),
        )
        self.assertIn("Vybraný termín je před začátkem období programu.", self.source)
        self.assertIn("Vybraný termín je po skončení období programu.", self.source)
        self.assertIn("Termín je možné rezervovat nejdříve", self.source)
        self.assertIn("Termín je možné rezervovat nejvýše", self.source)
        self.assertIn("Program se ve vybraný den nenabízí.", self.source)
        self.assertIn("Vybraný čas už není pro tento program dostupný.", self.source)

    def test_public_booking_validates_capacity_before_write(self):
        public_create = self.source.split("async def create_public_booking(", 1)[1]
        self.assertIn("booking_data.num_students < min_capacity", self.source)
        self.assertIn("booking_data.num_students > max_capacity", self.source)
        self.assertIn('"field": "num_students"', self.source)
        self.assertLess(
            public_create.index("input_error = _public_booking_input_error(program, booking_data)"),
            public_create.index("booking = await booking_repo.create(payload, institution_id)"),
        )

    def test_public_booking_write_errors_return_json_detail(self):
        public_create = self.source.split("async def create_public_booking(", 1)[1]
        self.assertIn("logger.exception(", public_create)
        self.assertIn("Rezervaci se nepodařilo uložit.", public_create)
        self.assertIn('"message_cs"', public_create)
        self.assertIn("await db.rollback()", public_create)

    def test_frontend_routes_api_field_errors_to_steps(self):
        self.assertIn("const bookingFieldStep = (field) =>", self.frontend)
        self.assertIn("if (d?.field)", self.frontend)
        self.assertIn("setFieldErrors(prev => ({ ...prev, [d.field]: apiMessage }))", self.frontend)
        self.assertIn("if (targetStep) setStep(targetStep)", self.frontend)


if __name__ == "__main__":
    unittest.main()
