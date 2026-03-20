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
from sqlalchemy import select, and_
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
    """Send feedback request email using Resend."""
    try:
        # Format date for display
        try:
            date_obj = datetime.strptime(reservation_date, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d. %m. %Y")
        except:
            formatted_date = reservation_date
        
        subject = f"Jak se vám líbil program {program_name}?"
        
        html_content = f"""
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #F1F5F9; font-family: 'Segoe UI', Arial, sans-serif;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 40px 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden;">
                    <!-- Header -->
                    <div style="background-color: #5a7aae; padding: 32px; text-align: center;">
                        <h1 style="color: #ffffff; font-size: 24px; margin: 0;">Zpětná vazba</h1>
                    </div>
                    
                    <!-- Content -->
                    <div style="padding: 32px;">
                        <p style="color: #475569; font-size: 16px; line-height: 1.6; margin: 0 0 16px 0;">
                            Dobrý den, {recipient_name},
                        </p>
                        
                        <p style="color: #475569; font-size: 16px; line-height: 1.6; margin: 0 0 16px 0;">
                            děkujeme za návštěvu programu <strong>{program_name}</strong> v instituci 
                            <strong>{institution_name}</strong> dne {formatted_date}.
                        </p>
                        
                        <p style="color: #475569; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                            Budeme rádi, pokud si najdete chvilku na vyplnění krátkého dotazníku. 
                            Vaše zpětná vazba nám pomáhá zlepšovat naše programy.
                        </p>
                        
                        <div style="text-align: center; margin: 32px 0;">
                            <a href="{feedback_url}" 
                               style="display: inline-block; background-color: #5a7aae; color: #ffffff; 
                                      padding: 14px 32px; text-decoration: none; border-radius: 6px; 
                                      font-weight: 500; font-size: 16px;">
                                Vyplnit dotazník
                            </a>
                        </div>
                        
                        <p style="color: #64748B; font-size: 14px; line-height: 1.6; margin: 24px 0 0 0;">
                            Dotazník zabere pouze 2 minuty a je zcela anonymní.
                        </p>
                    </div>
                    
                    <!-- Footer -->
                    <div style="background-color: #F8FAFC; padding: 24px; text-align: center; border-top: 1px solid #E2E8F0;">
                        <p style="color: #64748B; font-size: 12px; line-height: 1.5; margin: 0;">
                            Tento email byl odeslán automaticky systémem Budeživo.cz<br>
                            Pokud si nepřejete dostávat tyto emaily, můžete je ignorovat.
                        </p>
                    </div>
                </div>
            </td>
        </tr>
    </table>
</body>
</html>
"""
        
        plain_text = f"""
Dobrý den, {recipient_name},

děkujeme za návštěvu programu {program_name} v instituci {institution_name} dne {formatted_date}.

Budeme rádi, pokud si najdete chvilku na vyplnění krátkého dotazníku:
{feedback_url}

Vaše zpětná vazba nám pomáhá zlepšovat naše programy.
Dotazník zabere pouze 2 minuty a je zcela anonymní.

S pozdravem,
Tým {institution_name}
"""
        
        result = await EmailService.send_email(
            to_email=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=plain_text
        )
        
        return result.get("status") == "sent"
        
    except Exception as e:
        logger.error(f"Failed to send feedback email: {e}")
        return False


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
    
    scheduler.start()
    logger.info("Feedback scheduler started - runs daily at 8:00 AM CET")


def stop_scheduler():
    """Stop the APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Feedback scheduler stopped")
