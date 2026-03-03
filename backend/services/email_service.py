"""
Email Service Module for Budeživo.cz
Handles email template rendering and sending via Resend API.
"""
import os
import re
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import resend
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Resend
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


class EmailTemplateRenderer:
    """Renders email templates by replacing variables with actual values."""
    
    # Available template variables
    AVAILABLE_VARIABLES = {
        "school_name": "Název školy/skupiny",
        "contact_person": "Jméno kontaktní osoby",
        "email": "E-mail kontaktní osoby",
        "phone": "Telefon kontaktní osoby",
        "reservation_date": "Datum rezervace",
        "reservation_time": "Čas rezervace",
        "number_of_students": "Počet žáků",
        "number_of_teachers": "Počet pedagogů",
        "program_name": "Název programu",
        "program_duration": "Délka programu (min)",
        "institution_name": "Název instituce",
        "special_requirements": "Speciální požadavky",
    }
    
    @classmethod
    def get_available_variables(cls) -> Dict[str, str]:
        """Return available template variables with descriptions."""
        return cls.AVAILABLE_VARIABLES
    
    @classmethod
    def render(cls, template: str, context: Dict[str, Any]) -> str:
        """
        Render template by replacing {{variable}} placeholders with values.
        
        Args:
            template: Template string with {{variable}} placeholders
            context: Dictionary with variable values
            
        Returns:
            Rendered string with all variables replaced
        """
        if not template:
            return ""
        
        result = template
        
        # Replace all {{variable}} patterns
        pattern = r'\{\{(\w+)\}\}'
        
        def replacer(match):
            var_name = match.group(1)
            value = context.get(var_name, "")
            return str(value) if value is not None else ""
        
        result = re.sub(pattern, replacer, result)
        return result
    
    @classmethod
    def validate_template(cls, template: str) -> Dict[str, Any]:
        """
        Validate template and return list of used variables.
        
        Returns:
            Dict with 'valid' bool and 'variables' list
        """
        if not template:
            return {"valid": True, "variables": [], "unknown_variables": []}
        
        # Find all {{variable}} patterns
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
    """Service for sending emails via Resend API."""
    
    GDPR_FOOTER = """
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
    <p style="font-size: 12px; color: #6b7280; text-align: center;">
        Tento e-mail byl odeslán automaticky systémem Budeživo.cz.<br>
        Pokud si nepřejete dostávat tyto e-maily, kontaktujte prosím příslušnou instituci.
    </p>
    """
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if email service is properly configured."""
        return bool(RESEND_API_KEY)
    
    @classmethod
    async def send_email(
        cls,
        to_email: str,
        subject: str,
        html_content: str,
        add_gdpr_footer: bool = True
    ) -> Dict[str, Any]:
        """
        Send email via Resend API (async, non-blocking).
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            add_gdpr_footer: Whether to add GDPR opt-out footer
            
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
        
        # Add GDPR footer if requested
        full_html = html_content
        if add_gdpr_footer:
            full_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                {html_content}
                {cls.GDPR_FOOTER}
            </div>
            """
        
        params = {
            "from": SENDER_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": full_html
        }
        
        try:
            # Run sync SDK in thread to keep FastAPI non-blocking
            email_result = await asyncio.to_thread(resend.Emails.send, params)
            
            logger.info(f"Email sent successfully to {to_email}, ID: {email_result.get('id')}")
            
            return {
                "status": "sent",
                "message": f"Email sent to {to_email}",
                "email_id": email_result.get("id")
            }
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return {
                "status": "failed",
                "message": f"Failed to send email: {str(e)}",
                "error": str(e)
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
        Send booking confirmation email.
        
        Args:
            booking_data: Reservation details
            program_data: Program details
            institution_data: Institution details
            email_template: Custom email template (optional)
            
        Returns:
            Send result with status
        """
        # Build context for template rendering
        context = {
            "school_name": booking_data.get("school_name", ""),
            "contact_person": booking_data.get("contact_name", ""),
            "email": booking_data.get("contact_email", ""),
            "phone": booking_data.get("contact_phone", ""),
            "reservation_date": booking_data.get("date", ""),
            "reservation_time": booking_data.get("time_block", ""),
            "number_of_students": booking_data.get("num_students", 0),
            "number_of_teachers": booking_data.get("num_teachers", 0),
            "program_name": program_data.get("name_cs", ""),
            "program_duration": program_data.get("duration", 60),
            "institution_name": institution_data.get("name", ""),
            "special_requirements": booking_data.get("special_requirements", ""),
        }
        
        # Use custom template or fallback
        if email_template and email_template.get("subject") and email_template.get("body"):
            subject = EmailTemplateRenderer.render(email_template["subject"], context)
            body = EmailTemplateRenderer.render(email_template["body"], context)
        else:
            # Default template
            subject = f"Potvrzení rezervace - {context['program_name']}"
            body = cls._get_default_booking_email(context)
        
        return await cls.send_email(
            to_email=booking_data.get("contact_email", ""),
            subject=subject,
            html_content=body
        )
    
    @classmethod
    def _get_default_booking_email(cls, context: Dict[str, Any]) -> str:
        """Generate default booking confirmation email HTML."""
        return f"""
        <h2 style="color: #1e293b;">Potvrzení rezervace</h2>
        
        <p>Dobrý den, {context['contact_person']},</p>
        
        <p>děkujeme za Vaši rezervaci programu <strong>{context['program_name']}</strong> 
        v instituci <strong>{context['institution_name']}</strong>.</p>
        
        <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #334155;">Detail rezervace</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #64748b;">Datum:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{context['reservation_date']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748b;">Čas:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{context['reservation_time']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748b;">Škola/Skupina:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{context['school_name']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748b;">Počet žáků:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{context['number_of_students']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748b;">Počet pedagogů:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{context['number_of_teachers']}</td>
                </tr>
            </table>
        </div>
        
        <p>V případě dotazů nás neváhejte kontaktovat.</p>
        
        <p>S pozdravem,<br>
        <strong>{context['institution_name']}</strong></p>
        """
    
    @classmethod
    async def send_test_email(
        cls,
        to_email: str,
        subject: str,
        body: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send test email with rendered template.
        
        Args:
            to_email: Recipient email
            subject: Email subject template
            body: Email body template
            context: Template context for rendering
            
        Returns:
            Send result
        """
        rendered_subject = EmailTemplateRenderer.render(subject, context)
        rendered_body = EmailTemplateRenderer.render(body, context)
        
        return await cls.send_email(
            to_email=to_email,
            subject=f"[TEST] {rendered_subject}",
            html_content=rendered_body
        )
