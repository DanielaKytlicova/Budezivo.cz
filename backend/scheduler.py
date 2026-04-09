"""
Feedback Scheduler - APScheduler integration for automatic feedback emails.

Sends feedback request emails 1 working day after a completed reservation.
Working days = Monday-Friday (skips weekends).
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.supabase import AsyncSessionLocal
from database.models import Reservation, Feedback, Institution, Program
from routes.feedback import generate_feedback_token
from services.email_service import EmailService

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


def get_next_working_day(from_date: datetime) -> datetime:
    """
    Get the next working day (skip weekends).
    If from_date is Friday, return Monday.
    If from_date is Saturday, return Monday.
    If from_date is Sunday, return Monday.
    Otherwise return the next day.
    """
    next_day = from_date + timedelta(days=1)
    
    # Skip weekends (5=Saturday, 6=Sunday)
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)
    
    return next_day


def is_working_day_after(reservation_date_str: str, check_date: datetime) -> bool:
    """
    Check if check_date is 1 working day after reservation_date.
    """
    try:
        reservation_date = datetime.strptime(reservation_date_str, "%Y-%m-%d")
        reservation_date = reservation_date.replace(tzinfo=timezone.utc)
        
        target_date = get_next_working_day(reservation_date)
        
        return check_date.date() == target_date.date()
    except Exception as e:
        logger.error(f"Error parsing reservation date: {e}")
        return False


async def process_completed_reservations():
    """
    Main scheduler job: Find reservations that completed 1 working day ago
    and create/send feedback requests.
    """
    logger.info("Running feedback scheduler job...")
    
    async with AsyncSessionLocal() as db:
        try:
            today = datetime.now(timezone.utc)
            
            # Find all completed reservations without feedback
            # We need to check reservations from recent days and filter by working day logic
            
            # Get reservations from the last 7 days that are completed/confirmed
            week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            
            result = await db.execute(
                select(Reservation, Institution, Program)
                .join(Institution, Reservation.institution_id == Institution.id)
                .join(Program, Reservation.program_id == Program.id)
                .outerjoin(Feedback, Reservation.id == Feedback.reservation_id)
                .where(
                    and_(
                        Reservation.date >= week_ago,
                        Reservation.date < today.strftime("%Y-%m-%d"),
                        Reservation.status.in_(['confirmed', 'completed']),
                        Feedback.id == None  # No feedback created yet
                    )
                )
            )
            
            rows = result.all()
            
            sent_count = 0
            for reservation, institution, program in rows:
                # Check if this is 1 working day after the reservation
                if not is_working_day_after(reservation.date, today):
                    continue
                
                logger.info(f"Processing reservation {reservation.id} for feedback...")
                
                try:
                    # Create feedback entry
                    token = generate_feedback_token()
                    feedback = Feedback(
                        institution_id=reservation.institution_id,
                        reservation_id=reservation.id,
                        program_id=reservation.program_id,
                        token=token,
                        status='pending'
                    )
                    db.add(feedback)
                    await db.flush()
                    
                    # Send feedback email
                    feedback_url = f"{os.getenv('FRONTEND_URL', 'https://www.budezivo.cz')}/feedback/{token}"
                    
                    email_sent = await send_feedback_request_email(
                        recipient_email=reservation.contact_email,
                        recipient_name=reservation.contact_name,
                        institution_name=institution.name,
                        program_name=program.name_cs,
                        reservation_date=reservation.date,
                        feedback_url=feedback_url
                    )
                    
                    if email_sent:
                        feedback.email_sent_at = datetime.now(timezone.utc)
                        sent_count += 1
                        logger.info(f"Feedback email sent for reservation {reservation.id}")
                    else:
                        logger.warning(f"Failed to send feedback email for reservation {reservation.id}")
                    
                except Exception as e:
                    logger.error(f"Error processing reservation {reservation.id}: {e}")
                    continue
            
            await db.commit()
            logger.info(f"Feedback scheduler job completed. Sent {sent_count} emails.")
            
        except Exception as e:
            logger.error(f"Feedback scheduler job failed: {e}")
            await db.rollback()


async def send_feedback_request_email(
    recipient_email: str,
    recipient_name: str,
    institution_name: str,
    program_name: str,
    reservation_date: str,
    feedback_url: str
) -> bool:
    """Send feedback request email using the centralised template system."""
    try:
        try:
            date_obj = datetime.strptime(reservation_date, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d. %m. %Y")
        except Exception:
            formatted_date = reservation_date

        from templates.emails import get_template
        template_result = get_template("feedback_request", {
            "recipient_name": recipient_name,
            "institution_name": institution_name,
            "program_name": program_name,
            "formatted_date": formatted_date,
            "feedback_url": feedback_url,
        })

        result = await EmailService.send_email(
            to_email=recipient_email,
            subject=template_result["subject"],
            html_content=template_result["html"],
            text_content=template_result.get("text"),
            add_gdpr_footer=False,
        )
        return result.get("status") == "sent"

    except Exception as e:
        logger.error(f"Failed to send feedback email: {e}")
        return False


async def process_feedback_reminders():
    """
    Reminder scheduler job: Find feedback requests that were sent 7 days ago
    but haven't been filled out yet, and send a reminder email.
    """
    logger.info("Running feedback reminder scheduler job...")
    
    async with AsyncSessionLocal() as db:
        try:
            today = datetime.now(timezone.utc)
            seven_days_ago = today - timedelta(days=7)
            eight_days_ago = today - timedelta(days=8)
            
            # Find pending feedbacks where email was sent ~7 days ago and no reminder was sent
            result = await db.execute(
                select(Feedback, Reservation, Institution, Program)
                .join(Reservation, Feedback.reservation_id == Reservation.id)
                .join(Institution, Feedback.institution_id == Institution.id)
                .join(Program, Feedback.program_id == Program.id)
                .where(
                    and_(
                        Feedback.status == 'pending',
                        Feedback.email_sent_at.isnot(None),
                        Feedback.email_sent_at >= eight_days_ago,
                        Feedback.email_sent_at < seven_days_ago,
                        Feedback.reminder_sent_at == None  # No reminder sent yet
                    )
                )
            )
            
            rows = result.all()
            
            sent_count = 0
            for feedback, reservation, institution, program in rows:
                logger.info(f"Sending reminder for feedback {feedback.id}...")
                
                try:
                    feedback_url = f"{os.getenv('FRONTEND_URL', 'https://www.budezivo.cz')}/feedback/{feedback.token}"
                    
                    email_sent = await send_feedback_reminder_email(
                        recipient_email=reservation.contact_email,
                        recipient_name=reservation.contact_name,
                        institution_name=institution.name,
                        program_name=program.name_cs,
                        reservation_date=reservation.date,
                        feedback_url=feedback_url
                    )
                    
                    if email_sent:
                        feedback.reminder_sent_at = datetime.now(timezone.utc)
                        sent_count += 1
                        logger.info(f"Reminder email sent for feedback {feedback.id}")
                    else:
                        logger.warning(f"Failed to send reminder email for feedback {feedback.id}")
                    
                except Exception as e:
                    logger.error(f"Error sending reminder for feedback {feedback.id}: {e}")
                    continue
            
            await db.commit()
            logger.info(f"Feedback reminder job completed. Sent {sent_count} reminder emails.")
            
        except Exception as e:
            logger.error(f"Feedback reminder job failed: {e}")
            await db.rollback()


async def send_feedback_reminder_email(
    recipient_email: str,
    recipient_name: str,
    institution_name: str,
    program_name: str,
    reservation_date: str,
    feedback_url: str
) -> bool:
    """Send feedback reminder email using the centralised template system."""
    try:
        try:
            date_obj = datetime.strptime(reservation_date, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d. %m. %Y")
        except Exception:
            formatted_date = reservation_date

        from templates.emails import get_template
        template_result = get_template("feedback_reminder", {
            "recipient_name": recipient_name,
            "institution_name": institution_name,
            "program_name": program_name,
            "formatted_date": formatted_date,
            "feedback_url": feedback_url,
        })

        result = await EmailService.send_email(
            to_email=recipient_email,
            subject=template_result["subject"],
            html_content=template_result["html"],
            text_content=template_result.get("text"),
            add_gdpr_footer=False,
        )
        return result.get("status") == "sent"

    except Exception as e:
        logger.error(f"Failed to send feedback reminder email: {e}")
        return False


RETENTION_DAYS = {
    "1year": 365,
    "2years": 730,
    "3years": 1095,
    "5years": 1825,
}


async def process_gdpr_auto_cleanup():
    """
    GDPR auto-cleanup job: Anonymize PII in old reservations
    based on each institution's data_retention setting.
    Runs daily. Skips institutions with retention='never'.
    """
    logger.info("Running GDPR auto-cleanup job...")

    async with AsyncSessionLocal() as db:
        try:
            today = datetime.now(timezone.utc)

            # Get all institutions with gdpr_settings
            result = await db.execute(select(Institution))
            institutions = result.scalars().all()

            total_anonymized = 0
            for inst in institutions:
                gdpr = inst.gdpr_settings or {}
                retention = gdpr.get("data_retention", "never")
                should_anonymize = gdpr.get("anonymize", False)

                if retention == "never" or not should_anonymize:
                    continue

                max_days = RETENTION_DAYS.get(retention)
                if not max_days:
                    continue

                cutoff_date = (today - timedelta(days=max_days)).strftime("%Y-%m-%d")

                # Anonymize old reservations for this institution
                result = await db.execute(
                    select(Reservation).where(
                        and_(
                            Reservation.institution_id == inst.id,
                            Reservation.date < cutoff_date,
                            Reservation.contact_email != "anonymized@deleted.local",
                        )
                    )
                )
                old_reservations = result.scalars().all()

                for res in old_reservations:
                    # Only anonymize reservation-level PII.
                    # School contacts (schools, school_contacts tables) are NOT touched
                    # — they must persist for future program promotion campaigns.
                    res.contact_name = "Anonymizováno"
                    res.contact_email = "anonymized@deleted.local"
                    res.contact_phone = None
                    res.notes = None
                    total_anonymized += 1

            await db.commit()
            logger.info(f"GDPR auto-cleanup completed. Anonymized {total_anonymized} reservations.")

        except Exception as e:
            logger.error(f"GDPR auto-cleanup job failed: {e}")
            await db.rollback()


async def process_auto_archive_programs():
    """
    Auto-archive programs whose end_date has passed.
    Runs daily. Only archives active/draft programs with expired end_date.
    """
    logger.info("Running auto-archive programs job...")

    async with AsyncSessionLocal() as db:
        try:
            today = datetime.now(timezone.utc)
            
            # Find active programs with end_date in the past
            result = await db.execute(
                select(Program).where(and_(
                    Program.status.in_(['active', 'draft']),
                    Program.end_date != None,
                    Program.end_date < today,
                ))
            )
            expired_programs = result.scalars().all()
            
            count = 0
            for prog in expired_programs:
                prog.status = 'archived'
                prog.archived_at = today
                prog.archive_reason = 'Automaticky archivováno po ukončení platnosti'
                prog.is_published = False
                count += 1
            
            await db.commit()
            logger.info(f"Auto-archive: {count} programs archived.")
        except Exception as e:
            logger.error(f"Auto-archive job failed: {e}")
            await db.rollback()


def start_scheduler():
    """Start the APScheduler with feedback job."""
    if scheduler.running:
        logger.info("Scheduler already running")
        return
    
    # Run every day at 8:00 AM Prague time (7:00 UTC in winter, 6:00 UTC in summer)
    # Using 7:00 UTC as a reasonable default
    scheduler.add_job(
        process_completed_reservations,
        CronTrigger(hour=7, minute=0),
        id='feedback_scheduler',
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace period
    )
    
    # Run reminder job every day at 9:00 AM Prague time
    scheduler.add_job(
        process_feedback_reminders,
        CronTrigger(hour=8, minute=0),
        id='feedback_reminder_scheduler',
        replace_existing=True,
        misfire_grace_time=3600
    )
    
    # GDPR auto-cleanup: run daily at 3:00 AM UTC
    scheduler.add_job(
        process_gdpr_auto_cleanup,
        CronTrigger(hour=3, minute=0),
        id='gdpr_auto_cleanup',
        replace_existing=True,
        misfire_grace_time=3600
    )
    
    # Auto-archive expired programs: run daily at 4:00 AM UTC
    scheduler.add_job(
        process_auto_archive_programs,
        CronTrigger(hour=4, minute=0),
        id='auto_archive_programs',
        replace_existing=True,
        misfire_grace_time=3600
    )
    
    # Outlook calendar sync — every 5 minutes
    from apscheduler.triggers.interval import IntervalTrigger
    async def _run_outlook_sync():
        try:
            from routes.microsoft_calendar import sync_all_integrations
            await sync_all_integrations()
        except Exception as e:
            logger.error(f"Outlook sync scheduler error: {e}")
    
    scheduler.add_job(
        _run_outlook_sync,
        IntervalTrigger(minutes=5),
        id='outlook_calendar_sync',
        replace_existing=True,
        misfire_grace_time=300
    )
    
    scheduler.start()
    logger.info("Feedback scheduler started - includes Outlook sync every 5 min")


def stop_scheduler():
    """Stop the APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Feedback scheduler stopped")
