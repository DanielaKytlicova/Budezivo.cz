"""
Statistics routes with real data from database.
Provides data for charts, reports, and CSV export.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta, date as date_type
from collections import defaultdict
from typing import Optional, List
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract, case
from pydantic import BaseModel
import csv
import io

from core.security import get_current_user
from database.supabase import get_db
from database.models import (
    AvailabilityBlock,
    AvailabilityException,
    LecturerAvailability,
    LecturerTimeOff,
    Program,
    Reservation,
    Institution,
    User,
    UserCalendarIntegration,
)
from database.supabase_repositories import InstitutionRepositorySupabase
from services.plan_service import require_feature
from services.usage_service import track_usage
from routes.availability import _expand_calendar_time_blocks, _program_validity_date, get_day_name
from services.collision_service import parse_time_block

router = APIRouter(prefix="/statistics", tags=["Statistics"])
logger = logging.getLogger(__name__)


# ============ Pydantic Models ============

class MonthlyStats(BaseModel):
    month: str
    year: int
    bookings: int
    students: int
    teachers: int


class CapacityMonthlyStats(BaseModel):
    month: str
    year: int
    offered_blocks: int
    reserved_blocks: int
    utilization_percent: float


class ProgramStats(BaseModel):
    program_id: str
    program_name: str
    bookings_count: int
    total_students: int
    total_teachers: int


class StatusStats(BaseModel):
    status: str
    count: int


class AgeGroupStats(BaseModel):
    age_group: str
    count: int


class OverviewStats(BaseModel):
    total_bookings: int
    total_students: int
    total_teachers: int
    total_visitors: int
    confirmed_bookings: int
    pending_bookings: int
    cancelled_bookings: int
    completed_bookings: int
    avg_group_size: float


class StatisticsResponse(BaseModel):
    overview: OverviewStats
    monthly: List[MonthlyStats]
    by_program: List[ProgramStats]
    by_status: List[StatusStats]
    by_age_group: List[AgeGroupStats]
    capacity_monthly: List[CapacityMonthlyStats]
    period: dict


# ============ Helper Functions ============

def get_school_year_dates(year: int = None):
    """Get start and end dates for school year (September to June)."""
    now = datetime.now(timezone.utc)
    if year is None:
        # Current school year
        if now.month >= 9:
            start_year = now.year
        else:
            start_year = now.year - 1
    else:
        start_year = year
    
    start_date = datetime(start_year, 9, 1, tzinfo=timezone.utc)
    end_date = datetime(start_year + 1, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
    return start_date, end_date


def get_semester_dates(year: int = None, semester: int = 1):
    """Get dates for semester (1 = Sep-Jan, 2 = Feb-Jun)."""
    now = datetime.now(timezone.utc)
    if year is None:
        if now.month >= 9:
            start_year = now.year
        else:
            start_year = now.year - 1
    else:
        start_year = year
    
    if semester == 1:
        start_date = datetime(start_year, 9, 1, tzinfo=timezone.utc)
        end_date = datetime(start_year + 1, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
    else:
        start_date = datetime(start_year + 1, 2, 1, tzinfo=timezone.utc)
        end_date = datetime(start_year + 1, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
    
    return start_date, end_date


def get_calendar_year_dates(year: int = None):
    """Get start and end dates for calendar year."""
    if year is None:
        year = datetime.now(timezone.utc).year
    start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    return start_date, end_date


def get_month_dates(year: int = None, month: int = None):
    """Get start and end dates for a specific month."""
    now = datetime.now(timezone.utc)
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    else:
        end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    
    return start_date, end_date


CZECH_MONTHS = {
    1: "Leden", 2: "Únor", 3: "Březen", 4: "Duben",
    5: "Květen", 6: "Červen", 7: "Červenec", 8: "Srpen",
    9: "Září", 10: "Říjen", 11: "Listopad", 12: "Prosinec"
}

AGE_GROUP_LABELS = {
    "ms_3_6": "MŠ (3-6 let)",
    "zs1_7_12": "ZŠ 1. stupeň (7-12)",
    "zs2_12_15": "ZŠ 2. stupeň (12-15)",
    "ss_14_18": "SŠ (14-18)",
    "gym_14_18": "Gymnázium (14-18)",
    "adults": "Dospělí",
    "all": "Všechny věkové skupiny",
}

STATUS_LABELS = {
    "pending": "Čekající",
    "confirmed": "Potvrzené",
    "cancelled": "Zrušené",
    "completed": "Dokončené",
    "no_show": "Nedostavil se",
}


PRAGUE_TZ = ZoneInfo("Europe/Prague")


@dataclass(frozen=True)
class _CapacityCandidate:
    """One possible reservation run used only by the statistics calculation."""

    program_id: str
    start_minute: int
    end_minute: int
    allow_parallel: bool
    collision_resources: frozenset[str]
    room_id: Optional[str]
    blocked_program_ids: frozenset[str]
    lecturer_ids: frozenset[str]
    same_program_limit: Optional[int]


def _statistics_time_to_minute(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        hours, minutes = value.split(":")
        return int(hours) * 60 + int(minutes)
    except (AttributeError, TypeError, ValueError):
        return None


def _statistics_block_range(time_block: str, duration: int) -> Optional[tuple[int, int]]:
    start, end = parse_time_block(time_block)
    if start is None:
        return None
    return start, end if end is not None else start + duration


def _statistics_ranges_overlap(
    start_a: int,
    end_a: int,
    start_b: int,
    end_b: int,
) -> bool:
    return start_a < end_b and start_b < end_a


def _statistics_exception_blocks_slot(
    start_minute: int,
    end_minute: int,
    exceptions: list,
) -> bool:
    for exception in exceptions:
        if exception.start_time is None and exception.end_time is None:
            return True
        exception_start = _statistics_time_to_minute(exception.start_time) or 0
        exception_end = _statistics_time_to_minute(exception.end_time) or 24 * 60
        if _statistics_ranges_overlap(start_minute, end_minute, exception_start, exception_end):
            return True
    return False


def _statistics_reporting_limit(program: Program) -> int:
    """Use one unit for unlimited programs so the chart has a finite denominator.

    ``NULL`` means unlimited in booking validation. A statistics graph cannot
    display an infinite denominator, so it counts one schedulable run per
    configured time block in that case.
    """
    try:
        limit = int(program.max_concurrent_bookings)
    except (TypeError, ValueError):
        return 1
    return limit if limit > 0 else 1


def _statistics_candidates_conflict(
    candidate: _CapacityCandidate,
    selected: list[_CapacityCandidate],
) -> bool:
    """Mirror booking conflict rules for a hypothetical reporting schedule."""
    for other in selected:
        if candidate.program_id == other.program_id:
            if not _statistics_ranges_overlap(
                candidate.start_minute,
                candidate.end_minute,
                other.start_minute,
                other.end_minute,
            ):
                continue
            overlapping_same_program = sum(
                1
                for item in selected
                if item.program_id == candidate.program_id
                and _statistics_ranges_overlap(
                    candidate.start_minute,
                    candidate.end_minute,
                    item.start_minute,
                    item.end_minute,
                )
            )
            return overlapping_same_program >= (candidate.same_program_limit or 1)

        if not _statistics_ranges_overlap(
            candidate.start_minute,
            candidate.end_minute,
            other.start_minute,
            other.end_minute,
        ):
            continue

        if not candidate.allow_parallel or not other.allow_parallel:
            return True

        if (
            "lecturer" in candidate.collision_resources
            and "lecturer" in other.collision_resources
            and candidate.lecturer_ids
            and other.lecturer_ids
            and candidate.lecturer_ids.intersection(other.lecturer_ids)
        ):
            return True

        if (
            "room" in candidate.collision_resources
            and "room" in other.collision_resources
            and candidate.room_id
            and candidate.room_id == other.room_id
        ):
            return True

        if (
            other.program_id in candidate.blocked_program_ids
            or candidate.program_id in other.blocked_program_ids
        ):
            return True

    return False


def _statistics_max_additional_capacity(
    candidates: list[_CapacityCandidate],
    fixed_reservations: list[_CapacityCandidate],
) -> int:
    """Select the largest deterministic set of currently schedulable runs.

    Candidates are ordered by end time, which keeps the result stable and
    avoids counting several overlapping program windows as several physical
    runs. Existing reservations are fixed first; new candidates are added only
    when the same booking rules allow them to coexist.
    """
    available = [
        candidate
        for candidate in candidates
        if not _statistics_candidates_conflict(candidate, fixed_reservations)
    ]
    available.sort(key=lambda item: (item.end_minute, item.start_minute, item.program_id))

    selected: list[_CapacityCandidate] = []
    for candidate in available:
        if not _statistics_candidates_conflict(candidate, fixed_reservations + selected):
            selected.append(candidate)
    return len(selected)


def _statistics_lecturer_ids(program: Program, users: list[User]) -> set[str]:
    """Return active lecturers that the normal assignment pool can use."""
    program_id = str(program.id)
    configured_ids = {str(program.assigned_lecturer_id)} if program.assigned_lecturer_id else set()
    configured_ids.update(str(value) for value in (program.collision_lecturer_ids or []) if value)
    for user in users:
        supported = {str(value) for value in (user.supported_program_ids or [])}
        if program_id in supported:
            configured_ids.add(str(user.id))
    return {
        str(user.id)
        for user in users
        if str(user.id) in configured_ids
        and program_id not in {str(value) for value in (user.learning_program_ids or [])}
    }


def _statistics_lecturer_is_available(
    lecturer_id: str,
    day: date_type,
    start_minute: int,
    end_minute: int,
    availability_by_lecturer: dict[str, list[LecturerAvailability]],
    time_off_by_lecturer: dict[str, list[LecturerTimeOff]],
    lecturer_exceptions: dict[tuple[str, str], list[AvailabilityException]],
    blocks_by_lecturer: dict[str, list[AvailabilityBlock]],
    integrations_by_user_provider: dict[tuple[str, str], UserCalendarIntegration],
) -> bool:
    lecturer_blocks = availability_by_lecturer.get(lecturer_id, [])
    day_blocks = [
        block
        for block in lecturer_blocks
        if (block.is_recurring and block.day_of_week == day.weekday())
        or (not block.is_recurring and block.specific_date == day.isoformat())
    ]
    if day_blocks:
        in_schedule = any(
            (start := _statistics_time_to_minute(block.start_time)) is not None
            and (end := _statistics_time_to_minute(block.end_time)) is not None
            and start_minute >= start
            and end_minute <= end
            for block in day_blocks
        )
        if not in_schedule:
            return False
    elif lecturer_blocks:
        return False

    if _statistics_exception_blocks_slot(
        start_minute,
        end_minute,
        lecturer_exceptions.get((lecturer_id, day.isoformat()), []),
    ):
        return False

    for time_off in time_off_by_lecturer.get(lecturer_id, []):
        if time_off.start_date > day.isoformat() or time_off.end_date < day.isoformat():
            continue
        if time_off.start_time is None or time_off.end_time is None:
            return False
        off_start = _statistics_time_to_minute(time_off.start_time) or 0
        off_end = _statistics_time_to_minute(time_off.end_time) or 24 * 60
        if _statistics_ranges_overlap(start_minute, end_minute, off_start, off_end):
            return False

    local_start = datetime.combine(
        day,
        datetime.min.time().replace(minute=start_minute % 60, hour=start_minute // 60),
        tzinfo=PRAGUE_TZ,
    )
    local_end = datetime.combine(
        day,
        datetime.min.time().replace(minute=end_minute % 60, hour=end_minute // 60),
        tzinfo=PRAGUE_TZ,
    )
    for block in blocks_by_lecturer.get(lecturer_id, []):
        block_start = block.start_time
        block_end = block.end_time
        if block_start.tzinfo is None:
            block_start = block_start.replace(tzinfo=PRAGUE_TZ)
        if block_end.tzinfo is None:
            block_end = block_end.replace(tzinfo=PRAGUE_TZ)
        if block_end <= local_start or block_start >= local_end:
            continue
        if block.override:
            continue
        if block.source in ("google", "outlook"):
            provider = "google" if block.source == "google" else "microsoft"
            integration = integrations_by_user_provider.get((lecturer_id, provider))
            if not integration or not integration.is_active or not integration.import_enabled:
                continue
        return False

    return True


def _statistics_candidate_for_program(
    program: Program,
    time_block: str,
    lecturer_ids: set[str],
) -> Optional[_CapacityCandidate]:
    block_range = _statistics_block_range(time_block, program.duration or 60)
    if not block_range:
        return None
    start_minute, end_minute = block_range
    return _CapacityCandidate(
        program_id=str(program.id),
        start_minute=start_minute,
        end_minute=end_minute,
        allow_parallel=bool(program.allow_parallel),
        collision_resources=frozenset(program.collision_resources or []),
        room_id=str(program.room_id) if program.room_id else None,
        blocked_program_ids=frozenset(str(value) for value in (program.blocked_program_ids or [])),
        lecturer_ids=frozenset(lecturer_ids),
        same_program_limit=program.max_concurrent_bookings,
    )


async def _get_capacity_monthly(
    db: AsyncSession,
    institution_id,
    date_start: datetime,
    date_end: datetime,
) -> list[CapacityMonthlyStats]:
    """Calculate effective reservation capacity without changing booking logic.

    The old denominator counted every configured program window independently.
    This version builds hypothetical runs for each day, applies the same
    resource settings used by booking (program validity/exceptions, lecturer
    schedules/time-off, external blocks, rooms, parallel rules and concurrent
    limits), fixes already-created reservations, and then counts only the
    largest compatible set of additional runs. The helper is intentionally
    isolated to reporting; it never writes data or participates in booking.
    """
    range_start = date_start.strftime("%Y-%m-%d")
    range_end = date_end.strftime("%Y-%m-%d")

    all_programs_result = await db.execute(select(Program).where(and_(
        Program.institution_id == institution_id,
        Program.deleted_at.is_(None),
    )))
    all_programs = all_programs_result.scalars().all()
    programs = [
        program
        for program in all_programs
        if program.status == "active" and program.is_published
    ]
    programs_by_id = {str(program.id): program for program in all_programs}

    reservations_result = await db.execute(select(Reservation).where(and_(
        Reservation.institution_id == institution_id,
        Reservation.date >= range_start,
        Reservation.date <= range_end,
        Reservation.deleted_at.is_(None),
        Reservation.status != "cancelled",
    )))
    reservations_by_date: dict[str, list[Reservation]] = defaultdict(list)
    reserved_by_month: dict[tuple[int, int], int] = defaultdict(int)
    for reservation in reservations_result.scalars().all():
        reservation_date = str(reservation.date)
        try:
            parsed = datetime.strptime(reservation_date, "%Y-%m-%d")
        except ValueError:
            continue
        reservations_by_date[reservation_date].append(reservation)
        reserved_by_month[(parsed.year, parsed.month)] += 1

    exceptions_result = await db.execute(select(AvailabilityException).where(and_(
        AvailabilityException.institution_id == institution_id,
        AvailabilityException.date >= range_start,
        AvailabilityException.date <= range_end,
        AvailabilityException.scope_type.in_(["program", "lecturer"]),
    )))
    program_exceptions: dict[tuple[str, str], list[AvailabilityException]] = defaultdict(list)
    lecturer_exceptions: dict[tuple[str, str], list[AvailabilityException]] = defaultdict(list)
    for exception in exceptions_result.scalars().all():
        key = (str(exception.scope_id), str(exception.date))
        if exception.scope_type == "program":
            program_exceptions[key].append(exception)
        else:
            lecturer_exceptions[key].append(exception)

    users_result = await db.execute(select(User).where(and_(
        User.institution_id == institution_id,
        User.role.in_(("lektor", "edukator", "admin", "spravce")),
        User.status == "active",
        User.deleted_at.is_(None),
    )))
    users = users_result.scalars().all()
    availability_result = await db.execute(select(LecturerAvailability).where(
        LecturerAvailability.institution_id == institution_id
    ))
    time_off_result = await db.execute(select(LecturerTimeOff).where(and_(
        LecturerTimeOff.institution_id == institution_id,
        LecturerTimeOff.start_date <= range_end,
        LecturerTimeOff.end_date >= range_start,
    )))
    availability_by_lecturer: dict[str, list[LecturerAvailability]] = defaultdict(list)
    time_off_by_lecturer: dict[str, list[LecturerTimeOff]] = defaultdict(list)
    for availability in availability_result.scalars().all():
        availability_by_lecturer[str(availability.lecturer_id)].append(availability)
    for time_off in time_off_result.scalars().all():
        time_off_by_lecturer[str(time_off.lecturer_id)].append(time_off)

    block_start = datetime.combine(date_start.date(), datetime.min.time(), tzinfo=PRAGUE_TZ)
    block_end = datetime.combine(date_end.date(), datetime.max.time(), tzinfo=PRAGUE_TZ)
    blocks_result = await db.execute(select(AvailabilityBlock).where(and_(
        AvailabilityBlock.institution_id == institution_id,
        AvailabilityBlock.end_time > block_start,
        AvailabilityBlock.start_time < block_end,
    )))
    blocks_by_lecturer: dict[str, list[AvailabilityBlock]] = defaultdict(list)
    for block in blocks_result.scalars().all():
        blocks_by_lecturer[str(block.user_id)].append(block)

    integrations_result = await db.execute(select(UserCalendarIntegration).where(and_(
        UserCalendarIntegration.institution_id == institution_id,
        UserCalendarIntegration.is_active.is_(True),
        UserCalendarIntegration.import_enabled.is_(True),
    )))
    integrations_by_user_provider = {
        (str(integration.user_id), integration.provider): integration
        for integration in integrations_result.scalars().all()
    }

    lecturer_pool_by_program = {
        str(program.id): _statistics_lecturer_ids(program, users)
        for program in programs
    }
    qualified_pool_by_program = {
        str(program.id): {
            str(user.id)
            for user in users
            if str(program.id) in {
                str(value) for value in (user.supported_program_ids or [])
            }
            and str(program.id) not in {
                str(value) for value in (user.learning_program_ids or [])
            }
        }
        for program in programs
    }

    effective_capacity_by_month: dict[tuple[int, int], int] = defaultdict(int)
    day = date_start.date()
    last_day = date_end.date()
    while day <= last_day:
        date_str = day.isoformat()
        day_name = get_day_name(day)
        candidates: list[_CapacityCandidate] = []
        for program in programs:
            program_start = _program_validity_date(program.start_date)
            program_end = _program_validity_date(program.end_date)
            if program_start and day < program_start:
                continue
            if program_end and day > program_end:
                continue
            available_days = program.available_days or [
                "monday", "tuesday", "wednesday", "thursday", "friday"
            ]
            if day_name not in available_days:
                continue

            pool = lecturer_pool_by_program[str(program.id)]
            for time_block in _expand_calendar_time_blocks(
                program.time_blocks or ["09:00-10:30"],
                program.duration or 60,
            ):
                block_range = _statistics_block_range(time_block, program.duration or 60)
                if not block_range:
                    continue
                start_minute, end_minute = block_range
                if _statistics_exception_blocks_slot(
                    start_minute,
                    end_minute,
                    program_exceptions.get((str(program.id), date_str), []),
                ):
                    continue

                available_lecturers = {
                    lecturer_id
                    for lecturer_id in pool
                    if _statistics_lecturer_is_available(
                        lecturer_id,
                        day,
                        start_minute,
                        end_minute,
                        availability_by_lecturer,
                        time_off_by_lecturer,
                        lecturer_exceptions,
                        blocks_by_lecturer,
                        integrations_by_user_provider,
                    )
                }
                if "lecturer" in (program.collision_resources or []):
                    required = getattr(program, "required_lecturers", 1) or 1
                    if required > 1:
                        available_qualified = available_lecturers.intersection(
                            qualified_pool_by_program[str(program.id)]
                        )
                        if len(available_qualified) < required:
                            continue
                    has_explicit_pool = bool(
                        program.assigned_lecturer_id or program.collision_lecturer_ids
                    )
                    if len(available_lecturers) < required and (
                        bool(pool) or has_explicit_pool or required > 1
                    ):
                        continue
                else:
                    available_lecturers = set()

                candidate = _statistics_candidate_for_program(
                    program, time_block, available_lecturers
                )
                if not candidate:
                    continue
                # A finite concurrent limit means the system can accept that
                # many reservations in one overlapping program slot.
                candidates.extend([candidate] * _statistics_reporting_limit(program))

        fixed_reservations: list[_CapacityCandidate] = []
        for reservation in reservations_by_date.get(date_str, []):
            program = programs_by_id.get(str(reservation.program_id))
            if not program:
                continue
            assigned_lecturers = {
                str(reservation.assigned_lecturer_id)
            } if reservation.assigned_lecturer_id else set()
            assigned_lecturers.update(
                str(value)
                for value in (reservation.assigned_lecturer_ids or [])
                if value
            )
            if not assigned_lecturers:
                assigned_lecturers = lecturer_pool_by_program.get(str(program.id), set())
            candidate = _statistics_candidate_for_program(
                program,
                str(reservation.time_block),
                assigned_lecturers,
            )
            if candidate:
                fixed_reservations.append(candidate)

        effective_capacity_by_month[(day.year, day.month)] += (
            len(reservations_by_date.get(date_str, []))
            + _statistics_max_additional_capacity(candidates, fixed_reservations)
        )
        day += timedelta(days=1)

    result = []
    cursor = date_start.replace(day=1)
    while cursor <= date_end:
        key = (cursor.year, cursor.month)
        offered = effective_capacity_by_month[key]
        reserved = reserved_by_month[key]
        result.append(CapacityMonthlyStats(
            month=CZECH_MONTHS[cursor.month],
            year=cursor.year,
            offered_blocks=offered,
            reserved_blocks=reserved,
            utilization_percent=round((reserved / offered) * 100, 1) if offered else 0,
        ))
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)
    return result


# ============ Main Statistics Endpoint ============

@router.get("", response_model=StatisticsResponse)
async def get_statistics(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    period_type: str = Query("month", description="month, school_year, semester, calendar_year, custom"),
    year: Optional[int] = Query(None, description="Year for the period"),
    month: Optional[int] = Query(None, description="Month (1-12) for month period"),
    semester: Optional[int] = Query(None, description="Semester (1 or 2) for semester period"),
    start_date: Optional[str] = Query(None, description="Start date for custom period (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date for custom period (YYYY-MM-DD)"),
):
    """
    Get comprehensive statistics for the institution.
    
    Period types:
    - month: Current month (default) or specified month/year
    - school_year: September to June (academic year)
    - semester: First (Sep-Jan) or second (Feb-Jun) semester
    - calendar_year: January to December
    - custom: Custom date range
    """
    import uuid
    institution_id = uuid.UUID(current_user["institution_id"])
    
    # Determine date range based on period type
    if period_type == "month":
        date_start, date_end = get_month_dates(year, month)
        period_label = f"{CZECH_MONTHS[date_start.month]} {date_start.year}"
    elif period_type == "school_year":
        date_start, date_end = get_school_year_dates(year)
        period_label = f"Školní rok {date_start.year}/{date_end.year}"
    elif period_type == "semester":
        date_start, date_end = get_semester_dates(year, semester or 1)
        sem_label = "1. pololetí" if (semester or 1) == 1 else "2. pololetí"
        period_label = f"{sem_label} {date_start.year}/{date_end.year}"
    elif period_type == "calendar_year":
        date_start, date_end = get_calendar_year_dates(year)
        period_label = f"Rok {date_start.year}"
    elif period_type == "custom" and start_date and end_date:
        date_start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        date_end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        period_label = f"{start_date} - {end_date}"
    else:
        # Default to current month
        date_start, date_end = get_month_dates()
        period_label = f"{CZECH_MONTHS[date_start.month]} {date_start.year}"
    
    # Convert dates to string format for comparison with date column
    start_str = date_start.strftime("%Y-%m-%d")
    end_str = date_end.strftime("%Y-%m-%d")
    
    # Base query filter
    base_filter = and_(
        Reservation.institution_id == institution_id,
        Reservation.date >= start_str,
        Reservation.date <= end_str,
        Reservation.deleted_at.is_(None)
    )
    
    # ============ Overview Stats ============
    overview_result = await db.execute(
        select(
            func.count(Reservation.id).label("total"),
            func.coalesce(func.sum(Reservation.num_students), 0).label("students"),
            func.coalesce(func.sum(Reservation.num_teachers), 0).label("teachers"),
            func.count(case((Reservation.status == "confirmed", 1))).label("confirmed"),
            func.count(case((Reservation.status == "pending", 1))).label("pending"),
            func.count(case((Reservation.status == "cancelled", 1))).label("cancelled"),
            func.count(case((Reservation.status == "completed", 1))).label("completed"),
        ).where(base_filter)
    )
    overview_row = overview_result.fetchone()
    
    total_bookings = overview_row.total or 0
    total_students = int(overview_row.students or 0)
    total_teachers = int(overview_row.teachers or 0)
    
    overview = OverviewStats(
        total_bookings=total_bookings,
        total_students=total_students,
        total_teachers=total_teachers,
        total_visitors=total_students + total_teachers,
        confirmed_bookings=overview_row.confirmed or 0,
        pending_bookings=overview_row.pending or 0,
        cancelled_bookings=overview_row.cancelled or 0,
        completed_bookings=overview_row.completed or 0,
        avg_group_size=round(total_students / total_bookings, 1) if total_bookings > 0 else 0,
    )
    
    # ============ Monthly Stats ============
    # Get data for each month in the period
    monthly_data = []
    current = date_start.replace(day=1)
    while current <= date_end:
        month_start = current.strftime("%Y-%m-%d")
        if current.month == 12:
            next_month = current.replace(year=current.year + 1, month=1)
        else:
            next_month = current.replace(month=current.month + 1)
        month_end = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")
        
        month_result = await db.execute(
            select(
                func.count(Reservation.id).label("bookings"),
                func.coalesce(func.sum(Reservation.num_students), 0).label("students"),
                func.coalesce(func.sum(Reservation.num_teachers), 0).label("teachers"),
            ).where(and_(
                Reservation.institution_id == institution_id,
                Reservation.date >= month_start,
                Reservation.date <= month_end,
                Reservation.deleted_at.is_(None),
                Reservation.status != "cancelled"
            ))
        )
        month_row = month_result.fetchone()
        
        monthly_data.append(MonthlyStats(
            month=CZECH_MONTHS[current.month],
            year=current.year,
            bookings=month_row.bookings or 0,
            students=int(month_row.students or 0),
            teachers=int(month_row.teachers or 0),
        ))
        
        current = next_month
    
    # ============ By Program Stats ============
    program_result = await db.execute(
        select(
            Reservation.program_id,
            Program.name_cs,
            func.count(Reservation.id).label("bookings"),
            func.coalesce(func.sum(Reservation.num_students), 0).label("students"),
            func.coalesce(func.sum(Reservation.num_teachers), 0).label("teachers"),
        )
        .join(Program, Reservation.program_id == Program.id)
        .where(and_(base_filter, Reservation.status != "cancelled"))
        .group_by(Reservation.program_id, Program.name_cs)
        .order_by(func.count(Reservation.id).desc())
        .limit(10)
    )
    
    by_program = [
        ProgramStats(
            program_id=str(row.program_id),
            program_name=row.name_cs,
            bookings_count=row.bookings,
            total_students=int(row.students),
            total_teachers=int(row.teachers),
        )
        for row in program_result.fetchall()
    ]
    
    # ============ By Status Stats ============
    status_result = await db.execute(
        select(
            Reservation.status,
            func.count(Reservation.id).label("count"),
        )
        .where(and_(
            Reservation.institution_id == institution_id,
            Reservation.date >= start_str,
            Reservation.date <= end_str,
            Reservation.deleted_at.is_(None)
        ))
        .group_by(Reservation.status)
    )
    
    by_status = [
        StatusStats(
            status=STATUS_LABELS.get(row.status, row.status),
            count=row.count,
        )
        for row in status_result.fetchall()
    ]
    
    # ============ By Age Group Stats ============
    age_result = await db.execute(
        select(
            Reservation.group_type,
            func.count(Reservation.id).label("count"),
        )
        .where(and_(base_filter, Reservation.status != "cancelled"))
        .group_by(Reservation.group_type)
        .order_by(func.count(Reservation.id).desc())
    )
    
    by_age_group = [
        AgeGroupStats(
            age_group=AGE_GROUP_LABELS.get(row.group_type, row.group_type),
            count=row.count,
        )
        for row in age_result.fetchall()
    ]

    capacity_monthly = await _get_capacity_monthly(
        db, institution_id, date_start, date_end
    )
    
    return StatisticsResponse(
        overview=overview,
        monthly=monthly_data,
        by_program=by_program,
        by_status=by_status,
        by_age_group=by_age_group,
        capacity_monthly=capacity_monthly,
        period={
            "type": period_type,
            "label": period_label,
            "start": start_str,
            "end": end_str,
        }
    )


# ============ CSV Export ============

@router.get("/export/csv")
async def export_statistics_csv(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    period_type: str = Query("month"),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    semester: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    export_type: str = Query("reservations", description="reservations, summary, programs"),
    _guard=Depends(require_feature("data_export")),
):
    """
    Export statistics to CSV.
    
    Requires PRO plan or admin exception.
    """
    import uuid
    institution_id = uuid.UUID(current_user["institution_id"])
    
    # Check if user has PRO access
    institution_repo = InstitutionRepositorySupabase(db)
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    
    if not institution:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")
    
    is_pro = institution.get("plan") in ["standard", "premium", "pro", "pro_plus"]
    csv_export_exception = institution.get("pro_settings", {}).get("csv_export_exception", False)
    
    if not is_pro and not csv_export_exception:
        raise HTTPException(
            status_code=403, 
            detail="Export CSV je dostupný pouze pro PRO verzi. Kontaktujte podporu pro výjimku."
        )
    
    # Determine date range
    if period_type == "month":
        date_start, date_end = get_month_dates(year, month)
    elif period_type == "school_year":
        date_start, date_end = get_school_year_dates(year)
    elif period_type == "semester":
        date_start, date_end = get_semester_dates(year, semester or 1)
    elif period_type == "calendar_year":
        date_start, date_end = get_calendar_year_dates(year)
    elif period_type == "custom" and start_date and end_date:
        date_start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        date_end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    else:
        date_start, date_end = get_month_dates()
    
    start_str = date_start.strftime("%Y-%m-%d")
    end_str = date_end.strftime("%Y-%m-%d")
    
    # Create CSV buffer
    output = io.StringIO()
    
    if export_type == "reservations":
        # Export all reservations
        result = await db.execute(
            select(Reservation, Program.name_cs)
            .join(Program, Reservation.program_id == Program.id)
            .where(and_(
                Reservation.institution_id == institution_id,
                Reservation.date >= start_str,
                Reservation.date <= end_str,
                Reservation.deleted_at.is_(None)
            ))
            .order_by(Reservation.date)
        )
        
        writer = csv.writer(output, delimiter=';')
        writer.writerow([
            "Datum", "Čas", "Program", "Škola", "Kontakt", "Email", "Telefon",
            "Počet žáků", "Počet pedagogů", "Věková skupina", "Status", "Poznámky"
        ])
        
        for row in result.fetchall():
            res = row[0]
            program_name = row[1]
            writer.writerow([
                res.date,
                res.time_block,
                program_name,
                res.school_name,
                res.contact_name,
                res.contact_email,
                res.contact_phone,
                res.num_students,
                res.num_teachers,
                AGE_GROUP_LABELS.get(res.group_type, res.group_type),
                STATUS_LABELS.get(res.status, res.status),
                res.notes or "",
            ])
        
        filename = f"rezervace_{start_str}_{end_str}.csv"
        
    elif export_type == "summary":
        # Export monthly summary
        writer = csv.writer(output, delimiter=';')
        writer.writerow(["Měsíc", "Rok", "Počet rezervací", "Počet žáků", "Počet pedagogů", "Celkem návštěvníků"])
        
        current = date_start.replace(day=1)
        while current <= date_end:
            month_start = current.strftime("%Y-%m-%d")
            if current.month == 12:
                next_month = current.replace(year=current.year + 1, month=1)
            else:
                next_month = current.replace(month=current.month + 1)
            month_end = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")
            
            month_result = await db.execute(
                select(
                    func.count(Reservation.id).label("bookings"),
                    func.coalesce(func.sum(Reservation.num_students), 0).label("students"),
                    func.coalesce(func.sum(Reservation.num_teachers), 0).label("teachers"),
                ).where(and_(
                    Reservation.institution_id == institution_id,
                    Reservation.date >= month_start,
                    Reservation.date <= month_end,
                    Reservation.deleted_at.is_(None),
                    Reservation.status != "cancelled"
                ))
            )
            month_row = month_result.fetchone()
            
            students = int(month_row.students or 0)
            teachers = int(month_row.teachers or 0)
            
            writer.writerow([
                CZECH_MONTHS[current.month],
                current.year,
                month_row.bookings or 0,
                students,
                teachers,
                students + teachers,
            ])
            
            current = next_month
        
        filename = f"souhrn_{start_str}_{end_str}.csv"
        
    elif export_type == "programs":
        # Export by program
        writer = csv.writer(output, delimiter=';')
        writer.writerow(["Program", "Počet rezervací", "Počet žáků", "Počet pedagogů", "Celkem návštěvníků", "Průměrná velikost skupiny"])
        
        program_result = await db.execute(
            select(
                Program.name_cs,
                func.count(Reservation.id).label("bookings"),
                func.coalesce(func.sum(Reservation.num_students), 0).label("students"),
                func.coalesce(func.sum(Reservation.num_teachers), 0).label("teachers"),
            )
            .join(Program, Reservation.program_id == Program.id)
            .where(and_(
                Reservation.institution_id == institution_id,
                Reservation.date >= start_str,
                Reservation.date <= end_str,
                Reservation.deleted_at.is_(None),
                Reservation.status != "cancelled"
            ))
            .group_by(Program.name_cs)
            .order_by(func.count(Reservation.id).desc())
        )
        
        for row in program_result.fetchall():
            students = int(row.students or 0)
            teachers = int(row.teachers or 0)
            bookings = row.bookings or 0
            avg_size = round(students / bookings, 1) if bookings > 0 else 0
            
            writer.writerow([
                row.name_cs,
                bookings,
                students,
                teachers,
                students + teachers,
                avg_size,
            ])
        
        filename = f"programy_{start_str}_{end_str}.csv"
    else:
        raise HTTPException(status_code=400, detail="Neplatný typ exportu")
    
    # Return CSV file
    output.seek(0)
    
    # Add BOM for Excel UTF-8 compatibility
    bom = '\ufeff'
    content = bom + output.getvalue()
    
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# ============ Legacy endpoints for backwards compatibility ============

@router.get("/bookings-over-time")
async def get_bookings_over_time(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _guard=Depends(require_feature("advanced_stats")),
):
    """Get bookings over time data for charts (last 6 months)."""
    import uuid
    institution_id = uuid.UUID(current_user["institution_id"])
    
    now = datetime.now(timezone.utc)
    labels = []
    data = []
    
    for i in range(5, -1, -1):
        month_date = now - timedelta(days=i * 30)
        month_start = month_date.replace(day=1).strftime("%Y-%m-%d")
        if month_date.month == 12:
            next_month = month_date.replace(year=month_date.year + 1, month=1)
        else:
            next_month = month_date.replace(month=month_date.month + 1)
        month_end = (next_month.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
        
        result = await db.execute(
            select(func.count(Reservation.id))
            .where(and_(
                Reservation.institution_id == institution_id,
                Reservation.date >= month_start,
                Reservation.date <= month_end,
                Reservation.deleted_at.is_(None),
                Reservation.status != "cancelled"
            ))
        )
        count = result.scalar() or 0
        
        labels.append(CZECH_MONTHS[month_date.month][:3])
        data.append(count)
    
    return {"labels": labels, "data": data}


@router.get("/popular-programs")
async def get_popular_programs(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _guard=Depends(require_feature("advanced_stats")),
):
    """Get popular programs data for charts."""
    import uuid
    institution_id = uuid.UUID(current_user["institution_id"])
    
    # Last 6 months
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=180)).strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")
    
    result = await db.execute(
        select(
            Program.name_cs,
            func.count(Reservation.id).label("count"),
        )
        .join(Program, Reservation.program_id == Program.id)
        .where(and_(
            Reservation.institution_id == institution_id,
            Reservation.date >= start_date,
            Reservation.date <= end_date,
            Reservation.deleted_at.is_(None),
            Reservation.status != "cancelled"
        ))
        .group_by(Program.name_cs)
        .order_by(func.count(Reservation.id).desc())
        .limit(5)
    )
    
    rows = result.fetchall()
    labels = [row.name_cs for row in rows]
    data = [row.count for row in rows]
    
    return {"labels": labels, "data": data}



# ============ Advanced Analytics ============


@router.get("/heatmap")
async def get_heatmap(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    year: int = Query(default=None),
    month: int = Query(default=None),
    _guard=Depends(require_feature("advanced_stats")),
):
    """Heatmap: count of bookings by day-of-week x time_block."""
    from sqlalchemy import text as sql_text

    institution_id = current_user["institution_id"]
    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month

    from calendar import monthrange
    _, last_day = monthrange(y, m)
    start = f"{y}-{m:02d}-01"
    end = f"{y}-{m:02d}-{last_day}"

    result = await db.execute(
        sql_text("""
            SELECT
                EXTRACT(DOW FROM r.date::date) as dow,
                r.time_block,
                COUNT(r.id) as cnt
            FROM reservations r
            WHERE r.institution_id = :inst_id
              AND r.date >= :start_date
              AND r.date <= :end_date
              AND r.deleted_at IS NULL
              AND r.status != 'cancelled'
            GROUP BY dow, r.time_block
        """),
        {"inst_id": institution_id, "start_date": start, "end_date": end},
    )
    rows = result.fetchall()

    DAY_LABELS = ["Ne", "Po", "Út", "St", "Čt", "Pá", "So"]
    time_blocks = sorted(set(r.time_block for r in rows if r.time_block))
    heatmap = []
    for dow in range(7):
        row_data = {"day": DAY_LABELS[dow]}
        for tb in time_blocks:
            row_data[tb] = 0
        heatmap.append(row_data)

    for r in rows:
        dow_idx = int(r.dow)
        if 0 <= dow_idx <= 6 and r.time_block in time_blocks:
            heatmap[dow_idx][r.time_block] = r.cnt

    # Move Sunday to end (Czech week starts Monday)
    heatmap = heatmap[1:] + heatmap[:1]

    return {"time_blocks": time_blocks, "data": heatmap, "period": f"{y}-{m:02d}"}


@router.get("/trends")
async def get_trends(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    year: int = Query(default=None),
    _guard=Depends(require_feature("advanced_stats")),
):
    """Trend: monthly booking counts for current vs previous year."""
    institution_id = current_user["institution_id"]
    y = year or datetime.now(timezone.utc).year

    async def _monthly_counts(yr: int) -> list:
        from sqlalchemy import text as sql_text
        result = await db.execute(
            sql_text("""
                SELECT
                    EXTRACT(MONTH FROM r.date::date) as m,
                    COUNT(r.id) as cnt,
                    COALESCE(SUM(r.num_students), 0) as students
                FROM reservations r
                WHERE r.institution_id = :inst_id
                  AND EXTRACT(YEAR FROM r.date::date) = :yr
                  AND r.deleted_at IS NULL
                  AND r.status != 'cancelled'
                GROUP BY m
                ORDER BY m
            """),
            {"inst_id": institution_id, "yr": yr},
        )
        rows = result.fetchall()
        month_map = {int(r.m): {"bookings": r.cnt, "students": int(r.students)} for r in rows}
        return [
            {"month": i, "bookings": month_map.get(i, {}).get("bookings", 0),
             "students": month_map.get(i, {}).get("students", 0)}
            for i in range(1, 13)
        ]

    MONTH_LABELS = ["Led", "Úno", "Bře", "Dub", "Kvě", "Čer", "Črc", "Srp", "Zář", "Říj", "Lis", "Pro"]
    current = await _monthly_counts(y)
    previous = await _monthly_counts(y - 1)

    chart_data = []
    for i in range(12):
        chart_data.append({
            "name": MONTH_LABELS[i],
            f"{y}": current[i]["bookings"],
            f"{y - 1}": previous[i]["bookings"],
            f"Žáci {y}": current[i]["students"],
        })

    return {"chart_data": chart_data, "current_year": y, "previous_year": y - 1}


@router.get("/top-schools")
async def get_top_schools(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    year: int = Query(default=None),
    month: int = Query(default=None),
    limit: int = Query(default=10, le=50),
    _guard=Depends(require_feature("advanced_stats")),
):
    """Top schools by booking count in given period."""
    from sqlalchemy import text as sql_text

    institution_id = current_user["institution_id"]
    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month

    from calendar import monthrange
    _, last_day = monthrange(y, m)
    start = f"{y}-{m:02d}-01"
    end = f"{y}-{m:02d}-{last_day}"

    result = await db.execute(
        sql_text("""
            SELECT
                r.school_name,
                r.contact_email,
                COUNT(r.id) as bookings,
                COALESCE(SUM(r.num_students), 0) as total_students,
                COALESCE(SUM(r.num_teachers), 0) as total_teachers
            FROM reservations r
            WHERE r.institution_id = :inst_id
              AND r.date >= :start_date
              AND r.date <= :end_date
              AND r.deleted_at IS NULL
              AND r.status != 'cancelled'
            GROUP BY r.school_name, r.contact_email
            ORDER BY bookings DESC
            LIMIT :lim
        """),
        {"inst_id": institution_id, "start_date": start, "end_date": end, "lim": limit},
    )
    rows = result.fetchall()

    return {
        "schools": [
            {
                "name": r.school_name or "Neznámá",
                "email": r.contact_email,
                "bookings": r.bookings,
                "students": int(r.total_students),
                "teachers": int(r.total_teachers),
            }
            for r in rows
        ],
        "period": f"{y}-{m:02d}",
    }


@router.get("/conversion")
async def get_conversion_rate(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    year: int = Query(default=None),
    month: int = Query(default=None),
    _guard=Depends(require_feature("advanced_stats")),
):
    """Conversion rate: created vs confirmed vs cancelled bookings."""
    institution_id = current_user["institution_id"]
    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month

    from sqlalchemy import text as sql_text

    from calendar import monthrange
    _, last_day = monthrange(y, m)
    start = f"{y}-{m:02d}-01"
    end = f"{y}-{m:02d}-{last_day}"

    result = await db.execute(
        sql_text("""
            SELECT r.status, COUNT(r.id) as cnt
            FROM reservations r
            WHERE r.institution_id = :inst_id
              AND r.date >= :start_date
              AND r.date <= :end_date
              AND r.deleted_at IS NULL
            GROUP BY r.status
        """),
        {"inst_id": institution_id, "start_date": start, "end_date": end},
    )
    rows = result.fetchall()
    status_map = {r.status: r.cnt for r in rows}

    total = sum(status_map.values())
    confirmed = status_map.get("confirmed", 0) + status_map.get("completed", 0)
    pending = status_map.get("pending", 0)
    cancelled = status_map.get("cancelled", 0)

    return {
        "total": total,
        "confirmed": confirmed,
        "pending": pending,
        "cancelled": cancelled,
        "conversion_rate": round((confirmed / total * 100), 1) if total > 0 else 0,
        "period": f"{y}-{m:02d}",
    }
