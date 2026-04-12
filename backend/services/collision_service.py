"""
Collision validation logic for booking creation.
Checks for time overlap based on program collision settings.
Includes lecturer collision, room collision, and advisory locking.
"""
import logging
import hashlib
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text
import uuid

from database.models import Reservation, Program, Room

logger = logging.getLogger(__name__)


def parse_time_block(block: str) -> tuple:
    """
    Parse time block in format 'HH:MM' or 'HH:MM-HH:MM'.
    Returns (start_minutes, end_minutes).
    """
    try:
        if '-' in block:
            parts = block.split('-')
            sh, sm = map(int, parts[0].strip().split(':'))
            eh, em = map(int, parts[1].strip().split(':'))
            return sh * 60 + sm, eh * 60 + em
        else:
            h, m = map(int, block.split(':'))
            start = h * 60 + m
            return start, None  # End unknown, needs duration
    except (ValueError, AttributeError, IndexError):
        return None, None


def time_blocks_overlap(block_a: str, duration_a: int, block_b: str, duration_b: int) -> bool:
    """
    Check if two time blocks overlap.
    Supports 'HH:MM' (start time + duration) and 'HH:MM-HH:MM' (range) formats.
    """
    start_a, end_a = parse_time_block(block_a)
    start_b, end_b = parse_time_block(block_b)
    
    if start_a is None or start_b is None:
        return False
    
    if end_a is None:
        end_a = start_a + duration_a
    if end_b is None:
        end_b = start_b + duration_b
    
    return start_a < end_b and start_b < end_a


def _advisory_lock_key(institution_id: str, date: str) -> int:
    """Generate a deterministic int64 advisory lock key from institution+date."""
    raw = f"{institution_id}:{date}"
    h = hashlib.sha256(raw.encode()).hexdigest()
    return int(h[:15], 16)  # 60-bit int, fits pg_advisory_xact_lock bigint


async def check_booking_collision(
    db: AsyncSession,
    institution_id: str,
    program_id: str,
    date: str,
    time_block: str,
    lecturer_id: Optional[str] = None,
) -> Optional[str]:
    """
    Check if a booking would collide with existing reservations.
    Returns error message string if collision found, None if OK.
    
    Uses PostgreSQL advisory lock to prevent race conditions.
    """
    inst_uuid = uuid.UUID(institution_id)
    prog_uuid = uuid.UUID(program_id)

    # ── Advisory Lock: prevents parallel inserts for same institution+date ──
    lock_key = _advisory_lock_key(institution_id, date)
    await db.execute(text(f"SELECT pg_advisory_xact_lock({lock_key})"))

    # Get the program being booked
    result = await db.execute(
        select(Program).where(and_(
            Program.id == prog_uuid,
            Program.institution_id == inst_uuid
        ))
    )
    program = result.scalar_one_or_none()
    if not program:
        return None  # program not found - let the main handler deal with it

    duration = program.duration or 60
    allow_parallel = program.allow_parallel or False
    collision_resources = program.collision_resources or []
    blocked_program_ids = program.blocked_program_ids or []
    program_room_id = str(program.room_id) if program.room_id else None

    # ====== CASE 1: Parallel NOT allowed → block all overlapping slots globally ======
    if not allow_parallel:
        result = await db.execute(
            select(Reservation).where(and_(
                Reservation.institution_id == inst_uuid,
                Reservation.date == date,
                Reservation.status != 'cancelled'
            ))
        )
        existing = result.scalars().all()

        for res in existing:
            other_prog = await db.execute(
                select(Program).where(Program.id == res.program_id)
            )
            other_program = other_prog.scalar_one_or_none()
            other_duration = other_program.duration if other_program else 60

            if time_blocks_overlap(time_block, duration, res.time_block, other_duration):
                other_name = other_program.name_cs if other_program else "Neznámý program"
                return (
                    f"Časový konflikt s existující rezervací programu '{other_name}' "
                    f"dne {date} v čase {res.time_block}. "
                    f"Program '{program.name_cs}' neumožňuje paralelní provoz."
                )

        return None

    # ====== CASE 2: Parallel allowed - check specific resources and blocked programs ======
    
    result = await db.execute(
        select(Reservation).where(and_(
            Reservation.institution_id == inst_uuid,
            Reservation.date == date,
            Reservation.status != 'cancelled'
        ))
    )
    existing = result.scalars().all()

    for res in existing:
        other_prog = await db.execute(
            select(Program).where(Program.id == res.program_id)
        )
        other_program = other_prog.scalar_one_or_none()
        other_duration = other_program.duration if other_program else 60

        if not time_blocks_overlap(time_block, duration, res.time_block, other_duration):
            continue  # No time overlap, skip

        # Check if the other program blocks parallel entirely
        other_allow_parallel = other_program.allow_parallel if other_program else False
        if not other_allow_parallel:
            other_name = other_program.name_cs if other_program else "Neznámý program"
            return (
                f"Časový konflikt s existující rezervací programu '{other_name}' "
                f"dne {date} v čase {res.time_block}. "
                f"Program '{other_name}' neumožňuje paralelní provoz."
            )

        # ── Check LECTURER collision ──
        if "lecturer" in collision_resources:
            # Use lecturer_id from the new booking OR the program's default lecturer
            effective_lecturer_id = lecturer_id or (str(program.assigned_lecturer_id) if program.assigned_lecturer_id else None)
            if effective_lecturer_id and res.assigned_lecturer_id:
                if str(res.assigned_lecturer_id) == effective_lecturer_id:
                    other_name = other_program.name_cs if other_program else "Neznámý program"
                    lecturer_name = res.assigned_lecturer_name or "Lektor"
                    return (
                        f"Kolize lektora: {lecturer_name} je již přiřazen/a k programu '{other_name}' "
                        f"dne {date} v čase {res.time_block}."
                    )

        # ── Check ROOM collision ──
        if "room" in collision_resources and program_room_id:
            other_room_id = str(other_program.room_id) if other_program and other_program.room_id else None
            if other_room_id and other_room_id == program_room_id:
                other_name = other_program.name_cs if other_program else "Neznámý program"
                # Get room name
                room_result = await db.execute(select(Room).where(Room.id == uuid.UUID(program_room_id)))
                room = room_result.scalar_one_or_none()
                room_name = room.name if room else "Místnost"
                return (
                    f"Kolize místnosti: '{room_name}' je již obsazena programem '{other_name}' "
                    f"dne {date} v čase {res.time_block}."
                )

        # Check blocked program IDs
        other_program_id = str(res.program_id) if res.program_id else None
        if other_program_id and other_program_id in blocked_program_ids:
            other_name = other_program.name_cs if other_program else "Neznámý program"
            return (
                f"Kolize programů: Program nelze provozovat současně s '{other_name}' "
                f"dne {date} v čase {res.time_block}."
            )
        
        # Also check if the OTHER program blocks THIS program
        other_blocked = other_program.blocked_program_ids if other_program else []
        if other_blocked and str(program_id) in [str(x) for x in (other_blocked or [])]:
            other_name = other_program.name_cs if other_program else "Neznámý program"
            return (
                f"Kolize programů: Program '{other_name}' zakazuje překryv s tímto programem "
                f"dne {date} v čase {res.time_block}."
            )

    return None


async def check_availability_blocks(
    db: AsyncSession,
    lecturer_id: str,
    institution_id: str,
    date: str,
    time_block: str,
    duration: int,
) -> Optional[str]:
    """
    Check if a lecturer has an Outlook/manual availability block
    that prevents booking (source=outlook, override=false).
    Returns error message if blocked, None if OK.
    """
    from database.models import AvailabilityBlock
    import pytz

    PRAGUE_TZ = pytz.timezone("Europe/Prague")
    lect_uuid = uuid.UUID(lecturer_id)

    start_min, end_min = parse_time_block(time_block)
    if start_min is None:
        return None
    if end_min is None:
        end_min = start_min + duration

    year, month, day = map(int, date.split("-"))
    booking_start = PRAGUE_TZ.localize(
        __import__("datetime").datetime(year, month, day, start_min // 60, start_min % 60)
    )
    booking_end = PRAGUE_TZ.localize(
        __import__("datetime").datetime(year, month, day, end_min // 60, end_min % 60)
    )

    result = await db.execute(
        select(AvailabilityBlock).where(and_(
            AvailabilityBlock.user_id == lect_uuid,
            AvailabilityBlock.end_time > booking_start,
            AvailabilityBlock.start_time < booking_end,
            AvailabilityBlock.override == False,
        ))
    )
    blocks = result.scalars().all()

    for block in blocks:
        return (
            f"Lektor má blokaci v kalendáři: '{block.title or 'Outlook událost'}' "
            f"({block.start_time.strftime('%H:%M')}–{block.end_time.strftime('%H:%M')}). "
            f"Zdroj: {'Outlook' if block.source == 'outlook' else 'Ruční blokace'}."
        )

    return None


async def check_lecturer_collision_for_assignment(
    db: AsyncSession,
    lecturer_id: str,
    institution_id: str,
    booking_id: str,
) -> Optional[str]:
    """
    Check if assigning a lecturer to a booking would create a time conflict.
    Called from assign_lecturer endpoints.
    Returns error message if collision found, None if OK.
    """
    inst_uuid = uuid.UUID(institution_id)
    lect_uuid = uuid.UUID(lecturer_id)
    book_uuid = uuid.UUID(booking_id)

    # Get the target booking
    result = await db.execute(
        select(Reservation).where(and_(
            Reservation.id == book_uuid,
            Reservation.institution_id == inst_uuid
        ))
    )
    booking = result.scalar_one_or_none()
    if not booking:
        return None

    # Get the booking's program for duration
    prog_result = await db.execute(select(Program).where(Program.id == booking.program_id))
    program = prog_result.scalar_one_or_none()
    booking_duration = program.duration if program else 60

    # Find all other non-cancelled reservations on the same date with this lecturer
    result = await db.execute(
        select(Reservation).where(and_(
            Reservation.institution_id == inst_uuid,
            Reservation.date == booking.date,
            Reservation.status != 'cancelled',
            Reservation.assigned_lecturer_id == lect_uuid,
            Reservation.id != book_uuid,  # Exclude the booking we're assigning to
        ))
    )
    other_bookings = result.scalars().all()

    for other in other_bookings:
        # Get other program's duration
        other_prog_result = await db.execute(select(Program).where(Program.id == other.program_id))
        other_program = other_prog_result.scalar_one_or_none()
        other_duration = other_program.duration if other_program else 60

        if time_blocks_overlap(booking.time_block, booking_duration, other.time_block, other_duration):
            other_name = other_program.name_cs if other_program else "Neznámý program"
            return (
                f"Kolize lektora: Lektor je již přiřazen k programu '{other_name}' "
                f"dne {booking.date} v čase {other.time_block}."
            )

    # Also check lecturer availability (recurring + time-off)
    available = await check_lecturer_available_for_block(
        db, lecturer_id, institution_id, booking.date, booking.time_block, booking_duration
    )
    if not available:
        return (
            f"Lektor není dostupný dne {booking.date} v čase {booking.time_block} "
            f"(mimo pracovní dobu nebo má blokaci)."
        )

    # Check Outlook / manual availability blocks
    block_error = await check_availability_blocks(
        db, lecturer_id, institution_id, str(booking.date), booking.time_block, booking_duration
    )
    if block_error:
        return block_error

    return None


async def get_collision_info_for_availability(
    db: AsyncSession,
    institution_id: str,
    program_id: str,
    date: str,
    time_block: str,
) -> bool:
    """
    Quick check if a time block has a collision.
    Returns True if blocked, False if available.
    """
    error = await check_booking_collision(
        db, institution_id, program_id, date, time_block
    )
    return error is not None



async def check_lecturer_available_for_block(
    db: AsyncSession,
    lecturer_id: str,
    institution_id: str,
    date_str: str,
    time_block: str,
    program_duration: int,
) -> bool:
    """
    Check if a lecturer is available for a specific time block on a date.
    Returns True if available, False if not.
    Uses lecturer_availability (recurring) and lecturer_time_off (blockages).
    """
    from database.models import LecturerAvailability, LecturerTimeOff
    from datetime import date as date_type

    lect_uuid = uuid.UUID(lecturer_id)
    inst_uuid = uuid.UUID(institution_id)

    d = date_type.fromisoformat(date_str)
    day_of_week = d.weekday()  # 0=Monday

    # Parse the time block to get start/end minutes
    block_start, block_end = parse_time_block(time_block)
    if block_start is None:
        return True  # Can't parse, allow it

    if block_end is None:
        block_end = block_start + program_duration

    def time_str_to_min(t):
        h, m = map(int, t.split(':'))
        return h * 60 + m

    # 1a. Check recurring availability for this day of week
    result = await db.execute(
        select(LecturerAvailability).where(and_(
            LecturerAvailability.lecturer_id == lect_uuid,
            LecturerAvailability.institution_id == inst_uuid,
            LecturerAvailability.day_of_week == day_of_week,
            LecturerAvailability.is_recurring == True
        ))
    )
    recurring_blocks = result.scalars().all()

    # 1b. Check one-off availability for this specific date
    result = await db.execute(
        select(LecturerAvailability).where(and_(
            LecturerAvailability.lecturer_id == lect_uuid,
            LecturerAvailability.institution_id == inst_uuid,
            LecturerAvailability.is_recurring == False,
            LecturerAvailability.specific_date == date_str
        ))
    )
    oneoff_blocks = result.scalars().all()

    all_avail_blocks = list(recurring_blocks) + list(oneoff_blocks)

    # If no availability configured at all, lecturer has no schedule constraints → allow
    if not all_avail_blocks:
        # But check if they have ANY availability defined for other days/dates
        # If they do, it means they have a schedule and this day is not in it
        any_result = await db.execute(
            select(LecturerAvailability.id).where(and_(
                LecturerAvailability.lecturer_id == lect_uuid,
                LecturerAvailability.institution_id == inst_uuid
            )).limit(1)
        )
        has_any_availability = any_result.scalar_one_or_none() is not None
        if has_any_availability:
            # Lecturer has a schedule but not for this day → unavailable
            return False
        # No schedule at all → no constraints → allow
        return True

    in_availability = False
    for ab in all_avail_blocks:
        ab_start = time_str_to_min(ab.start_time)
        ab_end = time_str_to_min(ab.end_time)
        if block_start >= ab_start and block_end <= ab_end:
            in_availability = True
            break

    if not in_availability:
        return False

    # 2. Check time-off / blockages
    result = await db.execute(
        select(LecturerTimeOff).where(and_(
            LecturerTimeOff.lecturer_id == lect_uuid,
            LecturerTimeOff.institution_id == inst_uuid,
            LecturerTimeOff.start_date <= date_str,
            LecturerTimeOff.end_date >= date_str
        ))
    )
    blockages = result.scalars().all()

    for b in blockages:
        if b.start_time is None or b.end_time is None:
            return False  # All-day blockage

        b_start = time_str_to_min(b.start_time)
        b_end = time_str_to_min(b.end_time)
        # Overlap check
        if block_start < b_end and block_end > b_start:
            return False

    return True
