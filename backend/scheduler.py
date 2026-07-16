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
from database.models import Reservation, Feedback, Institution, Program, EmailLog
from routes.feedback import generate_feedback_token
from services.email_service import EmailService

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

_EMAIL_RE = None


def _valid_email(email: str) -> bool:
    import re
    global _EMAIL_RE
    if _EMAIL_RE is None:
        _EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    return bool(email and _EMAIL_RE.match(email.strip()))


def subtract_working_days(d, n: int):
    """Return the date that is ``n`` working days (Mon–Fri) before ``d``."""
    cur = d
    while n > 0:
        cur -= timedelta(days=1)
        if cur.weekday() < 5:  # Mon-Fri
            n -= 1
    return cur


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
    Main scheduler job: 
    1. Auto-complete confirmed reservations whose date has passed.
    2. Find completed reservations and send feedback requests.
    """
    logger.info("Running completed reservations scheduler job...")
    
    # --- Step 1: Auto-complete past confirmed reservations ---
    async with AsyncSessionLocal() as db:
        try:
            today = datetime.now(timezone.utc)
            today_str = today.strftime("%Y-%m-%d")
            
            result = await db.execute(
                select(Reservation).where(
                    and_(
                        Reservation.status == 'confirmed',
                        Reservation.date < today_str
                    )
                )
            )
            past_confirmed = result.scalars().all()
            
            completed_count = 0
            for reservation in past_confirmed:
                reservation.status = 'completed'
                completed_count += 1
            
            if completed_count > 0:
                await db.commit()
                logger.info(f"Auto-completed {completed_count} past reservations.")
        except Exception as e:
            logger.error(f"Error auto-completing reservations: {e}")
    
    # --- Step 2: Send feedback emails for newly completed reservations ---
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


async def process_plan_expiration():
    """
    Subscription auto-renewal / expiration scheduler.
    Runs daily. For every institution with plan_expires_at in the past:
    - If auto_renew=True AND billing_provider configured → create new billing order
      (real charge happens when billing provider implements webhook).
    - Otherwise → mark plan_status='expired' and reset limits to Free.
    Also sends a soft-reminder state change when plan expires within 7 days (future hook).
    """
    logger.info("Running plan expiration scheduler job...")

    async with AsyncSessionLocal() as db:
        try:
            from database.models import Institution, BillingOrder
            from services.plan_service import PLAN_LIMITS
            from services.billing_service import create_billing_order

            now = datetime.now(timezone.utc)

            # Find expired institutions still marked active
            result = await db.execute(
                select(Institution).where(and_(
                    Institution.plan_status == 'active',
                    Institution.plan != 'free',
                    Institution.plan_expires_at.isnot(None),
                    Institution.plan_expires_at < now,
                    Institution.deleted_at.is_(None),
                ))
            )
            expired = result.scalars().all()

            renewed = 0
            expired_count = 0
            prices = {"start": 49000, "pro": 99000, "pro_plus": 199000}

            for inst in expired:
                if inst.auto_renew and inst.billing_provider:
                    # Auto-renewal hook: create pending order for same tier
                    try:
                        await create_billing_order(
                            db=db,
                            institution_id=str(inst.id),
                            requested_plan=inst.plan,
                            provider=inst.billing_provider or "manual",
                            amount=prices.get(inst.plan, 0),
                            currency="CZK",
                            note="Auto-renewal scheduler",
                        )
                        inst.plan_status = 'pending'
                        inst.plan_updated_at = now
                        renewed += 1
                        logger.info(f"Auto-renewal: created billing order for inst {inst.id} ({inst.plan})")
                    except Exception as e:
                        logger.error(f"Auto-renewal failed for {inst.id}: {e}")
                        inst.plan_status = 'expired'
                        inst.plan_updated_at = now
                        expired_count += 1
                else:
                    # No auto-renew → mark expired + downgrade limits to Free
                    inst.plan_status = 'expired'
                    inst.plan_updated_at = now
                    free_limits = PLAN_LIMITS['free']
                    inst.programs_limit = free_limits['programs_limit']
                    inst.bookings_monthly_limit = free_limits['bookings_monthly_limit']
                    expired_count += 1
                    logger.info(f"Plan expired: inst {inst.id} (was {inst.plan})")

            await db.commit()
            logger.info(f"Plan expiration scheduler: {renewed} renewed, {expired_count} expired")
        except Exception as e:
            logger.error(f"Plan expiration job failed: {e}")
            await db.rollback()


async def process_event_payment_reminders():
    """Send a gentle payment reminder for QR/cash event applications that are
    still unpaid and whose event date is within EVENT_PAYMENT_REMINDER_DAYS days.

    Sent at most once per application (payment_reminder_sent_at guard).
    """
    import re as _re
    from database.models import EventApplication, EventDate, Event, InstitutionPaymentSettings

    days = int(os.getenv("EVENT_PAYMENT_REMINDER_DAYS", "3"))
    logger.info("Running event payment reminder job...")

    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            window_end = now + timedelta(days=days)

            rows = (await db.execute(
                select(EventApplication, EventDate, Event, Institution)
                .join(EventDate, EventApplication.event_date_id == EventDate.id)
                .join(Event, EventApplication.event_id == Event.id)
                .join(Institution, EventApplication.institution_id == Institution.id)
                .where(and_(
                    EventApplication.payment_method.in_(['qr', 'cash']),
                    EventApplication.payment_status.in_(['unpaid', 'pending']),
                    EventApplication.status.in_(['pending', 'approved']),
                    EventApplication.total_amount > 0,
                    EventApplication.payment_reminder_sent_at.is_(None),
                    EventDate.start_datetime >= now,
                    EventDate.start_datetime <= window_end,
                ))
            )).all()

            sent = 0
            ps_cache = {}
            for app, ed, event, inst in rows:
                email = (app.applicant_email or "").strip()
                if not email or not _re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                    continue
                iid = app.institution_id
                if iid not in ps_cache:
                    ps_cache[iid] = (await db.execute(
                        select(InstitutionPaymentSettings).where(
                            InstitutionPaymentSettings.institution_id == iid
                        )
                    )).scalar_one_or_none()
                ps = ps_cache[iid]
                date_label = ed.start_datetime.strftime("%d.%m.%Y %H:%M") if ed.start_datetime else None
                try:
                    from templates.emails import get_template
                    tpl = get_template("event_payment_reminder", {
                        "event_name": event.name,
                        "applicant_name": app.applicant_name or "",
                        "institution_name": inst.name,
                        "date_label": date_label,
                        "price": app.total_amount or 0,
                        "currency": "CZK",
                        "variable_symbol": app.variable_symbol,
                        "payment_method": app.payment_method,
                        "account_number": ps.account_number if ps else None,
                        "bank_code": ps.bank_code if ps else None,
                        "account_name": ps.account_name if ps else None,
                    })
                    res = await EmailService.send_email(
                        to_email=email,
                        subject=tpl["subject"],
                        html_content=tpl["html"],
                        text_content=tpl.get("text"),
                        add_gdpr_footer=False,
                        reply_to=getattr(inst, "email", None),
                    )
                    if res.get("status") == "sent":
                        app.payment_reminder_sent_at = now
                        sent += 1
                except Exception as e:
                    logger.error(f"Payment reminder failed for application {app.id}: {type(e).__name__}")
                    continue

            await db.commit()
            logger.info(f"Event payment reminder job completed. Sent {sent} reminders.")
        except Exception as e:
            logger.error(f"Event payment reminder job failed: {e}")
            await db.rollback()


async def process_visit_reminders():
    """Send 'visit reminder' to the booking contact 2 working days before the visit.

    - Working days = Mon–Fri (weekends skipped; public holidays not considered yet).
    - Only for active reservations (pending/confirmed); never cancelled/rejected/completed/deleted.
    - Sent at most once (visit_reminder_sent_at guard); failures never mark it as sent.
    - Gated per institution by notification_settings.customer.visit_reminder (default False).
    - Every attempt is written to email_logs.
    """
    logger.info("Running visit reminder scheduler job...")
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            today = now.date()
            today_str = today.strftime("%Y-%m-%d")
            horizon_str = (today + timedelta(days=10)).strftime("%Y-%m-%d")

            rows = (await db.execute(
                select(Reservation, Institution, Program)
                .join(Institution, Reservation.institution_id == Institution.id)
                .join(Program, Reservation.program_id == Program.id)
                .where(and_(
                    Reservation.status.in_(['pending', 'confirmed']),
                    Reservation.date >= today_str,
                    Reservation.date <= horizon_str,
                    Reservation.visit_reminder_sent_at.is_(None),
                    Reservation.deleted_at.is_(None),
                ))
            )).all()

            sent = 0
            for res, inst, prog in rows:
                ns = inst.notification_settings or {}
                if not (ns.get('customer') or {}).get('visit_reminder', False):
                    continue
                # Program-level opt-out also applies to customer emails
                if prog.send_email_notification is False:
                    continue
                try:
                    visit_date = datetime.strptime(res.date, "%Y-%m-%d").date()
                except Exception:
                    continue
                remind_date = subtract_working_days(visit_date, 2)
                if today < remind_date:
                    continue  # too early
                if today >= visit_date:
                    continue  # safety: never on/after the visit day

                email = (res.contact_email or "").strip()
                if not _valid_email(email):
                    res.visit_reminder_error = "chybí nebo neplatná e-mailová adresa"
                    res.visit_reminder_last_attempt_at = now
                    continue

                try:
                    date_label = visit_date.strftime("%d. %m. %Y")
                except Exception:
                    date_label = res.date

                from templates.emails import get_template
                tpl = get_template("reservation_reminder_teacher", {
                    "teacher_name": res.contact_name or "",
                    "program_name": prog.name_cs,
                    "reservation_date": date_label,
                    "reservation_time": res.time_block or "",
                    "institution_name": inst.name,
                    "institution_address": inst.address or "",
                })

                log = EmailLog(
                    institution_id=res.institution_id,
                    program_id=res.program_id,
                    reservation_id=res.id,
                    recipient_email=email,
                    subject=tpl["subject"],
                    status="pending",
                )
                db.add(log)
                res.visit_reminder_last_attempt_at = now
                try:
                    result = await EmailService.send_email(
                        to_email=email,
                        subject=tpl["subject"],
                        html_content=tpl["html"],
                        text_content=tpl.get("text"),
                        add_gdpr_footer=False,
                        reply_to=getattr(inst, "email", None),
                    )
                    if result.get("status") == "sent":
                        res.visit_reminder_sent_at = now
                        res.visit_reminder_error = None
                        log.status = "sent"
                        log.sent_at = now
                        log.email_id = result.get("email_id")
                        sent += 1
                    else:
                        err = result.get("error") or "odeslání se nezdařilo"
                        res.visit_reminder_error = str(err)[:500]
                        log.status = "failed"
                        log.error_message = str(err)[:500]
                except Exception as e:
                    res.visit_reminder_error = f"{type(e).__name__}: dočasná chyba služby"
                    log.status = "failed"
                    log.error_message = str(e)[:500]

            await db.commit()
            logger.info(f"Visit reminder job completed. Sent {sent} reminders.")
        except Exception as e:
            logger.error(f"Visit reminder job failed: {e}")
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

    # Plan expiration / auto-renewal: run daily at 5:00 AM UTC
    scheduler.add_job(
        process_plan_expiration,
        CronTrigger(hour=5, minute=0),
        id='plan_expiration_scheduler',
        replace_existing=True,
        misfire_grace_time=3600
    )

    # Event payment reminders (QR/cash, before the event): run daily at 6:00 AM UTC
    scheduler.add_job(
        process_event_payment_reminders,
        CronTrigger(hour=6, minute=0),
        id='event_payment_reminders',
        replace_existing=True,
        misfire_grace_time=3600
    )

    # Visit reminders (2 working days before the visit): run daily at 6:30 UTC
    scheduler.add_job(
        process_visit_reminders,
        CronTrigger(hour=6, minute=30),
        id='visit_reminders',
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

    # Google calendar sync — every 5 minutes (parallel to Outlook)
    async def _run_google_sync():
        try:
            from routes.google_calendar import sync_all_integrations as _g
            await _g()
        except Exception as e:
            logger.error(f"Google sync scheduler error: {e}")

    scheduler.add_job(
        _run_google_sync,
        IntervalTrigger(minutes=5),
        id='google_calendar_sync',
        replace_existing=True,
        misfire_grace_time=300
    )
    
    # Cleanup expired OAuth states & refresh tokens: run hourly
    async def _cleanup_auth_tokens():
        try:
            from database.models import OAuthState, RefreshToken
            from sqlalchemy import delete
            async with AsyncSessionLocal() as session:
                now = datetime.now(timezone.utc)
                # Delete expired OAuth states
                await session.execute(
                    delete(OAuthState).where(OAuthState.expires_at < now)
                )
                # Delete expired refresh tokens
                await session.execute(
                    delete(RefreshToken).where(RefreshToken.expires_at < now)
                )
                await session.commit()
                logger.info("Auth token cleanup completed")
        except Exception as e:
            logger.error(f"Auth token cleanup error: {e}")

    scheduler.add_job(
        _cleanup_auth_tokens,
        CronTrigger(minute=30),
        id='auth_token_cleanup',
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()
    logger.info("Feedback scheduler started - includes Outlook sync every 5 min")


def stop_scheduler():
    """Stop the APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Feedback scheduler stopped")
