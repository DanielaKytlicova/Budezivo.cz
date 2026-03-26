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
    """Send feedback reminder email using Resend."""
    try:
        # Format date for display
        try:
            date_obj = datetime.strptime(reservation_date, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d. %m. %Y")
        except:
            formatted_date = reservation_date
        
        subject = f"Připomínka: Vaše zpětná vazba na program {program_name}"
        
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
                    <div style="background-color: #c5ac87; padding: 32px; text-align: center;">
                        <h1 style="color: #ffffff; font-size: 24px; margin: 0;">Připomínka</h1>
                    </div>
                    
                    <!-- Content -->
                    <div style="padding: 32px;">
                        <p style="color: #475569; font-size: 16px; line-height: 1.6; margin: 0 0 16px 0;">
                            Dobrý den, {recipient_name},
                        </p>
                        
                        <p style="color: #475569; font-size: 16px; line-height: 1.6; margin: 0 0 16px 0;">
                            před týdnem jsme vám poslali žádost o zpětnou vazbu na program 
                            <strong>{program_name}</strong>, který jste navštívili dne {formatted_date} 
                            v instituci <strong>{institution_name}</strong>.
                        </p>
                        
                        <p style="color: #475569; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                            Pokud jste dotazník ještě nevyplnili, budeme velmi rádi za vaši zpětnou vazbu. 
                            Zabere vám to pouze 2 minuty.
                        </p>
                        
                        <div style="text-align: center; margin: 32px 0;">
                            <a href="{feedback_url}" 
                               style="display: inline-block; background-color: #c5ac87; color: #ffffff; 
                                      padding: 14px 32px; text-decoration: none; border-radius: 6px; 
                                      font-weight: 500; font-size: 16px;">
                                Vyplnit dotazník
                            </a>
                        </div>
                        
                        <p style="color: #64748B; font-size: 14px; line-height: 1.6; margin: 24px 0 0 0;">
                            Toto je poslední připomínka. Děkujeme za váš čas!
                        </p>
                    </div>
                    
                    <!-- Footer -->
                    <div style="background-color: #F8FAFC; padding: 24px; text-align: center; border-top: 1px solid #E2E8F0;">
                        <p style="color: #64748B; font-size: 12px; line-height: 1.5; margin: 0;">
                            Tento email byl odeslán automaticky systémem Budeživo.cz<br>
                            Pokud jste již dotazník vyplnili, můžete tento email ignorovat.
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

před týdnem jsme vám poslali žádost o zpětnou vazbu na program {program_name}, 
který jste navštívili dne {formatted_date} v instituci {institution_name}.

Pokud jste dotazník ještě nevyplnili, budeme velmi rádi za vaši zpětnou vazbu:
{feedback_url}

Toto je poslední připomínka. Děkujeme za váš čas!

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
    
    scheduler.start()
    logger.info("Feedback scheduler started - runs daily at 8:00 AM CET, reminders at 9:00 AM CET, GDPR cleanup at 4:00 AM CET")


def stop_scheduler():
    """Stop the APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Feedback scheduler stopped")
