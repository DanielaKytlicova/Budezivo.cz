"""
Collision validation logic for booking creation.
Checks for time overlap based on program collision settings.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid

from database.models import Reservation, Program

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
    """
    inst_uuid = uuid.UUID(institution_id)
    prog_uuid = uuid.UUID(program_id)

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

    # ====== CASE 1: Parallel NOT allowed → block all overlapping slots globally ======
    if not allow_parallel:
        # Find ALL non-cancelled reservations for the same institution on the same date
        result = await db.execute(
            select(Reservation).where(and_(
                Reservation.institution_id == inst_uuid,
                Reservation.date == date,
                Reservation.status != 'cancelled'
            ))
        )
        existing = result.scalars().all()

        for res in existing:
            # Get the other program's duration
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
    
    # Get all non-cancelled reservations for the same date
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

        # Check lecturer collision
        if "lecturer" in collision_resources and lecturer_id and res.assigned_lecturer_id:
            if str(res.assigned_lecturer_id) == lecturer_id:
                other_name = other_program.name_cs if other_program else "Neznámý program"
                return (
                    f"Kolize lektora: Lektor je již přiřazen k programu '{other_name}' "
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
