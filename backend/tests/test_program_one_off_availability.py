"""Behavioral integration tests on an isolated local PostgreSQL schema.

Run with TEST_PROGRAM_ONE_OFF_DATABASE_URL=postgresql+asyncpg://... (loopback
only). No production environment or external email/analytics calls are used.
"""
import importlib.util
import os
from pathlib import Path
import sys
import unittest
import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("JWT_SECRET", "isolated-one-off-test-secret-not-for-deployment")

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import BackgroundTasks, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.dialects.postgresql import insert
from database.models import (
    Base, Institution, User, Program, Reservation, AvailabilityException,
    LecturerAvailability, ProgramOneOffAvailability, Room,
)
from models.schemas import BookingCreate
from routes import bookings, availability
from routes import unified_availability as unified
from services.availability_service import evaluate_program_slots
from services.program_one_off_availability import get_program_one_offs

TEST_URL = os.environ.get("TEST_PROGRAM_ONE_OFF_DATABASE_URL")
DAY = "2026-09-22"
SLOT = "13:30-15:00"


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 9, 18, 10, 0, tzinfo=timezone.utc)
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)


class FrozenDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 9, 18)


@unittest.skipUnless(TEST_URL, "Set a loopback TEST_PROGRAM_ONE_OFF_DATABASE_URL for integration tests")
class ProgramOneOffIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        if urlparse(TEST_URL).hostname not in {"localhost", "127.0.0.1", "::1"}:
            self.fail("Integration tests refuse non-loopback database hosts")
        self.schema = "test_one_off_" + uuid.uuid4().hex
        self.engine = create_async_engine(TEST_URL, pool_size=1, max_overflow=0)
        async with self.engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{self.schema}"'))
            await conn.execute(text(f'SET search_path TO "{self.schema}"'))
            await conn.run_sync(lambda sync: Base.metadata.create_all(sync, tables=[
                table for table in Base.metadata.sorted_tables
                if table.name != "program_one_off_availability"
            ]))
            spec = importlib.util.spec_from_file_location("one_off_migration", ROOT / "alembic/versions/d9e0f1a2b3c4_program_one_off_availability.py")
            self.migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.migration)
            def migrate(sync):
                with Operations.context(MigrationContext.configure(sync)):
                    self.migration.upgrade()
            await conn.run_sync(migrate)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.db = self.factory()
        self.inst = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.pid = uuid.uuid4()
        self.db.add(Institution(id=self.inst, name="Isolated test institution", type="museum"))
        await self.db.commit()
        self.db.add(User(id=self.user_id, institution_id=self.inst, email="staff@example.org", name="Test", role="admin", password_hash="unused"))
        await self.db.commit()
        self.program = Program(
            id=self.pid, institution_id=self.inst, name_cs="Nej z nej: Alfonse Muchy",
            description_cs="Test program", age_group="all", duration=90,
            available_days=["tuesday"], time_blocks=["09:00-10:30"],
            min_days_before_booking=1, max_days_before_booking=90,
            min_capacity=1, max_capacity=30, allow_parallel=True,
            max_concurrent_bookings=1, send_email_notification=False,
        )
        self.db.add(self.program)
        await self.db.commit()
        self.user = {"institution_id": str(self.inst), "user_id": str(self.user_id), "role": "admin"}
        for module, attr, value in [
            (availability, "datetime", FrozenDatetime), (availability, "date_type", FrozenDate),
            (bookings, "datetime", FrozenDatetime),
        ]:
            self.enterContext(patch.object(module, attr, value))
        self.enterContext(patch("services.availability_service.datetime", FrozenDatetime))
        self.enterContext(patch("services.program_booking_window.datetime", FrozenDatetime))
        self.enterContext(patch.object(bookings, "_track_public_booking_event"))
        self.enterContext(patch.object(bookings, "_track_reservation_lifecycle_event"))

    async def asyncTearDown(self):
        await self.db.close()
        async with self.engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        await self.engine.dispose()

    async def add(self, day=DAY, start="13:30", end="15:00", program_id=None, user=None):
        return await unified.create_program_one_off(
            program_id or str(self.pid), unified.ProgramOneOffCreate(date=day, start_time=start, end_time=end),
            self.db, user or self.user,
        )

    async def daily(self, day=DAY, program_id=None):
        return (await availability.get_program_availability(str(self.inst), program_id or str(self.pid), day, self.db))["time_blocks"]

    async def internal(self, day=DAY):
        return await evaluate_program_slots(self.db, str(self.inst), str(self.pid), day)

    async def monthly(self):
        return (await availability.get_calendar_availability(str(self.inst), 2026, 9, str(self.pid), self.db))["dates"]

    async def submit(self, slot=SLOT, day=DAY):
        data = BookingCreate(
            program_id=str(self.pid), date=day, time_block=slot, school_name="Test school",
            group_type="zs1_7_12", num_students=10, num_teachers=1,
            contact_name="Test teacher", contact_email="teacher@example.org", contact_phone="123456789",
            terms_accepted=True,
        )
        request = Request({"type": "http", "method": "POST", "path": "/test", "headers": [], "client": ("127.0.0.1", 1)})
        # Bypass only the HTTP rate-limit wrapper; execute the real reservation route.
        return await bookings.create_public_booking.__wrapped__(
            str(self.inst), data, BackgroundTasks(), request, self.db
        )

    async def test_create_duplicate_reload_and_no_personal_or_schedule_change(self):
        first = await self.add()
        second = await self.add()
        self.assertEqual(first["id"], second["id"])
        await self.db.close()
        self.db = self.factory()
        listed = await unified.list_program_one_offs(str(self.pid), self.db, self.user)
        self.assertEqual([first], listed)
        self.assertEqual(0, await self.db.scalar(select(func.count()).select_from(LecturerAvailability)))
        program = await self.db.get(Program, self.pid)
        self.assertEqual(program.available_days, ["tuesday"])
        self.assertEqual(program.time_blocks, ["09:00-10:30"])

    async def test_database_uniqueness_and_migration_rollback(self):
        await self.add()
        result = await self.db.execute(insert(ProgramOneOffAvailability).values(
            institution_id=self.inst, program_id=self.pid, date=DAY,
            start_time="13:30", end_time="15:00",
        ).on_conflict_do_nothing(constraint="uq_program_one_off_slot").returning(ProgramOneOffAvailability.id))
        self.assertIsNone(result.scalar_one_or_none())
        await self.db.commit()
        self.assertEqual(1, await self.db.scalar(select(func.count()).select_from(ProgramOneOffAvailability)))
        await self.db.close()
        async with self.engine.begin() as conn:
            def downgrade(sync):
                with Operations.context(MigrationContext.configure(sync)):
                    self.migration.downgrade()
            await conn.run_sync(downgrade)
        self.db = self.factory()
        program = await self.db.get(Program, self.pid)
        self.assertEqual(program.time_blocks, ["09:00-10:30"])
        self.assertEqual(program.available_days, ["tuesday"])

    async def test_public_internal_month_and_next_week(self):
        before = await self.daily("2026-09-29")
        await self.add()
        self.assertEqual([s["time"] for s in await self.daily()], ["09:00-10:30", SLOT])
        self.assertIn({"time": SLOT, "status": "available", "reason": None}, await self.internal())
        self.assertEqual(before, await self.daily("2026-09-29"))
        month = {row["date"]: row for row in await self.monthly()}
        self.assertEqual(month[DAY]["available_blocks"], 2)
        self.assertEqual(month["2026-09-29"]["available_blocks"], 1)

    async def test_extra_on_non_regular_day_does_not_enable_regular_times(self):
        await self.add(day="2026-09-26")
        self.assertEqual([{"time": SLOT, "status": "available"}], await self.daily("2026-09-26"))
        self.assertEqual([SLOT], [s["time"] for s in await self.internal("2026-09-26")])
        month = {row["date"]: row for row in await self.monthly()}
        self.assertEqual(month["2026-09-26"]["available_blocks"], 1)
        self.assertFalse(month["2026-09-27"]["has_availability"])
        booked = await self.submit(day="2026-09-26")
        self.assertEqual(booked["time_block"], SLOT)

    async def test_public_submit_capacity_and_delete_preserve_booking(self):
        slot = await self.add()
        booked = await self.submit()
        with self.assertRaises(HTTPException) as caught:
            await self.submit()
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(next(s for s in await self.daily() if s["time"] == SLOT)["status"], "booked")
        await unified.delete_program_one_off(str(self.pid), slot["id"], self.db, self.user)
        self.assertIsNotNone(await self.db.get(Reservation, uuid.UUID(booked["id"])))
        self.assertNotIn(SLOT, [s["time"] for s in await self.daily()])
        with self.assertRaises(HTTPException) as caught:
            await self.submit()
        self.assertEqual(caught.exception.status_code, 400)

    async def test_reject_forged_end_time_and_next_week_but_keep_regular_booking(self):
        await self.add()
        for slot, day in [("13:30-16:00", DAY), (SLOT, "2026-09-29")]:
            with self.assertRaises(HTTPException) as caught:
                await self.submit(slot=slot, day=day)
            self.assertEqual(caught.exception.status_code, 400)
        booked = await self.submit(slot="09:00-10:30")
        self.assertEqual(booked["time_block"], "09:00-10:30")

    async def test_closure_still_blocks_extra_everywhere(self):
        await self.add(day="2026-09-26")
        self.db.add(AvailabilityException(institution_id=self.inst, scope_type="program", scope_id=self.pid,
            date="2026-09-26", start_time="13:00", end_time="16:00", reason="Closed"))
        await self.db.commit()
        self.assertEqual((await self.internal("2026-09-26"))[0]["status"], "blocked_exception")
        self.assertEqual((await self.daily("2026-09-26"))[0]["status"], "booked")
        self.assertFalse(next(row for row in await self.monthly() if row["date"] == "2026-09-26")["has_availability"])
        with self.assertRaises(HTTPException) as caught:
            await self.submit(day="2026-09-26")
        self.assertEqual(caught.exception.status_code, 409)

    async def test_tenant_program_and_role_isolation(self):
        slot = await self.add()
        other_inst = uuid.uuid4()
        self.db.add(Institution(id=other_inst, name="Other tenant", type="museum"))
        await self.db.commit()
        foreign_user = {**self.user, "institution_id": str(other_inst)}
        for operation in [
            unified.list_program_one_offs(str(self.pid), self.db, foreign_user),
            self.add(user=foreign_user),
            unified.delete_program_one_off(str(self.pid), slot["id"], self.db, foreign_user),
        ]:
            with self.assertRaises(HTTPException) as caught:
                await operation
            self.assertEqual(caught.exception.status_code, 404)
        with self.assertRaises(HTTPException) as caught:
            await self.add(user={**self.user, "role": "ucetni"})
        self.assertEqual(caught.exception.status_code, 403)
        other = Program(institution_id=self.inst, name_cs="Other", description_cs="Other", age_group="all")
        self.db.add(other)
        await self.db.commit()
        self.assertEqual([], await get_program_one_offs(self.db, str(self.inst), str(other.id), DAY, DAY))
        with self.assertRaises(HTTPException) as caught:
            await unified.delete_program_one_off(str(other.id), slot["id"], self.db, self.user)
        self.assertEqual(caught.exception.status_code, 404)

    async def test_invalid_input_and_program_bounds(self):
        for values in [("2026-02-30", "13:30", "15:00"), (DAY, "15:00", "13:30"), (DAY, "13:30", "13:30")]:
            with self.assertRaises(HTTPException):
                await self.add(*values)
        with self.assertRaises(ValidationError):
            await self.add(start="25:00")
        self.program.end_date = datetime(2026, 9, 21, tzinfo=timezone.utc)
        await self.db.commit()
        with self.assertRaises(HTTPException):
            await self.add()
        self.assertEqual(0, await self.db.scalar(select(func.count()).select_from(ProgramOneOffAvailability)))

    async def test_booking_open_gate_and_program_end_remain_effective(self):
        await self.add()
        self.program.booking_opens_at = datetime(2026, 9, 20, tzinfo=timezone.utc)
        await self.db.commit()
        self.assertEqual([], await self.daily())
        self.assertIn(SLOT, [s["time"] for s in await self.internal()])
        with self.assertRaises(HTTPException) as caught:
            await self.submit()
        self.assertEqual(caught.exception.status_code, 409)
        self.program.booking_opens_at = None
        self.program.end_date = datetime(2026, 9, 21, tzinfo=timezone.utc)
        await self.db.commit()
        self.assertEqual([], await self.daily())
        self.assertEqual((await self.internal())[0]["status"], "outside_base_availability")
        with self.assertRaises(HTTPException) as caught:
            await self.submit()
        self.assertEqual(caught.exception.status_code, 400)

    async def test_lecturer_unavailability_is_not_bypassed(self):
        await self.add()
        self.program.assigned_lecturer_id = self.user_id
        self.program.collision_resources = ["lecturer"]
        self.db.add(LecturerAvailability(institution_id=self.inst, lecturer_id=self.user_id,
            day_of_week=1, start_time="09:00", end_time="10:30", is_recurring=True))
        await self.db.commit()
        self.assertEqual(next(s for s in await self.internal() if s["time"] == SLOT)["status"], "blocked_lecturer")
        with self.assertRaises(HTTPException) as caught:
            await self.submit()
        self.assertEqual(caught.exception.status_code, 409)

    async def test_parallel_and_room_collision_remain_effective(self):
        await self.add(day="2026-09-26")
        room = Room(institution_id=self.inst, name="Shared room")
        self.db.add(room)
        await self.db.commit()
        other = Program(institution_id=self.inst, name_cs="Other", description_cs="Other", age_group="all", room_id=room.id, allow_parallel=False)
        self.db.add(other)
        await self.db.commit()
        self.program.room_id = room.id
        self.program.collision_resources = ["room"]
        self.db.add(Reservation(institution_id=self.inst, program_id=other.id, date="2026-09-26", time_block=SLOT,
            school_name="Other school", group_type="all", num_students=10,
            contact_name="Teacher", contact_email="other@example.org", contact_phone="123"))
        await self.db.commit()
        self.assertEqual((await self.internal("2026-09-26"))[0]["status"], "blocked_parallel")
        other.allow_parallel = True
        await self.db.commit()
        self.assertEqual((await self.internal("2026-09-26"))[0]["status"], "blocked_room")
        self.assertFalse(next(row for row in await self.monthly() if row["date"] == "2026-09-26")["has_availability"])
        with self.assertRaises(HTTPException) as caught:
            await self.submit(day="2026-09-26")
        self.assertEqual(caught.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
