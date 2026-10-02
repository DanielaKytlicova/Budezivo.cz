import sys
import unittest
import uuid
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.availability_preview import AvailabilityPreviewSnapshot


def obj(**values):
    return SimpleNamespace(**values)


class AvailabilityPreviewSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.institution_id = uuid.uuid4()
        self.program_id = uuid.uuid4()
        self.other_program_id = uuid.uuid4()
        self.lecturer_id = uuid.uuid4()
        self.program = obj(
            id=self.program_id,
            institution_id=self.institution_id,
            name_cs="Program",
            duration=60,
            preparation_time=0,
            cleanup_time=30,
            allow_parallel=False,
            collision_resources=[],
            blocked_program_ids=[],
            collision_lecturer_ids=[],
            assigned_lecturer_id=None,
            required_lecturers=1,
            max_bookings_per_day=None,
            max_concurrent_bookings=None,
            room_id=None,
        )
        self.other_program = obj(
            id=self.other_program_id,
            duration=60,
            preparation_time=0,
            cleanup_time=0,
            allow_parallel=True,
            blocked_program_ids=[],
            room_id=None,
        )
        self.snapshot = AvailabilityPreviewSnapshot(
            institution_id=self.institution_id,
            program=self.program,
            programs={
                str(self.program_id): self.program,
                str(self.other_program_id): self.other_program,
            },
            reservations_by_date=defaultdict(list),
            exceptions_by_date=defaultdict(list),
            users={},
            lecturer_availability=defaultdict(list),
            lecturer_time_off=defaultdict(list),
            availability_blocks=defaultdict(list),
            enabled_calendar_imports=set(),
        )

    def test_cleanup_time_blocks_following_reservation(self):
        self.snapshot.reservations_by_date["2026-10-06"].append(obj(
            id=uuid.uuid4(),
            program_id=self.other_program_id,
            time_block="10:00-11:00",
            assigned_lecturer_id=None,
            assigned_lecturer_ids=[],
        ))
        self.assertTrue(self.snapshot.is_blocked("2026-10-06", "09:00-10:00"))

    def test_exact_boundary_without_buffers_does_not_overlap(self):
        self.program.cleanup_time = 0
        self.snapshot.reservations_by_date["2026-10-06"].append(obj(
            id=uuid.uuid4(),
            program_id=self.other_program_id,
            time_block="10:00-11:00",
            assigned_lecturer_id=None,
            assigned_lecturer_ids=[],
        ))
        self.assertFalse(self.snapshot.is_blocked("2026-10-06", "09:00-10:00"))

    def test_daily_limit_blocks_every_slot_for_program(self):
        self.program.allow_parallel = True
        self.program.max_bookings_per_day = 1
        self.snapshot.reservations_by_date["2026-10-06"].append(obj(
            id=uuid.uuid4(),
            program_id=self.program_id,
            time_block="09:00-10:00",
            assigned_lecturer_id=None,
            assigned_lecturer_ids=[],
        ))
        self.assertTrue(self.snapshot.is_blocked("2026-10-06", "15:00-16:00"))

    def test_lecturer_schedule_and_time_off_are_evaluated_in_memory(self):
        self.snapshot.lecturer_availability[str(self.lecturer_id)].append(obj(
            lecturer_id=self.lecturer_id,
            is_recurring=True,
            day_of_week=1,
            specific_date=None,
            start_time="09:00",
            end_time="12:00",
        ))
        self.assertTrue(self.snapshot.lecturer_available_for_block(
            str(self.lecturer_id), "2026-10-06", "09:30-10:30", 60
        ))
        self.snapshot.lecturer_time_off[str(self.lecturer_id)].append(obj(
            start_date="2026-10-06",
            end_date="2026-10-06",
            start_time="10:00",
            end_time="11:00",
        ))
        self.assertFalse(self.snapshot.lecturer_available_for_block(
            str(self.lecturer_id), "2026-10-06", "09:30-10:30", 60
        ))


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None

    def scalars(self):
        return FakeScalarResult(self.rows)


class FakeDb:
    def __init__(self, result_rows):
        self.results = [FakeResult(rows) for rows in result_rows]
        self.execute_count = 0

    async def execute(self, _query):
        result = self.results[self.execute_count]
        self.execute_count += 1
        return result


class AvailabilityPreviewLoadTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_month_uses_fixed_five_queries_without_lecturers(self):
        institution_id = uuid.uuid4()
        program_id = uuid.uuid4()
        program = obj(
            id=program_id,
            institution_id=institution_id,
            assigned_lecturer_id=None,
            collision_lecturer_ids=[],
        )
        db = FakeDb([
            [program],  # selected program
            [],         # reservations for the complete range
            [program],  # programs referenced by reservations
            [],         # availability exceptions for the complete range
            [],         # active institution users
        ])
        snapshot = await AvailabilityPreviewSnapshot.load(
            db, str(institution_id), str(program_id), "2026-10-01", "2026-10-31"
        )
        self.assertIsNotNone(snapshot)
        self.assertEqual(db.execute_count, 5)


if __name__ == "__main__":
    unittest.main()
