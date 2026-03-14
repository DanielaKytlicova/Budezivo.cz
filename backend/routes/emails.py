"""
Email routes for testing and management.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import EmailLogRepositorySupabase
from services.email_service import (
    EmailService, 
    EmailTemplateRenderer,
    trigger_reservation_created_emails,
)
from templates.emails import get_available_templates, get_template
from config.email_config import EmailType, TEMPLATE_VARIABLES

router = APIRouter(prefix="/emails", tags=["Emails"])
logger = logging.getLogger(__name__)


class TestEmailRequest(BaseModel):
    """Request model for test email endpoint."""
    email_type: str
    email: EmailStr


class TestEmailResponse(BaseModel):
    """Response model for test email endpoint."""
    status: str
    message: str
    email_id: Optional[str] = None
    template_name: str


@router.get("/config")
async def get_email_config():
    """Get email service configuration status."""
    return EmailService.get_config_status()


@router.get("/templates")
async def list_email_templates():
    """List all available email templates."""
    templates = get_available_templates()
    return {
        "templates": templates,
        "count": len(templates),
        "categories": {
            "account": [t for t in templates if t.startswith(("user_", "account_", "password_"))],
            "reservation": [t for t in templates if t.startswith("reservation_")],
            "reminder": [t for t in templates if "reminder" in t],
            "admin": [t for t in templates if t.startswith("new_")],
        }
    }


@router.get("/templates/{template_name}")
async def get_email_template_preview(template_name: str):
    """Get preview of email template with sample data."""
    if template_name not in get_available_templates():
        raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
    
    # Sample data for preview
    sample_data = {
        "user_name": "Jan Novák",
        "user_email": "jan.novak@skola.cz",
        "institution_name": "Muzeum Umění",
        "institution_email": "info@muzeum.cz",
        "institution_phone": "+420 123 456 789",
        "institution_address": "Muzejní 123, Praha",
        "program_name": "Objevujeme malíře",
        "program_description": "Interaktivní program pro děti.",
        "program_duration": "90",
        "reservation_date": "15. 1. 2026",
        "reservation_time": "09:00 - 10:30",
        "school_name": "ZŠ Květinová",
        "teacher_name": "Jan Novák",
        "teacher_email": "jan.novak@skola.cz",
        "teacher_phone": "+420 987 654 321",
        "children_count": "25",
        "teachers_count": "2",
        "special_requirements": "Jeden žák na vozíku",
        "reset_link": "https://budezivo.cz/reset-password?token=abc123",
        "activation_link": "https://budezivo.cz/activate?token=xyz789",
        "dashboard_url": "https://budezivo.cz/admin",
        "booking_url": "https://budezivo.cz/booking/demo",
        "cancellation_reason": "Nemoc ve třídě",
        "rejection_reason": "Termín je již obsazen",
    }
    
    try:
        result = get_template(template_name, sample_data)
        return {
            "template_name": template_name,
            "subject": result["subject"],
            "html": result["html"],
            "text": result.get("text", ""),
            "sample_data": sample_data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variables")
async def get_template_variables():
    """Get all available template variables with descriptions."""
    return {
        "variables": TEMPLATE_VARIABLES,
        "count": len(TEMPLATE_VARIABLES),
    }


@router.post("/test", response_model=TestEmailResponse)
async def send_test_email(
    request: TestEmailRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send test email to verify email configuration.
    
    Requires authentication. Only sends to the specified email address.
    Uses sample data for template variables.
    """
    # Validate template exists
    if request.email_type not in get_available_templates():
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown email type: {request.email_type}. Available: {get_available_templates()}"
        )
    
    # Sample data for test
    test_data = {
        "user_name": "Test User",
        "user_email": request.email,
        "institution_name": "Testovací Instituce",
        "institution_email": "test@budezivo.cz",
        "institution_phone": "+420 123 456 789",
        "institution_address": "Testovací 123, Praha",
        "program_name": "Testovací Program",
        "program_description": "Toto je testovací email.",
        "program_duration": "60",
        "reservation_date": "1. 1. 2026",
        "reservation_time": "09:00 - 10:00",
        "school_name": "Testovací Škola",
        "teacher_name": "Test Teacher",
        "teacher_email": request.email,
        "teacher_phone": "+420 111 222 333",
        "children_count": "20",
        "teachers_count": "2",
        "special_requirements": "Žádné",
        "reset_link": "https://budezivo.cz/reset?token=test123",
        "activation_link": "https://budezivo.cz/activate?token=test456",
        "dashboard_url": "https://budezivo.cz/admin",
        "booking_url": "https://budezivo.cz/booking/test",
        "cancellation_reason": "Test zrušení",
        "rejection_reason": "Test odmítnutí",
    }
    
    # Send test email
    result = await EmailService.send_transactional_email(
        template_name=request.email_type,
        to_email=request.email,
        data=test_data,
    )
    
    # Log the test email
    try:
        log_repo = EmailLogRepositorySupabase(db)
        await log_repo.create({
            "institution_id": current_user["institution_id"],
            "recipient_email": request.email,
            "subject": f"[TEST] {request.email_type}",
            "status": result.get("status", "unknown"),
            "error_message": result.get("error"),
            "email_id": result.get("email_id"),
        })
    except Exception as e:
        logger.warning(f"Failed to log test email: {e}")
    
    return TestEmailResponse(
        status=result.get("status", "unknown"),
        message=result.get("message", ""),
        email_id=result.get("email_id"),
        template_name=request.email_type,
    )


@router.get("/logs")
async def get_email_logs(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
):
    """Get email logs for current institution."""
    log_repo = EmailLogRepositorySupabase(db)
    logs = await log_repo.find_by_institution(current_user["institution_id"], limit=limit)
    return {
        "logs": logs,
        "count": len(logs),
    }
