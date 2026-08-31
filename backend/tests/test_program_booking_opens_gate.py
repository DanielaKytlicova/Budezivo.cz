import unittest
from datetime import date, datetime, timezone

from services.program_booking_window import (
    booking_opens_message,
    parse_program_datetime,
    program_booking_window_message,
)


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

    def test_program_window_blocks_dates_before_program_start(self):
        message = program_booking_window_message(
            {"start_date": "2026-09-22T00:00:00Z"},
            date(2026, 9, 21),
            now=datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(message, "Vybraný termín je před začátkem období programu.")

    def test_program_window_allows_program_start_date(self):
        message = program_booking_window_message(
            {"start_date": "2026-09-22T00:00:00Z"},
            date(2026, 9, 22),
            now=datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc),
        )

        self.assertIsNone(message)

    def test_program_window_blocks_dates_after_program_end(self):
        message = program_booking_window_message(
            {"end_date": "2026-09-30T23:59:00Z"},
            date(2026, 10, 1),
            now=datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(message, "Vybraný termín je po skončení období programu.")

    def test_program_window_reuses_booking_open_gate(self):
        message = program_booking_window_message(
            {"booking_opens_at": "2026-09-01T07:00:00Z"},
            date(2026, 9, 22),
            now=datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(message, "Rezervace tohoto programu se spustí až 01.09.2026 09:00.")

    def test_internal_program_window_can_ignore_booking_open_gate(self):
        message = program_booking_window_message(
            {
                "booking_opens_at": "2026-12-01T07:00:00Z",
                "start_date": "2026-11-24T00:00:00Z",
                "end_date": "2026-12-23T23:59:00Z",
            },
            date(2026, 11, 24),
            now=datetime(2026, 8, 31, 19, 0, tzinfo=timezone.utc),
            enforce_booking_opens=False,
        )

        self.assertIsNone(message)


if __name__ == "__main__":
    unittest.main()
