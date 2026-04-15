"""
Waitlist service — skeleton for future matching.
Phase 2 prepared: hooks for slot creation, booking cancellation, capacity change.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database.models import WaitlistEntry

logger = logging.getLogger(__name__)


async def find_matching_entries(db: AsyncSession, program_id: str, slot_date: str, slot_time: str = None):
    """
    Find waitlist entries that match a newly available slot.
    Phase 2: Currently only logs matches, does NOT send emails.
    """
    from uuid import UUID
    query = select(WaitlistEntry).where(and_(
        WaitlistEntry.program_id == UUID(program_id),
        WaitlistEntry.status == 'active',
    ))
    result = await db.execute(query)
    entries = result.scalars().all()

    matches = []
    for entry in entries:
        if entry.request_type == 'specific_date' and entry.requested_date == slot_date:
            matches.append(entry)
        elif entry.request_type == 'date_range':
            if entry.range_start_date and entry.range_end_date:
                if entry.range_start_date <= slot_date <= entry.range_end_date:
                    matches.append(entry)

    if matches:
        logger.info(f"Waitlist: {len(matches)} matching entries for program {program_id} on {slot_date}")

    return matches


async def notify_candidates(entries, slot_info: dict):
    """
    Phase 2: Send notifications to matching waitlist candidates.
    Currently only logs — does NOT send emails yet.
    """
    for entry in entries:
        logger.info(
            f"Waitlist notify (SKELETON): {entry.email} for program {entry.program_id} "
            f"slot {slot_info.get('date')} {slot_info.get('time', '')}"
        )
