"""
Central Availability Service.
Single source of truth for slot evaluation.

Architecture:
  Layer 1 (Base Availability): program time_blocks + available_days + exceptions
  Layer 2 (Collision): parallel rules, lecturer, room, program blocks

evaluate_slot() returns {status, reason} for any given program+date+time.
"""
import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from database.models import (
    Program, Reservation, Room,
    LecturerAvailability, LecturerTimeOff, AvailabilityException,
)
from services.collision_service import (
    parse_time_block, time_blocks_overlap,
    check_lecturer_available_for_block,
    check_any_lecturer_available_for_block,
)

logger = logging.getLogger(__name__)

# Slot status constants
STATUS_AVAILABLE = "available"
STATUS_BOOKED = "booked"
STATUS_BLOCKED_EXCEPTION = "blocked_exception"
STATUS_BLOCKED_LECTURER = "blocked_lecturer"
STATUS_BLOCKED_ROOM = "blocked_room"
STATUS_BLOCKED_PARALLEL = "blocked_parallel"
STATUS_BLOCKED_PROGRAM = "blocked_program"
STATUS_OUTSIDE_BASE = "outside_base_availability"


def _time_to_min(t: str) -> int:
    h, m = map(int, t.split(':'))
    return h * 60 + m


def _min_to_time(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


async def get_program_exceptions(
    db: AsyncSession,
    institution_id: str,
    program_id: str,
    date: str,
) -> list:
    """Get all availability exceptions for a program on a date."""
    result = await db.execute(
        select(AvailabilityException).where(and_(
            AvailabilityException.institution_id == uuid.UUID(institution_id),
            AvailabilityException.scope_type == 'program',
            AvailabilityException.scope_id == uuid.UUID(program_id),
            AvailabilityException.date == date,
        ))
    )
    return result.scalars().all()


async def get_lecturer_exceptions(
    db: AsyncSession,
    institution_id: str,
    lecturer_id: str,
    date: str,
) -> list:
    """Get all availability exceptions for a lecturer on a date."""
    result = await db.execute(
        select(AvailabilityException).where(and_(
            AvailabilityException.institution_id == uuid.UUID(institution_id),
            AvailabilityException.scope_type == 'lecturer',
            AvailabilityException.scope_id == uuid.UUID(lecturer_id),
            AvailabilityException.date == date,
        ))
    )
    return result.scalars().all()


def _slot_blocked_by_exception(slot_start: int, slot_end: int, exceptions: list) -> Optional[str]:
    """Check if a slot is blocked by any exception. Returns reason or None."""
    for exc in exceptions:
        if exc.start_time is None and exc.end_time is None:
            # All-day exception
            return exc.reason or "Jednorázová nedostupnost (celý den)"
        exc_start = _time_to_min(exc.start_time) if exc.start_time else 0
        exc_end = _time_to_min(exc.end_time) if exc.end_time else 24 * 60
        if slot_start < exc_end and slot_end > exc_start:
            return exc.reason or "Jednorázová nedostupnost"
    return None


async def _check_collision_layer(
    db: AsyncSession,
    institution_id: str,
    program: object,
    date: str,
    slot_start: int,
    slot_end: int,
    time_block_str: str,
) -> dict:
    """
    Layer 2: Check collision rules for a slot.
    Returns {status, reason} or None if no collision.
    """
    inst_uuid = uuid.UUID(institution_id)
    duration = program.duration or 60
    allow_parallel = program.allow_parallel if program.allow_parallel is not None else False
    collision_resources = program.collision_resources or []
    collision_lecturer_ids = program.collision_lecturer_ids or []
    blocked_program_ids = program.blocked_program_ids or []
    program_room_id = str(program.room_id) if program.room_id else None
    assigned_lecturer_id = str(program.assigned_lecturer_id) if program.assigned_lecturer_id else None

    # Get all non-cancelled reservations on this date
    result = await db.execute(
        select(Reservation).where(and_(
            Reservation.institution_id == inst_uuid,
            Reservation.date == date,
            Reservation.status != 'cancelled'
        ))
    )
    existing_reservations = result.scalars().all()

    # Check own-program bookings first (always blocks regardless of collision settings)
    for res in existing_reservations:
        if str(res.program_id) == str(program.id):
            res_start, res_end = parse_time_block(res.time_block)
            if res_end is None:
                res_end = res_start + duration
            if slot_start < res_end and slot_end > res_start:
                return {"status": STATUS_BOOKED, "reason": f"Obsazeno rezervací ({res.school_name or ''})"}

    # If parallel NOT allowed → any overlapping reservation blocks
    if not allow_parallel:
        for res in existing_reservations:
            other_prog = await db.execute(select(Program).where(Program.id == res.program_id))
            other_program = other_prog.scalar_one_or_none()
            other_duration = other_program.duration if other_program else 60
            res_start, res_end = parse_time_block(res.time_block)
            if res_end is None:
                res_end = res_start + other_duration
            if slot_start < res_end and slot_end > res_start:
                other_name = other_program.name_cs if other_program else "Jiný program"
                return {"status": STATUS_BLOCKED_PARALLEL, "reason": f"Blokováno: '{other_name}' (paralelní provoz zakázán)"}
        # No overlapping reservations found, check if other non-parallel programs have reservations
    else:
        # Parallel allowed — check specific collision resources
        for res in existing_reservations:
            if str(res.program_id) == str(program.id):
                continue  # Already checked above
            other_prog = await db.execute(select(Program).where(Program.id == res.program_id))
            other_program = other_prog.scalar_one_or_none()
            other_duration = other_program.duration if other_program else 60
            res_start, res_end = parse_time_block(res.time_block)
            if res_end is None:
                res_end = res_start + other_duration
            if slot_start >= res_end or slot_end <= res_start:
                continue  # No overlap

            # Other program doesn't allow parallel
            if other_program and not (other_program.allow_parallel if other_program.allow_parallel is not None else False):
                other_name = other_program.name_cs if other_program else "Jiný program"
                return {"status": STATUS_BLOCKED_PARALLEL, "reason": f"Blokováno: '{other_name}' neumožňuje paralelní provoz"}

            # Lecturer collision
            if "lecturer" in collision_resources:
                effective_lecturer = assigned_lecturer_id
                if effective_lecturer and res.assigned_lecturer_id and str(res.assigned_lecturer_id) == effective_lecturer:
                    other_name = other_program.name_cs if other_program else "Jiný program"
                    return {"status": STATUS_BLOCKED_LECTURER, "reason": f"Kolize lektora: přiřazen k '{other_name}'"}

            # Room collision
            if "room" in collision_resources and program_room_id:
                other_room_id = str(other_program.room_id) if other_program and other_program.room_id else None
                if other_room_id and other_room_id == program_room_id:
                    room_result = await db.execute(select(Room).where(Room.id == uuid.UUID(program_room_id)))
                    room = room_result.scalar_one_or_none()
                    room_name = room.name if room else "Místnost"
                    return {"status": STATUS_BLOCKED_ROOM, "reason": f"Kolize místnosti: '{room_name}' obsazena"}

            # Blocked program IDs
            other_pid = str(res.program_id) if res.program_id else None
            if other_pid and other_pid in blocked_program_ids:
                other_name = other_program.name_cs if other_program else "Jiný program"
                return {"status": STATUS_BLOCKED_PROGRAM, "reason": f"Blokace: nesmí běžet s '{other_name}'"}
            # Reverse check
            other_blocked = other_program.blocked_program_ids if other_program else []
            if other_blocked and str(program.id) in [str(x) for x in (other_blocked or [])]:
                other_name = other_program.name_cs if other_program else "Jiný program"
                return {"status": STATUS_BLOCKED_PROGRAM, "reason": f"Blokace: '{other_name}' zakazuje překryv"}

    # Lecturer availability check (when lecturer collision enabled)
    has_lecturer_collision = "lecturer" in collision_resources
    if has_lecturer_collision:
        if assigned_lecturer_id:
            available = await check_lecturer_available_for_block(
                db, assigned_lecturer_id, institution_id, date, time_block_str, duration
            )
            if not available:
                return {"status": STATUS_BLOCKED_LECTURER, "reason": "Lektor není dostupný v tomto čase"}
        elif collision_lecturer_ids:
            any_available = False
            for lid in collision_lecturer_ids:
                if await check_lecturer_available_for_block(db, str(lid), institution_id, date, time_block_str, duration):
                    any_available = True
                    break
            if not any_available:
                return {"status": STATUS_BLOCKED_LECTURER, "reason": "Žádný vybraný lektor není dostupný"}
        else:
            any_available = await check_any_lecturer_available_for_block(
                db, institution_id, date, time_block_str, duration
            )
            if not any_available:
                return {"status": STATUS_BLOCKED_LECTURER, "reason": "Žádný lektor není dostupný"}

    return None  # No collision


async def evaluate_program_slots(
    db: AsyncSession,
    institution_id: str,
    program_id: str,
    date: str,
) -> list:
    """
    Evaluate all time slots for a program on a given date.
    Returns list of {time, status, reason}.
    
    Layer 1: Base availability (time_blocks, available_days, exceptions)
    Layer 2: Collision rules (parallel, lecturer, room, program blocks)
    """
    from database.supabase_repositories import ProgramRepositorySupabase

    program_repo = ProgramRepositorySupabase(db)
    program_dict = await program_repo.find_by_id(program_id, institution_id)
    if not program_dict:
        return []

    # Also get the ORM object for collision checks
    prog_result = await db.execute(
        select(Program).where(and_(
            Program.id == uuid.UUID(program_id),
            Program.institution_id == uuid.UUID(institution_id)
        ))
    )
    program_obj = prog_result.scalar_one_or_none()
    if not program_obj:
        return []

    time_blocks_raw = program_dict.get("time_blocks") or ["09:00-10:30", "10:45-12:15", "13:00-14:30"]
    available_days = program_dict.get("available_days") or ["monday", "tuesday", "wednesday", "thursday", "friday"]
    duration = program_dict.get("duration") or 60

    # Check day of week
    from datetime import datetime as dt
    try:
        date_obj = dt.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return []

    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    day_name = days[date_obj.weekday()]
    if day_name not in available_days:
        return [{"time": "all", "status": STATUS_OUTSIDE_BASE, "reason": f"{day_name} není v dostupných dnech programu"}]

    # Expand time blocks
    expanded = []
    for tb in time_blocks_raw:
        if '-' in tb:
            parts = tb.split('-')
            w_start = _time_to_min(parts[0].strip())
            w_end = _time_to_min(parts[1].strip())
            if w_end - w_start > duration + 15:
                slot_s = w_start
                while slot_s + duration <= w_end:
                    expanded.append((_min_to_time(slot_s), _min_to_time(slot_s + duration)))
                    slot_s += 30
            else:
                expanded.append((parts[0].strip(), parts[1].strip()))
        else:
            start = _time_to_min(tb.strip())
            expanded.append((_min_to_time(start), _min_to_time(start + duration)))

    # Get exceptions for this program+date
    exceptions = await get_program_exceptions(db, institution_id, program_id, date)

    slots = []
    for start_str, end_str in expanded:
        s_start = _time_to_min(start_str)
        s_end = _time_to_min(end_str)
        time_str = f"{start_str}-{end_str}"

        # Layer 1: Check exception
        exc_reason = _slot_blocked_by_exception(s_start, s_end, exceptions)
        if exc_reason:
            slots.append({"time": time_str, "status": STATUS_BLOCKED_EXCEPTION, "reason": exc_reason})
            continue

        # Layer 2: Check collisions
        collision = await _check_collision_layer(
            db, institution_id, program_obj, date, s_start, s_end, time_str
        )
        if collision:
            slots.append({"time": time_str, **collision})
            continue

        slots.append({"time": time_str, "status": STATUS_AVAILABLE, "reason": None})

    return slots


async def evaluate_lecturer_slots(
    db: AsyncSession,
    institution_id: str,
    lecturer_id: str,
    date: str,
) -> list:
    """
    Evaluate all time slots for a lecturer on a given date.
    Returns list of {time, status, reason}.
    """
    from datetime import date as date_type

    lect_uuid = uuid.UUID(lecturer_id)
    inst_uuid = uuid.UUID(institution_id)

    try:
        d = date_type.fromisoformat(date)
    except ValueError:
        return []

    day_of_week = d.weekday()

    # Get recurring availability
    result = await db.execute(
        select(LecturerAvailability).where(and_(
            LecturerAvailability.lecturer_id == lect_uuid,
            LecturerAvailability.institution_id == inst_uuid,
            LecturerAvailability.day_of_week == day_of_week,
            LecturerAvailability.is_recurring == True,
        ))
    )
    recurring = result.scalars().all()

    # Get one-off availability
    result = await db.execute(
        select(LecturerAvailability).where(and_(
            LecturerAvailability.lecturer_id == lect_uuid,
            LecturerAvailability.institution_id == inst_uuid,
            LecturerAvailability.is_recurring == False,
            LecturerAvailability.specific_date == date,
        ))
    )
    oneoffs = result.scalars().all()

    all_blocks = list(recurring) + list(oneoffs)
    if not all_blocks:
        return []

    # Get exceptions
    exceptions = await get_lecturer_exceptions(db, institution_id, lecturer_id, date)

    # Get time-offs
    result = await db.execute(
        select(LecturerTimeOff).where(and_(
            LecturerTimeOff.lecturer_id == lect_uuid,
            LecturerTimeOff.institution_id == inst_uuid,
            LecturerTimeOff.start_date <= date,
            LecturerTimeOff.end_date >= date,
        ))
    )
    time_offs = result.scalars().all()

    # Get existing reservations for this lecturer on this date
    result = await db.execute(
        select(Reservation).where(and_(
            Reservation.institution_id == inst_uuid,
            Reservation.date == date,
            Reservation.status != 'cancelled',
            Reservation.assigned_lecturer_id == lect_uuid,
        ))
    )
    reservations = result.scalars().all()

    slots = []
    for ab in all_blocks:
        ab_start = _time_to_min(ab.start_time)
        ab_end = _time_to_min(ab.end_time)
        # Generate 30-min slots within this availability block
        slot_s = ab_start
        while slot_s + 30 <= ab_end:
            slot_e = slot_s + 30
            time_str = f"{_min_to_time(slot_s)}-{_min_to_time(slot_e)}"

            # Check exception
            exc_reason = _slot_blocked_by_exception(slot_s, slot_e, exceptions)
            if exc_reason:
                slots.append({"time": time_str, "status": STATUS_BLOCKED_EXCEPTION, "reason": exc_reason})
                slot_s += 30
                continue

            # Check time-off
            blocked_by_timeoff = False
            for to in time_offs:
                if to.start_time and to.end_time:
                    to_start = _time_to_min(to.start_time)
                    to_end = _time_to_min(to.end_time)
                    if slot_s < to_end and slot_e > to_start:
                        slots.append({"time": time_str, "status": STATUS_BLOCKED_EXCEPTION, "reason": to.reason or "Dovolená/absence"})
                        blocked_by_timeoff = True
                        break
                else:
                    slots.append({"time": time_str, "status": STATUS_BLOCKED_EXCEPTION, "reason": to.reason or "Celý den nedostupný"})
                    blocked_by_timeoff = True
                    break
            if blocked_by_timeoff:
                slot_s += 30
                continue

            # Check reservation overlap
            booked = False
            for res in reservations:
                res_start, res_end = parse_time_block(res.time_block)
                prog_result = await db.execute(select(Program).where(Program.id == res.program_id))
                prog = prog_result.scalar_one_or_none()
                if res_end is None:
                    res_end = res_start + (prog.duration if prog else 60)
                if slot_s < res_end and slot_e > res_start:
                    prog_name = prog.name_cs if prog else ""
                    slots.append({"time": time_str, "status": STATUS_BOOKED, "reason": f"Rezervace: {prog_name} ({res.school_name or ''})"})
                    booked = True
                    break
            if booked:
                slot_s += 30
                continue

            slots.append({"time": time_str, "status": STATUS_AVAILABLE, "reason": None})
            slot_s += 30

    return slots


async def check_exception_blocks_slot(
    db: AsyncSession,
    institution_id: str,
    scope_type: str,
    scope_id: str,
    date: str,
    time_block: str,
    duration: int,
) -> Optional[str]:
    """
    Check if a slot is blocked by an availability exception.
    Used by collision_service to integrate exceptions into booking validation.
    Returns reason string if blocked, None if clear.
    """
    if scope_type == 'program':
        exceptions = await get_program_exceptions(db, institution_id, scope_id, date)
    else:
        exceptions = await get_lecturer_exceptions(db, institution_id, scope_id, date)

    if not exceptions:
        return None

    s_start, s_end = parse_time_block(time_block)
    if s_start is None:
        return None
    if s_end is None:
        s_end = s_start + duration

    return _slot_blocked_by_exception(s_start, s_end, exceptions)
