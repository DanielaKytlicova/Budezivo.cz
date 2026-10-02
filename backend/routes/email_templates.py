"""
Email Template Management Routes.
Handles CRUD operations for program email templates.
"""
import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import (
    ProgramRepositorySupabase,
    EmailTemplateRepositorySupabase,
    EmailLogRepositorySupabase,
    InstitutionRepositorySupabase
)
from services.email_service import EmailService, EmailTemplateRenderer
from config.email_config import EmailType, get_sender_for_email_type
from templates.emails import get_template

router = APIRouter(prefix="/programs", tags=["Email Templates"])
logger = logging.getLogger(__name__)


def _reservation_confirmation_sample_context(program: dict, institution: dict, recipient: str) -> dict:
    """Build representative data for the real reservation confirmation template."""
    return {
        "school_name": "Základní škola Příkladová",
        "teacher_name": "Jan Novák",
        "contact_person": "Jan Novák",
        "teacher_email": recipient,
        "email": recipient,
        "teacher_phone": "+420 123 456 789",
        "phone": "+420 123 456 789",
        "reservation_date": datetime.now().strftime("%d.%m.%Y"),
        "reservation_time": "09:00–10:00",
        "children_count": 25,
        "number_of_students": 25,
        "teachers_count": 2,
        "number_of_teachers": 2,
        "program_name": program.get("name_cs", "Název programu"),
        "program_duration": program.get("duration", 60),
        "program_pricing_info": program.get("pricing_info") or "",
        "institution_name": institution.get("name", "Vaše instituce"),
        "institution_email": institution.get("email", ""),
        "institution_phone": institution.get("phone", ""),
        "institution_address": institution.get("address", ""),
        "institution_logo_url": institution.get("logo_url"),
        "theme_logo_url": institution.get("theme_logo_url"),
        "theme_primary_color": institution.get("theme_primary_color"),
        "theme_secondary_color": institution.get("theme_secondary_color"),
        "theme_accent_color": institution.get("theme_accent_color"),
        "special_requirements": "Bezbariérový přístup",
        "google_calendar_url": "https://calendar.google.com/calendar/render?action=TEMPLATE",
        "outlook_calendar_url": "https://outlook.live.com/calendar/0/deeplink/compose",
    }


# ============ Pydantic Models ============

class EmailTemplateUpdate(BaseModel):
    """Schema for updating email template."""
    subject: str
    body: str


class EmailTemplatePreviewRequest(BaseModel):
    """Schema for template preview request."""
    subject: str
    body: str


class EmailTestRequest(BaseModel):
    """Schema for sending test email."""
    recipient_email: EmailStr
    subject: str
    body: str


# ============ Routes ============

@router.get("/{program_id}/email-template")
async def get_email_template(
    program_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get email template for a program."""
    # Verify program belongs to user's institution
    program_repo = ProgramRepositorySupabase(db)
    program = await program_repo.find_by_id(program_id, current_user["institution_id"])
    
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Get template
    template_repo = EmailTemplateRepositorySupabase(db)
    template = await template_repo.find_by_program(program_id)
    
    # Return available variables along with template
    return {
        "template": template,
        "available_variables": EmailTemplateRenderer.get_available_variables(),
        "email_service_configured": EmailService.is_configured()
    }


@router.put("/{program_id}/email-template")
async def update_email_template(
    program_id: str,
    data: EmailTemplateUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create or update email template for a program."""
    # Verify program belongs to user's institution
    program_repo = ProgramRepositorySupabase(db)
    program = await program_repo.find_by_id(program_id, current_user["institution_id"])
    
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Validate template
    subject_validation = EmailTemplateRenderer.validate_template(data.subject)
    body_validation = EmailTemplateRenderer.validate_template(data.body)
    
    unknown_vars = list(set(
        subject_validation.get("unknown_variables", []) + 
        body_validation.get("unknown_variables", [])
    ))
    
    if unknown_vars:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown template variables: {', '.join(unknown_vars)}"
        )
    
    # Create or update template
    template_repo = EmailTemplateRepositorySupabase(db)
    template = await template_repo.create_or_update(
        program_id=program_id,
        institution_id=current_user["institution_id"],
        subject=data.subject,
        body=data.body,
        updated_by=current_user["user_id"]
    )
    
    logger.info(f"Email template updated for program {program_id}")
    
    return {
        "message": "Template saved successfully",
        "template": template
    }


@router.post("/{program_id}/email-template/preview")
async def preview_email_template(
    program_id: str,
    data: EmailTemplatePreviewRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Preview email template with sample data."""
    # Verify program belongs to user's institution
    program_repo = ProgramRepositorySupabase(db)
    program = await program_repo.find_by_id(program_id, current_user["institution_id"])
    
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Get institution info
    institution_repo = InstitutionRepositorySupabase(db)
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    sample_context = {
        "school_name": "Základní škola Příkladová",
        "contact_person": "Jan Novák",
        "email": "jan.novak@skola.cz",
        "phone": "+420 123 456 789",
        "reservation_date": datetime.now().strftime("%d.%m.%Y"),
        "reservation_time": "09:00",
        "number_of_students": 25,
        "number_of_teachers": 2,
        "program_name": program.get("name_cs", "Název programu"),
        "program_duration": program.get("duration", 60),
        "institution_name": institution.get("name", "Vaše instituce") if institution else "Vaše instituce",
        "special_requirements": "Bezbariérový přístup",
    }
    rendered_subject = EmailTemplateRenderer.render(data.subject, sample_context)
    rendered_body = EmailTemplateRenderer.render(data.body, sample_context)
    
    return {
        "preview": {
            "subject": rendered_subject,
            "body": rendered_body
        },
        "sample_data": sample_context
    }


@router.post("/{program_id}/email-template/test")
async def send_test_email(
    program_id: str,
    data: EmailTestRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send test email with the template."""
    # Verify program belongs to user's institution
    program_repo = ProgramRepositorySupabase(db)
    program = await program_repo.find_by_id(program_id, current_user["institution_id"])
    
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Check if email service is configured
    if not EmailService.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Email service not configured. Please set RESEND_API_KEY."
        )
    
    # Get institution info
    institution_repo = InstitutionRepositorySupabase(db)
    institution = await institution_repo.find_by_id_with_theme(current_user["institution_id"])
    sample_context = _reservation_confirmation_sample_context(
        program,
        institution or {},
        str(data.recipient_email),
    )
    rendered_body = EmailTemplateRenderer.render(data.body, sample_context)
    sample_context.update({
        "custom_email_subject": EmailTemplateRenderer.render(data.subject, sample_context),
        "custom_email_body_html": rendered_body,
        "custom_email_body_text": EmailTemplateRenderer.html_to_text(rendered_body),
    })
    rendered = get_template("reservation_confirmed", sample_context)

    # Use the same renderer, sender and HTML/text structure as the production
    # confirmation. Only the subject prefix marks this message as a test.
    result = await EmailService.send_email(
        to_email=data.recipient_email,
        subject=f"[TEST] {rendered['subject']}",
        html_content=rendered["html"],
        text_content=rendered.get("text"),
        from_email=get_sender_for_email_type(EmailType.RESERVATION_CONFIRMED),
        reply_to=(institution or {}).get("email"),
        add_gdpr_footer=False,
        tags=[{"name": "template", "value": "reservation_confirmed_test"}],
    )
    
    # Log the test email
    if result.get("status") in ["sent", "failed"]:
        log_repo = EmailLogRepositorySupabase(db)
        await log_repo.create({
            "institution_id": current_user["institution_id"],
            "program_id": program_id,
            "reservation_id": None,
            "recipient_email": data.recipient_email,
            "subject": f"[TEST] {rendered['subject']}",
            "body_snapshot": rendered["html"],
            "status": result.get("status"),
            "error_message": result.get("error"),
            "email_id": result.get("email_id"),
        })
    
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result.get("message"))
    
    return {
        "message": f"Test email sent to {data.recipient_email}",
        "email_id": result.get("email_id")
    }


@router.get("/{program_id}/email-logs")
async def get_email_logs(
    program_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50
):
    """Get email logs for a program."""
    # Verify program belongs to user's institution
    program_repo = ProgramRepositorySupabase(db)
    program = await program_repo.find_by_id(program_id, current_user["institution_id"])
    
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Get logs
    log_repo = EmailLogRepositorySupabase(db)
    logs = await log_repo.find_by_program(program_id, limit=limit)
    
    return {"logs": logs}


@router.get("/email-config/status")
async def get_email_config_status(
    current_user: dict = Depends(get_current_user)
):
    """Check email service configuration status."""
    return {
        "configured": EmailService.is_configured(),
        "available_variables": EmailTemplateRenderer.get_available_variables()
    }
