import unittest
from datetime import datetime, timezone

from services.program_booking_window import booking_opens_message, parse_program_datetime


class ProgramBookingOpensGateTests(unittest.TestCase):
    def test_future_booking_open_time_blocks_public_booking(self):
        message = booking_opens_message(
            {"booking_opens_at": "2026-09-01T07:00:00Z"},
            now=datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(message, "Rezervace tohoto programu se spustí až 01.09.2026 09:00.")

    def test_past_booking_open_time_allows_public_booking(self):
        message = booking_opens_message(
            {"booking_opens_at": "2026-09-01T07:00:00Z"},
            now=datetime(2026, 9, 1, 7, 0, tzinfo=timezone.utc),
        )

        self.assertIsNone(message)

    def test_program_schema_accepts_booking_open_time(self):
        from models.schemas import ProgramCreate

        data = {
            "name_cs": "Test",
            "name_en": "Test",
            "description_cs": "Popis",
            "description_en": "Description",
            "duration": 60,
            "age_group": "zs1",
            "target_group": "schools",
            "booking_opens_at": "2026-09-01T07:00:00Z",
        }

        program = ProgramCreate(**data)

        self.assertEqual(program.booking_opens_at.isoformat(), "2026-09-01T07:00:00+00:00")

    def test_timezone_values_are_converted_to_utc(self):
        parsed = parse_program_datetime("2026-09-01T09:00:00+02:00")

        self.assertEqual(parsed.isoformat(), "2026-09-01T07:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
