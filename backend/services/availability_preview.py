"""Batched, read-only collision evaluation for public availability previews.

The booking submit path intentionally keeps using ``check_booking_collision`` with
its transaction-scoped advisory lock.  This module only removes repeated SQL from
calendar/day previews by loading the relevant month (or day) into memory once.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date as date_type, datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    AvailabilityBlock,
    AvailabilityException,
    LecturerAvailability,
    LecturerTimeOff,
    Program,
    Reservation,
    User,
    UserCalendarIntegration,
)
from services.collision_service import (
    parse_time_block,
    program_collision_lecturer_ids,
    program_concurrent_limit,
    reservation_lecturer_ids,
    time_blocks_overlap,
)


LECTURER_ROLES = ("lektor", "edukator", "admin", "spravce")
PRAGUE = ZoneInfo("Europe/Prague")


def _minutes(value: str) -> int:
    hours, minutes = map(int, value.split(":"))
    return hours * 60 + minutes


@dataclass
class AvailabilityPreviewSnapshot:
    """All data needed to evaluate one program over a bounded date range."""

    institution_id: uuid.UUID
    program: Program
    programs: dict[str, Program]
    reservations_by_date: dict[str, list[Reservation]]
    exceptions_by_date: dict[str, list[AvailabilityException]]
    users: dict[str, User]
    lecturer_availability: dict[str, list[LecturerAvailability]]
    lecturer_time_off: dict[str, list[LecturerTimeOff]]
    availability_blocks: dict[str, list[AvailabilityBlock]]
    enabled_calendar_imports: set[tuple[str, str]]

    @classmethod
    async def load(
        cls,
        db: AsyncSession,
        institution_id: str,
        program_id: str,
        start_date: str,
        end_date: str,
    ) -> "AvailabilityPreviewSnapshot | None":
        inst_uuid = uuid.UUID(institution_id)
        prog_uuid = uuid.UUID(program_id)

        program_result = await db.execute(
            select(Program).where(and_(
                Program.id == prog_uuid,
                Program.institution_id == inst_uuid,
            ))
        )
        program = program_result.scalar_one_or_none()
        if not program:
            return None

        reservations_result = await db.execute(
            select(Reservation).where(and_(
                Reservation.institution_id == inst_uuid,
                Reservation.date >= start_date,
                Reservation.date <= end_date,
                Reservation.status != "cancelled",
            ))
        )
        reservations = list(reservations_result.scalars().all())

        program_ids = {program.id, *(row.program_id for row in reservations)}
        programs_result = await db.execute(select(Program).where(Program.id.in_(program_ids)))
        programs = {str(row.id): row for row in programs_result.scalars().all()}

        exceptions_result = await db.execute(
            select(AvailabilityException).where(and_(
                AvailabilityException.institution_id == inst_uuid,
                AvailabilityException.date >= start_date,
                AvailabilityException.date <= end_date,
            ))
        )

        users_result = await db.execute(
            select(User).where(and_(
                User.institution_id == inst_uuid,
                User.status == "active",
            ))
        )
        users = {str(row.id): row for row in users_result.scalars().all()}

        lecturer_ids = [uuid.UUID(value) for value in users]
        availability_rows = []
        time_off_rows = []
        block_rows = []
        integrations = []
        if lecturer_ids:
            availability_result = await db.execute(
                select(LecturerAvailability).where(and_(
                    LecturerAvailability.institution_id == inst_uuid,
                    LecturerAvailability.lecturer_id.in_(lecturer_ids),
                    or_(
                        LecturerAvailability.is_recurring.is_(True),
                        and_(
                            LecturerAvailability.specific_date >= start_date,
                            LecturerAvailability.specific_date <= end_date,
                        ),
                    ),
                ))
            )
            availability_rows = list(availability_result.scalars().all())

            time_off_result = await db.execute(
                select(LecturerTimeOff).where(and_(
                    LecturerTimeOff.institution_id == inst_uuid,
                    LecturerTimeOff.lecturer_id.in_(lecturer_ids),
                    LecturerTimeOff.start_date <= end_date,
                    LecturerTimeOff.end_date >= start_date,
                ))
            )
            time_off_rows = list(time_off_result.scalars().all())

            start_dt = datetime.combine(date_type.fromisoformat(start_date), time.min, PRAGUE).astimezone(timezone.utc)
            end_dt = datetime.combine(date_type.fromisoformat(end_date), time.max, PRAGUE).astimezone(timezone.utc)
            blocks_result = await db.execute(
                select(AvailabilityBlock).where(and_(
                    AvailabilityBlock.institution_id == inst_uuid,
                    AvailabilityBlock.user_id.in_(lecturer_ids),
                    AvailabilityBlock.end_time > start_dt,
                    AvailabilityBlock.start_time < end_dt,
                    AvailabilityBlock.override.is_(False),
                ))
            )
            block_rows = list(blocks_result.scalars().all())

            integrations_result = await db.execute(
                select(UserCalendarIntegration).where(and_(
                    UserCalendarIntegration.institution_id == inst_uuid,
                    UserCalendarIntegration.user_id.in_(lecturer_ids),
                    UserCalendarIntegration.is_active.is_(True),
                    UserCalendarIntegration.import_enabled.is_(True),
                ))
            )
            integrations = list(integrations_result.scalars().all())

        reservations_by_date: dict[str, list[Reservation]] = defaultdict(list)
        for row in reservations:
            reservations_by_date[str(row.date)].append(row)

        exceptions_by_date: dict[str, list[AvailabilityException]] = defaultdict(list)
        for row in exceptions_result.scalars().all():
            exceptions_by_date[str(row.date)].append(row)

        lecturer_availability: dict[str, list[LecturerAvailability]] = defaultdict(list)
        for row in availability_rows:
            lecturer_availability[str(row.lecturer_id)].append(row)

        lecturer_time_off: dict[str, list[LecturerTimeOff]] = defaultdict(list)
        for row in time_off_rows:
            lecturer_time_off[str(row.lecturer_id)].append(row)

        availability_blocks: dict[str, list[AvailabilityBlock]] = defaultdict(list)
        for row in block_rows:
            availability_blocks[str(row.user_id)].append(row)

        enabled_calendar_imports = {
            (str(row.user_id), str(row.provider)) for row in integrations
        }

        return cls(
            institution_id=inst_uuid,
            program=program,
            programs=programs,
            reservations_by_date=reservations_by_date,
            exceptions_by_date=exceptions_by_date,
            users=users,
            lecturer_availability=lecturer_availability,
            lecturer_time_off=lecturer_time_off,
            availability_blocks=availability_blocks,
            enabled_calendar_imports=enabled_calendar_imports,
        )

    def lecturer_has_any_availability_on_date(self, lecturer_id: str, date_str: str) -> bool:
        rows = self.lecturer_availability.get(str(lecturer_id), [])
        if not rows:
            return True
        day_of_week = date_type.fromisoformat(date_str).weekday()
        return any(
            (row.is_recurring and row.day_of_week == day_of_week)
            or (not row.is_recurring and row.specific_date == date_str)
            for row in rows
        )

    def lecturer_available_for_block(
        self, lecturer_id: str, date_str: str, time_block: str, duration: int
    ) -> bool:
        lecturer_id = str(lecturer_id)
        block_start, block_end = parse_time_block(time_block)
        if block_start is None:
            return True
        if block_end is None:
            block_end = block_start + duration

        rows = self.lecturer_availability.get(lecturer_id, [])
        day_of_week = date_type.fromisoformat(date_str).weekday()
        matching = [
            row for row in rows
            if (row.is_recurring and row.day_of_week == day_of_week)
            or (not row.is_recurring and row.specific_date == date_str)
        ]
        if rows and not matching:
            return False
        if matching and not any(
            block_start >= _minutes(row.start_time) and block_end <= _minutes(row.end_time)
            for row in matching
        ):
            return False

        for row in self.lecturer_time_off.get(lecturer_id, []):
            if not (row.start_date <= date_str <= row.end_date):
                continue
            if row.start_time is None or row.end_time is None:
                return False
            if block_start < _minutes(row.end_time) and block_end > _minutes(row.start_time):
                return False
        return True

    def _calendar_blocked(
        self, lecturer_id: str, date_str: str, time_block: str, duration: int
    ) -> bool:
        start_minute, end_minute = parse_time_block(time_block)
        if start_minute is None:
            return False
        if end_minute is None:
            end_minute = start_minute + duration
        day = date_type.fromisoformat(date_str)
        booking_start = datetime.combine(day, time(start_minute // 60, start_minute % 60), PRAGUE)
        booking_end = datetime.combine(day, time(end_minute // 60, end_minute % 60), PRAGUE)
        for row in self.availability_blocks.get(str(lecturer_id), []):
            provider = "microsoft" if row.source == "outlook" else row.source
            if row.source in {"google", "outlook"} and (
                str(lecturer_id), provider
            ) not in self.enabled_calendar_imports:
                continue
            row_start = row.start_time if row.start_time.tzinfo else row.start_time.replace(tzinfo=timezone.utc)
            row_end = row.end_time if row.end_time.tzinfo else row.end_time.replace(tzinfo=timezone.utc)
            if row_end > booking_start.astimezone(timezone.utc) and row_start < booking_end.astimezone(timezone.utc):
                return True
        return False

    def _reservation_overlaps(
        self, reservation: Reservation, time_block: str, duration: int
    ) -> bool:
        other = self.programs.get(str(reservation.program_id))
        return time_blocks_overlap(
            time_block,
            duration,
            reservation.time_block,
            other.duration if other else 60,
            self.program.preparation_time or 0,
            self.program.cleanup_time or 0,
            other.preparation_time if other else 0,
            other.cleanup_time if other else 0,
        )

    def _eligible_candidates(self) -> tuple[list[User], int]:
        candidate_ids: list[str] = []
        if self.program.assigned_lecturer_id:
            candidate_ids.append(str(self.program.assigned_lecturer_id))
        for lecturer_id in self.program.collision_lecturer_ids or []:
            value = str(lecturer_id)
            if value not in candidate_ids:
                candidate_ids.append(value)
        program_id = str(self.program.id)
        for user in self.users.values():
            if program_id in [str(value) for value in (user.supported_program_ids or [])]:
                value = str(user.id)
                if value not in candidate_ids:
                    candidate_ids.append(value)
        eligible = [
            self.users[value] for value in candidate_ids
            if value in self.users
            and self.users[value].deleted_at is None
            and program_id not in [str(pid) for pid in (self.users[value].learning_program_ids or [])]
        ]
        return eligible, len(candidate_ids)

    def has_assignable_main_lecturer(self, date_str: str, time_block: str) -> bool:
        if "lecturer" not in (self.program.collision_resources or []):
            return True
        candidates, configured_count = self._eligible_candidates()
        if not candidates:
            return configured_count == 0
        duration = self.program.duration or 60
        for user in candidates:
            lecturer_id = str(user.id)
            if not self.lecturer_available_for_block(lecturer_id, date_str, time_block, duration):
                continue
            if self._calendar_blocked(lecturer_id, date_str, time_block, duration):
                continue
            occupied = any(
                lecturer_id in reservation_lecturer_ids(row)
                and self._reservation_overlaps(row, time_block, duration)
                for row in self.reservations_by_date.get(date_str, [])
            )
            if not occupied:
                return True
        return False

    def _required_lecturer_capacity_met(self, date_str: str, time_block: str) -> bool:
        required = self.program.required_lecturers or 1
        if required <= 1:
            return True
        program_id = str(self.program.id)
        qualified = [
            user for user in self.users.values()
            if user.role in LECTURER_ROLES
            and user.deleted_at is None
            and program_id in [str(value) for value in (user.supported_program_ids or [])]
        ]
        duration = self.program.duration or 60
        available = 0
        for user in qualified:
            lecturer_id = str(user.id)
            occupied = any(
                lecturer_id in reservation_lecturer_ids(row)
                and self._reservation_overlaps(row, time_block, duration)
                for row in self.reservations_by_date.get(date_str, [])
            )
            if not occupied and self.lecturer_available_for_block(
                lecturer_id, date_str, time_block, duration
            ):
                available += 1
        return available >= required

    def is_blocked(self, date_str: str, time_block: str) -> bool:
        """Return the same boolean decision as the existing preview collision call."""
        program = self.program
        duration = program.duration or 60
        start_minute, end_minute = parse_time_block(time_block)
        if start_minute is None:
            start_minute, end_minute = 0, duration
        elif end_minute is None:
            end_minute = start_minute + duration

        for row in self.exceptions_by_date.get(date_str, []):
            if row.scope_type != "program" or str(row.scope_id) != str(program.id):
                continue
            if row.start_time is None and row.end_time is None:
                return True
            exception_start = _minutes(row.start_time) if row.start_time else 0
            exception_end = _minutes(row.end_time) if row.end_time else 24 * 60
            if start_minute < exception_end and end_minute > exception_start:
                return True

        if not self._required_lecturer_capacity_met(date_str, time_block):
            return True

        reservations = self.reservations_by_date.get(date_str, [])
        daily_limit = program.max_bookings_per_day
        try:
            daily_limit = int(daily_limit) if daily_limit not in (None, "") else None
        except (TypeError, ValueError):
            daily_limit = None
        if daily_limit and sum(str(row.program_id) == str(program.id) for row in reservations) >= daily_limit:
            return True

        concurrent_limit = program_concurrent_limit(program)
        if concurrent_limit is not None:
            overlapping = sum(
                str(row.program_id) == str(program.id)
                and time_blocks_overlap(
                    time_block, duration, row.time_block, duration,
                    program.preparation_time or 0, program.cleanup_time or 0,
                    program.preparation_time or 0, program.cleanup_time or 0,
                )
                for row in reservations
            )
            if overlapping >= concurrent_limit:
                return True

        allow_parallel = program.allow_parallel or False
        collision_resources = program.collision_resources or []
        blocked_program_ids = [str(value) for value in (program.blocked_program_ids or [])]
        program_room_id = str(program.room_id) if program.room_id else None
        for row in reservations:
            if str(row.program_id) == str(program.id) and not allow_parallel:
                continue
            other = self.programs.get(str(row.program_id))
            if not self._reservation_overlaps(row, time_block, duration):
                continue
            if not allow_parallel or not (other.allow_parallel if other else False):
                return True
            if "lecturer" in collision_resources:
                if reservation_lecturer_ids(row).intersection(program_collision_lecturer_ids(program)):
                    return True
            if "room" in collision_resources and program_room_id:
                if other and other.room_id and str(other.room_id) == program_room_id:
                    return True
            if str(row.program_id) in blocked_program_ids:
                return True
            if other and str(program.id) in [str(value) for value in (other.blocked_program_ids or [])]:
                return True
        return False
