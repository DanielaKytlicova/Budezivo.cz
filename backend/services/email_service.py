"""
Email Service Module for Budeživo.cz
Handles email template rendering and sending via Resend API.
Supports multiple sender addresses, logging, and development mode.
"""
import os
import re
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import resend

from config.email_config import (
    EmailType,
    SenderType,
    get_resend_api_key,
    get_sender_email,
    get_sender_addresses,
    is_development,
    get_sender_for_email_type,
    get_dev_recipient,
    TEMPLATE_VARIABLES,
)
from templates.emails import get_template, get_available_templates

logger = logging.getLogger(__name__)


def _init_resend():
    """Initialize Resend API key at runtime."""
    api_key = get_resend_api_key()
    if api_key:
        resend.api_key = api_key
        logger.info(f"Resend API initialized: {api_key[:8]}...")
        return True
    else:
        logger.warning("RESEND_API_KEY not found - email sending disabled")
        return False


class EmailTemplateRenderer:
    """Renders email templates by replacing variables with actual values."""
    
    AVAILABLE_VARIABLES = TEMPLATE_VARIABLES
    
    @classmethod
    def get_available_variables(cls) -> Dict[str, str]:
        """Return available template variables with descriptions."""
        return cls.AVAILABLE_VARIABLES
    
    @classmethod
    def render(cls, template: str, context: Dict[str, Any]) -> str:
        """
        Render template by replacing {{variable}} placeholders with values.
        """
        if not template:
            return ""
        
        result = template
        pattern = r'\{\{(\w+)\}\}'
        
        def replacer(match):
            var_name = match.group(1)
            value = context.get(var_name, "")
            return str(value) if value is not None else ""
        
        result = re.sub(pattern, replacer, result)
        return result
    
    @classmethod
    def validate_template(cls, template: str) -> Dict[str, Any]:
        """Validate template and return list of used variables."""
        if not template:
            return {"valid": True, "variables": [], "unknown_variables": []}
        
        pattern = r'\{\{(\w+)\}\}'
        found_vars = re.findall(pattern, template)
        
        known_vars = []
        unknown_vars = []
        
        for var in found_vars:
            if var in cls.AVAILABLE_VARIABLES:
                known_vars.append(var)
            else:
                unknown_vars.append(var)
        
        return {
            "valid": len(unknown_vars) == 0,
            "variables": list(set(known_vars)),
            "unknown_variables": list(set(unknown_vars))
        }


class EmailService:
    """Service for sending transactional emails via Resend API."""
    
    GDPR_FOOTER = """
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
    <p style="font-size: 12px; color: #6b7280; text-align: center;">
        Tento e-mail byl odeslán automaticky systémem Budeživo.cz.<br>
        Pokud si nepřejete dostávat tyto e-maily, kontaktujte prosím příslušnou instituci.
    </p>
    """
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if email service is properly configured (runtime check)."""
        api_key = get_resend_api_key()
        configured = bool(api_key)
        if configured:
            logger.debug(f"Email service configured: API key {api_key[:8]}...")
        else:
            logger.debug("Email service NOT configured: RESEND_API_KEY missing")
        return configured
    
    @classmethod
    def get_config_status(cls) -> Dict[str, Any]:
        """Get current email service configuration status."""
        api_key = get_resend_api_key()
        return {
            "configured": cls.is_configured(),
            "development_mode": is_development(),
            "available_templates": get_available_templates(),
            "sender_addresses": {k.value: v for k, v in get_sender_addresses().items()},
            "api_key_preview": f"{api_key[:8]}..." if api_key else None,
        }
    
    @classmethod
    async def send_email(
        cls,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        add_gdpr_footer: bool = True,
        reply_to: Optional[str] = None,
        tags: Optional[List[Dict[str, str]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send email via Resend API (async, non-blocking).
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            text_content: Plain text fallback (optional)
            from_email: Sender address (optional, uses default)
            add_gdpr_footer: Whether to add GDPR opt-out footer
            reply_to: Reply-to address (optional)
            tags: Resend tags for categorization
            
        Returns:
            Dict with status, message, and email_id or error
        """
        if not cls.is_configured():
            logger.warning("Email service not configured - RESEND_API_KEY missing")
            return {
                "status": "skipped",
                "message": "Email service not configured",
                "error": "RESEND_API_KEY not set"
            }
        
        # Initialize Resend API key at runtime (ensures it's set before sending)
        _init_resend()
        
        # Development mode - redirect to dev email
        actual_recipient = get_dev_recipient(to_email)
        if is_development() and actual_recipient != to_email:
            logger.info(f"Development mode: redirecting email from {to_email} to {actual_recipient}")
            subject = f"[DEV - původně pro: {to_email}] {subject}"
        
        # Add GDPR footer if requested
        full_html = html_content
        if add_gdpr_footer and cls.GDPR_FOOTER not in html_content:
            full_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                {html_content}
                {cls.GDPR_FOOTER}
            </div>
            """
        
        # Build email params
        params = {
            "from": from_email or get_sender_email(),
            "to": [actual_recipient],
            "subject": subject,
            "html": full_html,
        }
        
        if text_content:
            params["text"] = text_content
        
        if reply_to:
            params["reply_to"] = reply_to
            
        if tags:
            params["tags"] = tags
        
        if attachments:
            params["attachments"] = attachments
        
        try:
            # Run sync SDK in thread to keep FastAPI non-blocking
            email_result = await asyncio.to_thread(resend.Emails.send, params)
            
            email_id = email_result.get("id") if isinstance(email_result, dict) else getattr(email_result, 'id', None)
            
            logger.info(f"Email sent successfully to {actual_recipient}, ID: {email_id}")
            
            return {
                "status": "sent",
                "message": f"Email sent to {actual_recipient}",
                "email_id": email_id,
                "original_recipient": to_email,
                "actual_recipient": actual_recipient,
            }
            
        except Exception as e:
            logger.error(f"Failed to send email to {actual_recipient}: {str(e)}")
            return {
                "status": "failed",
                "message": f"Failed to send email: {str(e)}",
                "error": str(e)
            }
    
    @classmethod
    async def send_transactional_email(
        cls,
        template_name: str,
        to_email: str,
        data: Dict[str, Any],
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send transactional email using predefined template.
        
        Args:
            template_name: Name of the email template
            to_email: Recipient email address
            data: Template context data
            reply_to: Reply-to address (optional)
            
        Returns:
            Send result with status
        """
        try:
            # Get rendered template
            template_result = get_template(template_name, data)
            
            # Determine sender based on email type
            try:
                email_type = EmailType(template_name)
                from_email = get_sender_for_email_type(email_type)
            except ValueError:
                from_email = get_sender_email()
            
            # Send email
            result = await cls.send_email(
                to_email=to_email,
                subject=template_result["subject"],
                html_content=template_result["html"],
                text_content=template_result.get("text"),
                from_email=from_email,
                reply_to=reply_to,
                add_gdpr_footer=False,  # Templates already have footer
                tags=[{"name": "template", "value": template_name}],
            )
            
            result["template_name"] = template_name
            return result
            
        except ValueError as e:
            logger.error(f"Template error for {template_name}: {str(e)}")
            return {
                "status": "failed",
                "message": f"Template error: {str(e)}",
                "error": str(e),
                "template_name": template_name,
            }
        except Exception as e:
            logger.error(f"Failed to send transactional email {template_name}: {str(e)}")
            return {
                "status": "failed",
                "message": f"Failed to send email: {str(e)}",
                "error": str(e),
                "template_name": template_name,
            }
    
    @classmethod
    async def send_booking_confirmation(
        cls,
        booking_data: Dict[str, Any],
        program_data: Dict[str, Any],
        institution_data: Dict[str, Any],
        email_template: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send booking confirmation email (backwards compatible).
        Includes .ics attachment for Outlook/calendar integration.
        """
        # Generate ICS attachment
        ics_attachment = cls._generate_ics_attachment(booking_data, program_data, institution_data)
        
        # Build context for template rendering
        context = {
            "school_name": booking_data.get("school_name", ""),
            "teacher_name": booking_data.get("contact_name", ""),
            "contact_person": booking_data.get("contact_name", ""),
            "teacher_email": booking_data.get("contact_email", ""),
            "email": booking_data.get("contact_email", ""),
            "teacher_phone": booking_data.get("contact_phone", ""),
            "phone": booking_data.get("contact_phone", ""),
            "reservation_date": booking_data.get("date", ""),
            "reservation_time": booking_data.get("time_block", ""),
            "children_count": booking_data.get("num_students", 0),
            "number_of_students": booking_data.get("num_students", 0),
            "teachers_count": booking_data.get("num_teachers", 0),
            "number_of_teachers": booking_data.get("num_teachers", 0),
            "program_name": program_data.get("name_cs", ""),
            "program_duration": program_data.get("duration", 60),
            "institution_name": institution_data.get("name", ""),
            "institution_email": institution_data.get("email", ""),
            "institution_phone": institution_data.get("phone", ""),
            "institution_address": institution_data.get("address", ""),
            "special_requirements": booking_data.get("special_requirements", ""),
        }
        
        # Use custom template or default transactional template
        if email_template and email_template.get("subject") and email_template.get("body"):
            subject = EmailTemplateRenderer.render(email_template["subject"], context)
            body = EmailTemplateRenderer.render(email_template["body"], context)
            
            return await cls.send_email(
                to_email=booking_data.get("contact_email", ""),
                subject=subject,
                html_content=body,
                reply_to=institution_data.get("email"),
                attachments=[ics_attachment] if ics_attachment else None,
            )
        else:
            # Use predefined template
            return await cls.send_transactional_email(
                template_name="reservation_created_teacher",
                to_email=booking_data.get("contact_email", ""),
                data=context,
                reply_to=institution_data.get("email"),
            )
    
    @staticmethod
    def _generate_ics_attachment(booking_data: dict, program_data: dict, institution_data: dict) -> Optional[dict]:
        """Generate ICS file content as a Resend attachment dict."""
        try:
            from icalendar import Calendar, Event, vText
            import pytz
            from datetime import datetime, timedelta
            import base64
            
            PRAGUE_TZ = pytz.timezone("Europe/Prague")
            
            cal = Calendar()
            cal.add("prodid", "-//Budezivo.cz//Calendar//CS")
            cal.add("version", "2.0")
            cal.add("method", "PUBLISH")
            
            event = Event()
            res_id = booking_data.get("id", "unknown")
            event.add("uid", f"{res_id}@budezivo.cz")
            
            program_name = program_data.get("name_cs") or "Program"
            event.add("summary", program_name)
            
            date_str = booking_data.get("date", "")
            time_block = booking_data.get("time_block", "09:00")
            duration_min = program_data.get("duration") or 60
            
            try:
                year, month, day = map(int, date_str.split("-"))
                start_part = time_block.split("-")[0].strip()
                parts = start_part.split(":")
                h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
                dt_start = PRAGUE_TZ.localize(datetime(year, month, day, h, m))
                dt_end = dt_start + timedelta(minutes=duration_min)
            except (ValueError, IndexError):
                return None
            
            event.add("dtstart", dt_start)
            event.add("dtend", dt_end)
            
            desc = f"Škola: {booking_data.get('school_name', '')}\nPočet dětí: {booking_data.get('num_students', '')}"
            event.add("description", desc)
            
            address = institution_data.get("address") or institution_data.get("name") or ""
            if address:
                event["location"] = vText(address)
            
            cal.add_component(event)
            ics_bytes = cal.to_ical()
            
            return {
                "filename": "rezervace.ics",
                "content": base64.b64encode(ics_bytes).decode("utf-8"),
                "content_type": "text/calendar",
            }
        except Exception as e:
            logger.error(f"Failed to generate ICS attachment: {e}")
            return None
    
    @classmethod
    async def send_test_email(
        cls,
        to_email: str,
        subject: str,
        body: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send test email with rendered template (backwards compatible).
        """
        rendered_subject = EmailTemplateRenderer.render(subject, context)
        rendered_body = EmailTemplateRenderer.render(body, context)
        
        return await cls.send_email(
            to_email=to_email,
            subject=f"[TEST] {rendered_subject}",
            html_content=rendered_body
        )


# ============ Email Trigger Functions ============

async def trigger_reservation_created_emails(
    booking_data: Dict[str, Any],
    program_data: Dict[str, Any],
    institution_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Trigger emails after reservation is created."""
    results = {}

    context = _build_email_context(booking_data, program_data, institution_data)
    
    # Send to teacher
    results["teacher"] = await EmailService.send_transactional_email(
        template_name="reservation_created_teacher",
        to_email=booking_data.get("contact_email", ""),
        data=context,
        reply_to=institution_data.get("email"),
    )
    
    # Send to institution (if email configured)
    if institution_data.get("email"):
        results["institution"] = await EmailService.send_transactional_email(
            template_name="reservation_created_institution",
            to_email=institution_data.get("email"),
            data=context,
        )
    
    return results


def _compute_calendar_links(
    booking_data: Dict[str, Any],
    program_data: Dict[str, Any],
    institution_data: Dict[str, Any],
) -> Dict[str, str]:
    """Build "Add to Google Calendar" + "Add to Outlook" deep-link URLs.

    Both providers accept simple GET parameters with no auth — clicking the
    link opens the user's calendar with the event pre-filled, ready to save.
    Returns empty strings when the booking lacks valid date/time so the
    template can hide the buttons gracefully.
    """
    from urllib.parse import quote
    try:
        from datetime import datetime, timedelta
        import pytz

        date_str = booking_data.get("date", "")
        time_block = booking_data.get("time_block", "")
        duration_min = int(program_data.get("duration") or 60)

        # time_block looks like "09:00-10:30" — fall back to the first token
        start_part = time_block.split("-")[0].strip() if time_block else "09:00"
        h_str, _, m_str = start_part.partition(":")
        hour = int(h_str)
        minute = int(m_str) if m_str else 0

        year, month, day = (int(x) for x in date_str.split("-"))
        prague = pytz.timezone("Europe/Prague")
        dt_start_local = prague.localize(datetime(year, month, day, hour, minute))
        dt_end_local = dt_start_local + timedelta(minutes=duration_min)

        # Google + Outlook deep-links want UTC in YYYYMMDDTHHMMSSZ
        gfmt = "%Y%m%dT%H%M%SZ"
        utc_start = dt_start_local.astimezone(pytz.UTC).strftime(gfmt)
        utc_end = dt_end_local.astimezone(pytz.UTC).strftime(gfmt)

        # ISO for Outlook web
        iso_start = dt_start_local.astimezone(pytz.UTC).isoformat()
        iso_end = dt_end_local.astimezone(pytz.UTC).isoformat()
    except (ValueError, IndexError, TypeError):
        return {"google_calendar_url": "", "outlook_calendar_url": ""}

    program_name = program_data.get("name_cs") or "Program"
    institution_name = institution_data.get("name") or ""
    location = institution_data.get("address") or institution_name
    school_name = booking_data.get("school_name") or ""
    children = booking_data.get("num_students") or 0

    description = (
        f"Rezervace přes Budeživo.cz\n"
        f"Instituce: {institution_name}\n"
        f"Škola: {school_name}\n"
        f"Počet dětí: {children}"
    )

    google_url = (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={quote(program_name)}"
        f"&dates={utc_start}/{utc_end}"
        f"&details={quote(description)}"
        f"&location={quote(location)}"
    )
    outlook_url = (
        "https://outlook.office.com/calendar/0/deeplink/compose?path=/calendar/action/compose"
        f"&rru=addevent&subject={quote(program_name)}"
        f"&body={quote(description)}"
        f"&startdt={quote(iso_start)}"
        f"&enddt={quote(iso_end)}"
        f"&location={quote(location)}"
    )

    return {
        "google_calendar_url": google_url,
        "outlook_calendar_url": outlook_url,
    }


def _build_email_context(
    booking_data: Dict[str, Any],
    program_data: Dict[str, Any],
    institution_data: Dict[str, Any],
    **extra
) -> Dict[str, Any]:
    """Build shared context dict for email templates including theme data."""
    ctx = {
        "school_name": booking_data.get("school_name", ""),
        "teacher_name": booking_data.get("contact_name", ""),
        "teacher_email": booking_data.get("contact_email", ""),
        "teacher_phone": booking_data.get("contact_phone", ""),
        "reservation_date": booking_data.get("date", ""),
        "reservation_time": booking_data.get("time_block", ""),
        "children_count": booking_data.get("num_students", 0),
        "teachers_count": booking_data.get("num_teachers", 0),
        "program_name": program_data.get("name_cs", ""),
        "program_duration": program_data.get("duration", 60),
        "program_pricing_info": program_data.get("pricing_info") or "",
        "institution_name": institution_data.get("name", ""),
        "institution_email": institution_data.get("email", ""),
        "institution_phone": institution_data.get("phone", ""),
        "institution_address": institution_data.get("address", ""),
        "institution_logo_url": institution_data.get("logo_url"),
        "theme_logo_url": institution_data.get("theme_logo_url"),
        "theme_primary_color": institution_data.get("theme_primary_color"),
        "theme_secondary_color": institution_data.get("theme_secondary_color"),
        "theme_accent_color": institution_data.get("theme_accent_color"),
        "special_requirements": booking_data.get("special_requirements", ""),
        "dashboard_url": "https://budezivo.cz/admin",
    }
    # Add Google Calendar + Outlook web "Add to calendar" deep-links
    ctx.update(_compute_calendar_links(booking_data, program_data, institution_data))
    ctx.update(extra)
    return ctx


async def trigger_reservation_confirmed_email(
    booking_data: Dict[str, Any],
    program_data: Dict[str, Any],
    institution_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Trigger email when reservation is confirmed."""
    context = _build_email_context(booking_data, program_data, institution_data)

    return await EmailService.send_transactional_email(
        template_name="reservation_confirmed",
        to_email=booking_data.get("contact_email", ""),
        data=context,
        reply_to=institution_data.get("email"),
    )


async def trigger_reservation_cancelled_email(
    booking_data: Dict[str, Any],
    program_data: Dict[str, Any],
    institution_data: Dict[str, Any],
    cancellation_reason: str = "",
) -> Dict[str, Any]:
    """Trigger email when reservation is cancelled."""
    context = _build_email_context(
        booking_data, program_data, institution_data,
        cancellation_reason=cancellation_reason,
        booking_url=f"https://www.budezivo.cz/booking/{institution_data.get('id', '')}",
    )

    return await EmailService.send_transactional_email(
        template_name="reservation_cancelled",
        to_email=booking_data.get("contact_email", ""),
        data=context,
        reply_to=institution_data.get("email"),
    )


async def trigger_password_reset_email(
    user_email: str,
    reset_link: str,
) -> Dict[str, Any]:
    """Trigger password reset email."""
    return await EmailService.send_transactional_email(
        template_name="password_reset",
        to_email=user_email,
        data={
            "user_email": user_email,
            "reset_link": reset_link,
        },
    )


async def trigger_event_application_confirmation(
    to_email: str,
    data: Dict[str, Any],
    reply_to: Optional[str] = None,
) -> Dict[str, Any]:
    """Trigger confirmation email after a public event registration is saved."""
    return await EmailService.send_transactional_email(
        template_name="event_application_confirmation",
        to_email=to_email,
        data=data,
        reply_to=reply_to,
    )




async def trigger_user_registration_email(
    user_email: str,
    user_name: str,
    institution_name: str,
) -> Dict[str, Any]:
    """Trigger welcome email after registration."""
    return await EmailService.send_transactional_email(
        template_name="user_registration_confirmation",
        to_email=user_email,
        data={
            "user_name": user_name,
            "user_email": user_email,
            "institution_name": institution_name,
            "dashboard_url": "https://budezivo.cz/admin",
        },
    )


async def trigger_reservation_rescheduled_email(
    booking_data: Dict[str, Any],
    program_data: Dict[str, Any],
    institution_data: Dict[str, Any],
    original_date: str,
    original_time: str,
) -> Dict[str, Any]:
    """Trigger email when admin changes reservation date or time."""
    context = _build_email_context(
        booking_data, program_data, institution_data,
        original_date=original_date,
        original_time=original_time,
    )

    return await EmailService.send_transactional_email(
        template_name="reservation_rescheduled",
        to_email=booking_data.get("contact_email", ""),
        data=context,
        reply_to=institution_data.get("email"),
    )
