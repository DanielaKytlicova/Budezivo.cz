"""
Waitlist service — Phase 2: Semi-automatic matching.
Hooks into: booking cancellation, slot creation, capacity changes.
Finds matching waitlist entries for admins. It must never contact teachers
automatically; admins decide whom to contact.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database.models import WaitlistEntry, Program

logger = logging.getLogger(__name__)


async def find_matching_entries(
    db: AsyncSession,
    program_id: str,
    slot_date: str,
    slot_time: Optional[str] = None,
    institution_id: str = '',
) -> List:
    """
    Find active waitlist entries matching a newly freed slot.
    Checks: specific_date match OR date_range containing the slot date.
    """
    prog_uuid = uuid.UUID(program_id)
    conditions = [
        WaitlistEntry.program_id == prog_uuid,
        WaitlistEntry.status == 'active',
    ]
    if institution_id:
        conditions.append(WaitlistEntry.institution_id == uuid.UUID(institution_id))

    result = await db.execute(
        select(WaitlistEntry).where(and_(*conditions)).order_by(WaitlistEntry.created_at.asc())
    )
    all_entries = result.scalars().all()
    
    matches = []
    for entry in all_entries:
        matched = False
        
        if entry.request_type == 'specific_date':
            if entry.requested_date == slot_date:
                matched = True
        elif entry.request_type == 'date_range':
            if entry.range_start_date and entry.range_end_date:
                if entry.range_start_date <= slot_date <= entry.range_end_date:
                    matched = True
        
        if matched and slot_time and entry.preferred_time_of_day != 'any':
            # Filter by preferred time of day
            try:
                hour = int(slot_time.split(':')[0])
                pref = entry.preferred_time_of_day
                if pref == 'morning' and hour >= 12:
                    matched = False
                elif pref == 'midday' and (hour < 11 or hour >= 14):
                    matched = False
                elif pref == 'afternoon' and hour < 12:
                    matched = False
            except (ValueError, IndexError):
                pass
        
        if matched:
            matches.append(entry)
    
    if matches:
        logger.info(f"Waitlist match: {len(matches)} entries for program {program_id} on {slot_date}")
    
    return matches


async def mark_matches_for_admin(
    db: AsyncSession,
    entries: List,
    slot_info: dict,
    program_name: str = '',
) -> int:
    """
    Mark matching waitlist entries so admins can review them.

    This intentionally does not send email to teachers and does not decide who
    should be contacted. The admin/educator sees the match and chooses manually.
    """
    marked = 0
    slot_date = slot_info.get('date', '')
    slot_time = slot_info.get('time', '')
    note = f"Uvolnil se termín: {program_name}, {slot_date}{f' {slot_time}' if slot_time else ''}."

    for entry in entries:
        entry.status = 'matched'
        entry.admin_note = f"{entry.admin_note}\n{note}".strip() if entry.admin_note else note
        entry.updated_at = datetime.now(timezone.utc)
        marked += 1

    if marked > 0:
        await db.commit()

    return marked


async def on_booking_cancelled(
    db: AsyncSession,
    program_id: str,
    date: str,
    time_block: str = '',
    institution_id: str = '',
):
    """
    Hook: Called when a booking is cancelled.
    Finds matching waitlist entries and marks them for admin review.
    """
    # Get program name
    prog_result = await db.execute(
        select(Program.name_cs).where(Program.id == uuid.UUID(program_id))
    )
    program_name = prog_result.scalar_one_or_none() or 'Program'
    
    slot_time = time_block.split('-')[0].strip() if time_block and '-' in time_block else ''

    matches = await find_matching_entries(db, program_id, date, slot_time, institution_id=institution_id)

    if matches:
        marked = await mark_matches_for_admin(
            db, matches,
            {'date': date, 'time': slot_time},
            program_name,
        )
        logger.info(f"Waitlist hook (booking_cancelled): marked {marked} candidate(s) for admin review for {program_name} on {date}")
    
    return len(matches)


async def on_slot_freed(
    db: AsyncSession,
    program_id: str,
    date: str,
    time_block: str = '',
):
    """
    Hook: Called when a time slot becomes available (e.g., exception removed, capacity changed).
    """
    prog_result = await db.execute(
        select(Program.name_cs).where(Program.id == uuid.UUID(program_id))
    )
    program_name = prog_result.scalar_one_or_none() or 'Program'
    
    slot_time = time_block.split('-')[0].strip() if time_block and '-' in time_block else ''

    matches = await find_matching_entries(db, program_id, date, slot_time)
    
    if matches:
        marked = await mark_matches_for_admin(
            db, matches,
            {'date': date, 'time': slot_time},
            program_name,
        )
        logger.info(f"Waitlist hook (slot_freed): marked {marked} candidate(s) for admin review for {program_name} on {date}")
    
    return len(matches)
