import asyncio
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from services.collision_service import (
    check_booking_collision,
    check_lecturer_available_for_block,
)
from database.supabase_repositories import BookingRepositorySupabase


INSTITUTION_ID = "11111111-1111-1111-1111-111111111111"
LECTURER_ID = "22222222-2222-2222-2222-222222222222"
PROGRAM_ID = "33333333-3333-3333-3333-333333333333"


class FakeScalars:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeResult:
    def __init__(self, rows=None, scalar=None):
        self.rows = rows or []
        self.scalar = scalar

    def scalars(self):
        return FakeScalars(self.rows)

    def scalar_one_or_none(self):
        return self.scalar


class FakeDb:
    def __init__(self, results):
        self.results = list(results)
        self.queries = []

    async def execute(self, query):
        self.queries.append(query)
        if not self.results:
            raise AssertionError("Unexpected db.execute call")
        return self.results.pop(0)


class FakeCreateDb:
    def __init__(self):
        self.added = None
        self.commits = 0
        self.refreshed = None

    def add(self, obj):
        self.added = obj

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshed = obj


def result(rows=None, scalar=None):
    return FakeResult(rows=rows, scalar=scalar)


def availability(start, end):
    return SimpleNamespace(start_time=start, end_time=end)


def time_off(start_date="2026-09-01", end_date="2026-09-01", start_time=None, end_time=None):
    return SimpleNamespace(
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
    )


def program(collision_resources=None):
    return SimpleNamespace(
        id=uuid.UUID(PROGRAM_ID),
        institution_id=uuid.UUID(INSTITUTION_ID),
        name_cs="Test program",
        duration=60,
        allow_parallel=True,
        max_concurrent_bookings=None,
        collision_resources=collision_resources or ["lecturer"],
        blocked_program_ids=[],
        room_id=None,
        assigned_lecturer_id=uuid.UUID(LECTURER_ID),
        collision_lecturer_ids=[],
        required_lecturers=1,
    )


class LecturerTimeOffWithoutScheduleTests(unittest.TestCase):
    def run_available(self, db, time_block="10:00-11:00"):
        return asyncio.run(
            check_lecturer_available_for_block(
                db,
                LECTURER_ID,
                INSTITUTION_ID,
                "2026-09-01",
                time_block,
                60,
            )
        )

    def test_no_schedule_and_no_time_off_is_available(self):
        db = FakeDb([
            result(rows=[]),
            result(rows=[]),
            result(scalar=None),
            result(rows=[]),
        ])

        self.assertTrue(self.run_available(db, "12:00-13:00"))

    def test_no_schedule_with_overlapping_time_off_is_unavailable(self):
        db = FakeDb([
            result(rows=[]),
            result(rows=[]),
            result(scalar=None),
            result(rows=[time_off(start_time="09:00", end_time="11:00")]),
        ])

        self.assertFalse(self.run_available(db, "10:30-11:30"))

    def test_no_schedule_with_non_overlapping_time_off_is_available(self):
        db = FakeDb([
            result(rows=[]),
            result(rows=[]),
            result(scalar=None),
            result(rows=[time_off(start_time="09:00", end_time="11:00")]),
        ])

        self.assertTrue(self.run_available(db, "12:00-13:00"))

    def test_no_schedule_with_all_day_time_off_is_unavailable(self):
        db = FakeDb([
            result(rows=[]),
            result(rows=[]),
            result(scalar=None),
            result(rows=[time_off()]),
        ])

        self.assertFalse(self.run_available(db, "12:00-13:00"))

    def test_existing_schedule_allows_slot_inside_window(self):
        db = FakeDb([
            result(rows=[availability("09:00", "14:00")]),
            result(rows=[]),
            result(rows=[]),
        ])

        self.assertTrue(self.run_available(db, "10:00-11:00"))

    def test_existing_schedule_blocks_slot_outside_window(self):
        db = FakeDb([
            result(rows=[availability("09:00", "14:00")]),
            result(rows=[]),
        ])

        self.assertFalse(self.run_available(db, "15:00-16:00"))

    def test_existing_schedule_still_respects_time_off(self):
        db = FakeDb([
            result(rows=[availability("09:00", "14:00")]),
            result(rows=[]),
            result(rows=[time_off(start_time="10:00", end_time="11:00")]),
        ])

        self.assertFalse(self.run_available(db, "10:00-11:00"))

    def test_valid_booking_flow_still_creates_bookable_program_reservation(self):
        db = FakeDb([
            result(),  # advisory lock
            result(scalar=program(["lecturer"])),
            result(rows=[]),  # existing reservations
            result(rows=[]),  # recurring lecturer availability
            result(rows=[]),  # one-off lecturer availability
            result(scalar=None),  # no lecturer schedule anywhere
            result(rows=[]),  # no lecturer time-off
        ])

        with patch("services.availability_service.check_exception_blocks_slot", return_value=None):
            collision = asyncio.run(
                check_booking_collision(
                    db,
                    INSTITUTION_ID,
                    PROGRAM_ID,
                    "2026-09-01",
                    "12:00-13:00",
                )
            )

        self.assertIsNone(collision)

        create_db = FakeCreateDb()
        booking = asyncio.run(
            BookingRepositorySupabase(create_db).create(
                {
                    "program_id": PROGRAM_ID,
                    "date": "2026-09-01",
                    "time_block": "12:00-13:00",
                    "school_name": "Test school",
                    "group_type": "school",
                    "age_or_class": "5. třída",
                    "num_students": 20,
                    "num_teachers": 2,
                    "special_requirements": None,
                    "contact_name": "Test Contact",
                    "contact_email": "test@example.test",
                    "contact_phone": "+420 600 111 222",
                    "assigned_lecturer_id": LECTURER_ID,
                    "assigned_lecturer_name": "Test Lecturer",
                    "assignment_source": "auto",
                    "assignment_reason": "test",
                    "gdpr_consent": True,
                    "terms_accepted": True,
                },
                INSTITUTION_ID,
            )
        )

        self.assertEqual(booking["program_id"], PROGRAM_ID)
        self.assertEqual(booking["date"], "2026-09-01")
        self.assertEqual(create_db.commits, 1)

    def test_program_without_lecturer_collision_resource_does_not_check_lecturer_availability(self):
        db = FakeDb([
            result(),  # advisory lock
            result(scalar=program([])),
            result(rows=[]),  # existing reservations
        ])

        with patch("services.availability_service.check_exception_blocks_slot", return_value=None):
            collision = asyncio.run(
                check_booking_collision(
                    db,
                    INSTITUTION_ID,
                    PROGRAM_ID,
                    "2026-09-01",
                    "12:00-13:00",
                )
            )

        self.assertIsNone(collision)
        self.assertEqual(len(db.queries), 3)


if __name__ == "__main__":
    unittest.main()
