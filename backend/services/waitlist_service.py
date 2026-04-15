"""
Waitlist service — Phase 2: Semi-automatic matching.
Hooks into: booking cancellation, slot creation, capacity changes.
Finds matching waitlist entries and notifies candidates via email.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update

from database.models import WaitlistEntry, Program

logger = logging.getLogger(__name__)


async def find_matching_entries(
    db: AsyncSession,
    program_id: str,
    slot_date: str,
    slot_time: Optional[str] = None,
) -> List:
    """
    Find active waitlist entries matching a newly freed slot.
    Checks: specific_date match OR date_range containing the slot date.
    """
    prog_uuid = uuid.UUID(program_id)
    
    result = await db.execute(
        select(WaitlistEntry).where(and_(
            WaitlistEntry.program_id == prog_uuid,
            WaitlistEntry.status == 'active',
        ))
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


async def notify_candidates(
    db: AsyncSession,
    entries: List,
    slot_info: dict,
    program_name: str = '',
) -> int:
    """
    Send email notifications to matching waitlist candidates.
    Updates their status to 'contacted'.
    Returns number of notified candidates.
    """
    notified = 0
    
    for entry in entries:
        try:
            from services.email_service import EmailService
            
            slot_date = slot_info.get('date', '')
            slot_time = slot_info.get('time', '')
            
            subject = f"Uvolnil se termín: {program_name}"
            html = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #1E293B; padding: 24px; border-radius: 8px 8px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 20px;">Uvolnil se termín!</h1>
                </div>
                <div style="padding: 24px; background: white; border: 1px solid #E2E8F0; border-top: none; border-radius: 0 0 8px 8px;">
                    <p style="color: #475569; font-size: 15px;">
                        Dobrý den, {entry.teacher_name},
                    </p>
                    <p style="color: #475569; font-size: 15px;">
                        uvolnil se termín programu <strong>{program_name}</strong>, o který jste projevili zájem.
                    </p>
                    <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 16px; margin: 16px 0;">
                        <p style="margin: 4px 0; color: #166534; font-size: 14px;">
                            <strong>Program:</strong> {program_name}
                        </p>
                        <p style="margin: 4px 0; color: #166534; font-size: 14px;">
                            <strong>Datum:</strong> {slot_date}
                        </p>
                        {f'<p style="margin: 4px 0; color: #166534; font-size: 14px;"><strong>Čas:</strong> {slot_time}</p>' if slot_time else ''}
                    </div>
                    <p style="color: #475569; font-size: 15px;">
                        Doporučujeme co nejdříve provést rezervaci, než termín obsadí někdo jiný.
                    </p>
                    <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 20px 0;">
                    <p style="color: #94A3B8; font-size: 12px; text-align: center;">
                        Odesláno systémem Budeživo.cz
                    </p>
                </div>
            </div>
            """
            
            if EmailService.is_configured():
                await EmailService.send_email(
                    to_email=entry.email,
                    subject=subject,
                    html_content=html,
                )
            
            # Update status to 'contacted'
            entry.status = 'contacted'
            entry.updated_at = datetime.now(timezone.utc)
            notified += 1
            
            logger.info(f"Waitlist notify: {entry.email} for {program_name} on {slot_date}")
            
        except Exception as e:
            logger.warning(f"Waitlist notify failed for {entry.email}: {e}")
    
    if notified > 0:
        await db.commit()
    
    return notified


async def on_booking_cancelled(
    db: AsyncSession,
    program_id: str,
    date: str,
    time_block: str = '',
    institution_id: str = '',
):
    """
    Hook: Called when a booking is cancelled.
    Finds matching waitlist entries and notifies them.
    """
    # Get program name
    prog_result = await db.execute(
        select(Program.name_cs).where(Program.id == uuid.UUID(program_id))
    )
    program_name = prog_result.scalar_one_or_none() or 'Program'
    
    slot_time = time_block.split('-')[0] if time_block and '-' in time_block else ''
    
    matches = await find_matching_entries(db, program_id, date, slot_time)
    
    if matches:
        notified = await notify_candidates(
            db, matches,
            {'date': date, 'time': slot_time},
            program_name,
        )
        logger.info(f"Waitlist hook (booking_cancelled): notified {notified} candidates for {program_name} on {date}")
    
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
    
    slot_time = time_block.split('-')[0] if time_block and '-' in time_block else ''
    
    matches = await find_matching_entries(db, program_id, date, slot_time)
    
    if matches:
        notified = await notify_candidates(
            db, matches,
            {'date': date, 'time': slot_time},
            program_name,
        )
        logger.info(f"Waitlist hook (slot_freed): notified {notified} candidates for {program_name} on {date}")
    
    return len(matches)
