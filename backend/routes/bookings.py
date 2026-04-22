"""
Booking/Reservation management routes.
Uses Supabase (PostgreSQL) for database operations.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from models.schemas import BookingCreate, Booking, BookingUpdate, PublicBooking
from core.security import get_current_user
from database.supabase import get_db, AsyncSessionLocal
from database.supabase_repositories import (
    BookingRepositorySupabase, 
    UserRepositorySupabase, 
    SchoolRepositorySupabase,
    ProgramRepositorySupabase,
    InstitutionRepositorySupabase,
    EmailTemplateRepositorySupabase,
    EmailLogRepositorySupabase
)
from services.email_service import (
    EmailService, 
    trigger_reservation_created_emails,
    trigger_reservation_confirmed_email,
    trigger_reservation_cancelled_email,
    trigger_reservation_rescheduled_email,
)
from services.collision_service import check_booking_collision, check_lecturer_collision_for_assignment
from services.collision_classifier import classify as classify_collision
from services.lecturer_assignment_service import pick_main_lecturer, SOURCE_MANUAL, SOURCE_UNASSIGNED
from routes.audit import log_action

from pydantic import BaseModel as PydanticBaseModel

class BulkStatusRequest(PydanticBaseModel):
    booking_ids: List[str]
    status: str  # confirmed, cancelled, completed

class AssignLecturerRequest(PydanticBaseModel):
    lecturer_id: str

router = APIRouter(prefix="/bookings", tags=["Bookings"])
logger = logging.getLogger(__name__)
_booking_limiter = Limiter(key_func=get_remote_address)

# Fields to strip from public booking responses
_INTERNAL_BOOKING_FIELDS = {
    "assigned_lecturer_id", "assigned_lecturer_name", "assigned_lecturer_at",
    "terms_accepted_at", "terms_accepted_text_version",
    "institution_id", "actual_students", "actual_teachers", "notes",
}


def _strip_internal_fields(booking: dict) -> dict:
    """Remove internal metadata from booking for public response."""
    return {k: v for k, v in booking.items() if k not in _INTERNAL_BOOKING_FIELDS}


async def _resolve_main_lecturer(
    db: AsyncSession, institution_id: str, booking_data: BookingCreate,
    admin_override: Optional[dict] = None,
) -> dict:
    """
    Resolve which main lecturer to assign. Admin overrides bypass auto-pick (source=manual_admin).
    Raises HTTPException(409) if the program has a lecturer pool but no one is available.
    """
    program_repo = ProgramRepositorySupabase(db)
    program_row = await program_repo.find_by_id(booking_data.program_id, institution_id)
    if not program_row:
        raise HTTPException(status_code=404, detail="Program nenalezen")

    # Admin explicit override wins
    if admin_override and admin_override.get("assigned_lecturer_id"):
        # Validate this lecturer is main-mode and available
        from sqlalchemy import select
        from database.models import User
        import uuid as _uuid
        r = await db.execute(select(User).where(User.id == _uuid.UUID(admin_override["assigned_lecturer_id"])))
        u = r.scalar_one_or_none()
        if not u or u.lecturer_mode != "main":
            raise HTTPException(
                status_code=400,
                detail="Zvolený lektor není v režimu hlavního lektora (máte vybraného Náslech/trainee — hlavní lektor musí být zadán zvlášť).",
            )
        return {
            "lecturer_id": str(u.id),
            "lecturer_name": u.name or u.email,
            "source": SOURCE_MANUAL,
            "reason": f"{u.name or u.email} — ručně přiřazeno administrátorem",
        }

    # Load full ORM program object for service
    from sqlalchemy import select
    from database.models import Program
    import uuid as _uuid
    r = await db.execute(select(Program).where(Program.id == _uuid.UUID(booking_data.program_id)))
    program_obj = r.scalar_one_or_none()
    if program_obj is None:
        raise HTTPException(status_code=404, detail="Program nenalezen")

    result = await pick_main_lecturer(
        db, institution_id, program_obj, booking_data.date, booking_data.time_block,
    )
    if result is None:
        raise HTTPException(
            status_code=409,
            detail="Pro tento termín není k dispozici žádný hlavní lektor (všichni kandidáti mají kolize nebo nejsou v rozvrhu). Zvolte prosím jiný termín.",
        )
    return result


@router.post("", response_model=Booking)
async def create_booking(
    booking_data: BookingCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create booking for authenticated user."""
    # Check for collisions
    collision_error = await check_booking_collision(
        db, current_user["institution_id"], booking_data.program_id,
        booking_data.date, booking_data.time_block
    )
    if collision_error:
        raise HTTPException(status_code=409, detail=classify_collision(collision_error))

    # Resolve main lecturer (admin may pre-fill assigned_lecturer_id for manual override)
    payload = booking_data.model_dump()
    admin_override = None
    if payload.get("assigned_lecturer_id"):
        admin_override = {"assigned_lecturer_id": payload["assigned_lecturer_id"]}
    resolved = await _resolve_main_lecturer(
        db, current_user["institution_id"], booking_data, admin_override
    )
    payload.update({
        "assigned_lecturer_id": resolved["lecturer_id"],
        "assigned_lecturer_name": resolved["lecturer_name"],
        "assigned_lecturer_at": datetime.now(timezone.utc) if resolved["lecturer_id"] else None,
        "assignment_source": resolved["source"],
        "assignment_reason": resolved["reason"],
    })

    booking_repo = BookingRepositorySupabase(db)
    booking = await booking_repo.create(payload, current_user["institution_id"])
    return booking


@router.post("/public/{institution_id}", response_model=PublicBooking)
@_booking_limiter.limit("10/minute")
async def create_public_booking(
    institution_id: str,
    booking_data: BookingCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create public booking without authentication."""
    # Validate terms acceptance
    if not booking_data.terms_accepted:
        raise HTTPException(
            status_code=400, 
            detail="Pro odeslání rezervace je nutné souhlasit s podmínkami"
        )
    
    booking_repo = BookingRepositorySupabase(db)
    school_repo = SchoolRepositorySupabase(db)
    program_repo = ProgramRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)
    template_repo = EmailTemplateRepositorySupabase(db)
    log_repo = EmailLogRepositorySupabase(db)
    
    # Handle demo institution
    if institution_id == "demo":
        demo_booking = {
            "id": f"demo-{datetime.now(timezone.utc).timestamp()}",
            "institution_id": "demo",
            "program_id": booking_data.program_id,
            "date": booking_data.date,
            "time_block": booking_data.time_block,
            "school_name": booking_data.school_name,
            "group_type": booking_data.group_type,
            "age_or_class": booking_data.age_or_class,
            "num_students": booking_data.num_students,
            "num_teachers": booking_data.num_teachers,
            "special_requirements": booking_data.special_requirements,
            "contact_name": booking_data.contact_name,
            "contact_email": booking_data.contact_email,
            "contact_phone": booking_data.contact_phone,
            "gdpr_consent": booking_data.gdpr_consent,
            "terms_accepted": booking_data.terms_accepted,
            "terms_accepted_at": datetime.now(timezone.utc).isoformat() if booking_data.terms_accepted else None,
            "terms_accepted_text_version": booking_data.terms_accepted_text_version,
            "status": "pending",
            "actual_students": None,
            "actual_teachers": None,
            "assigned_lecturer_id": None,
            "assigned_lecturer_name": None,
            "assigned_lecturer_at": None,
            "notes": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        logger.info(f"Demo booking created for {booking_data.contact_email}")
        return _strip_internal_fields(demo_booking)
    
    # Create booking
    # First check for collisions
    collision_error = await check_booking_collision(
        db, institution_id, booking_data.program_id, booking_data.date, booking_data.time_block
    )
    if collision_error:
        raise HTTPException(status_code=409, detail=classify_collision(collision_error))

    # Resolve main lecturer (auto-pick; public flow never has admin override)
    resolved = await _resolve_main_lecturer(db, institution_id, booking_data, admin_override=None)

    payload = booking_data.model_dump()
    payload.update({
        "assigned_lecturer_id": resolved["lecturer_id"],
        "assigned_lecturer_name": resolved["lecturer_name"],
        "assigned_lecturer_at": datetime.now(timezone.utc) if resolved["lecturer_id"] else None,
        "assignment_source": resolved["source"],
        "assignment_reason": resolved["reason"],
    })

    booking = await booking_repo.create(payload, institution_id)
    
    # Create or update school record
    school = await school_repo.find_by_email(institution_id, booking_data.contact_email)
    if school:
        await school_repo.increment_booking_count(school["id"])
    else:
        await school_repo.create({
            "name": booking_data.school_name,
            "contact_person": booking_data.contact_name,
            "email": booking_data.contact_email,
            "phone": booking_data.contact_phone,
        }, institution_id)
    
    logger.info(f"Booking created: {booking['id']} for {booking_data.contact_email}")
    
    # Strip internal fields from public response (keep full booking for email processing)
    public_booking = _strip_internal_fields(booking)
    # Send confirmation emails in background (if program has email enabled)
    try:
        program = await program_repo.find_by_id(booking_data.program_id, institution_id)
        institution = await institution_repo.find_by_id_with_theme(institution_id)
        
        if program and program.get("send_email_notification", False):
            email_template = await template_repo.find_by_program(booking_data.program_id)
            
            # Send emails asynchronously using new trigger system
            async def send_booking_emails():
                try:
                    # Use custom template if available, otherwise use transactional templates
                    if email_template and email_template.get("subject") and email_template.get("body"):
                        result = await EmailService.send_booking_confirmation(
                            booking_data=booking,
                            program_data=program,
                            institution_data=institution or {},
                            email_template=email_template
                        )
                        
                        # Log custom template email
                        await log_repo.create({
                            "institution_id": institution_id,
                            "program_id": booking_data.program_id,
                            "reservation_id": booking["id"],
                            "recipient_email": booking_data.contact_email,
                            "subject": "Custom template",
                            "status": result.get("status", "sent"),
                            "error_message": result.get("error"),
                            "email_id": result.get("email_id"),
                        })
                    else:
                        # Use standard transactional emails
                        results = await trigger_reservation_created_emails(
                            booking_data=booking,
                            program_data=program,
                            institution_data=institution or {},
                        )
                        
                        # Log emails
                        for recipient, result in results.items():
                            await log_repo.create({
                                "institution_id": institution_id,
                                "program_id": booking_data.program_id,
                                "reservation_id": booking["id"],
                                "recipient_email": result.get("actual_recipient", booking_data.contact_email),
                                "subject": f"reservation_created_{recipient}",
                                "status": result.get("status", "sent"),
                                "error_message": result.get("error"),
                                "email_id": result.get("email_id"),
                            })
                    
                    logger.info(f"Booking confirmation emails sent for {booking['id']}")
                except Exception as e:
                    logger.error(f"Failed to send booking emails: {str(e)}")
            
            # Run in background
            background_tasks.add_task(send_booking_emails)
    except Exception as e:
        logger.error(f"Error preparing booking email: {str(e)}")
    
    return public_booking


@router.get("", response_model=List[Booking])
async def get_bookings(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all bookings for institution."""
    booking_repo = BookingRepositorySupabase(db)
    return await booking_repo.find_by_institution(current_user["institution_id"])


@router.get("/{booking_id}", response_model=Booking)
async def get_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get single booking by ID."""
    booking_repo = BookingRepositorySupabase(db)
    booking = await booking_repo.find_by_id(booking_id, current_user["institution_id"])
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.patch("/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    status: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update booking status and trigger appropriate emails."""
    booking_repo = BookingRepositorySupabase(db)
    program_repo = ProgramRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)
    log_repo = EmailLogRepositorySupabase(db)
    
    # Get booking before update
    booking = await booking_repo.find_by_id(booking_id, current_user["institution_id"])
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    old_status = booking.get("status")
    
    # Update status
    result = await booking_repo.update_status(
        booking_id,
        current_user["institution_id"],
        status
    )
    if result == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Trigger emails based on status change
    async def send_status_email():
        try:
            program = await program_repo.find_by_id(booking.get("program_id"), current_user["institution_id"])
            institution = await institution_repo.find_by_id_with_theme(current_user["institution_id"])
            
            if not program or not institution:
                return
            
            email_result = None
            template_name = None
            
            if status == "confirmed" and old_status != "confirmed":
                email_result = await trigger_reservation_confirmed_email(
                    booking_data=booking,
                    program_data=program,
                    institution_data=institution,
                )
                template_name = "reservation_confirmed"
                
            elif status == "cancelled" and old_status != "cancelled":
                email_result = await trigger_reservation_cancelled_email(
                    booking_data=booking,
                    program_data=program,
                    institution_data=institution,
                    cancellation_reason="",
                )
                template_name = "reservation_cancelled"
                
                # Waitlist Phase 2: notify candidates about freed slot
                try:
                    from services.waitlist_service import on_booking_cancelled
                    await on_booking_cancelled(
                        db,
                        program_id=booking.get("program_id", ""),
                        date=booking.get("date", ""),
                        time_block=booking.get("time_block", ""),
                        institution_id=current_user["institution_id"],
                    )
                except Exception as wl_err:
                    logger.warning(f"Waitlist notify on cancel failed: {wl_err}")
            
            # Log email if sent
            if email_result and template_name:
                await log_repo.create({
                    "institution_id": current_user["institution_id"],
                    "program_id": booking.get("program_id"),
                    "reservation_id": booking_id,
                    "recipient_email": booking.get("contact_email", ""),
                    "subject": f"{template_name}",
                    "status": email_result.get("status", "sent"),
                    "error_message": email_result.get("error"),
                    "email_id": email_result.get("email_id"),
                })
                
        except Exception as e:
            logger.error(f"Failed to send status change email: {str(e)}")
    
    background_tasks.add_task(send_status_email)

    # Audit log
    await log_action(
        db, institution_id=current_user["institution_id"],
        user_id=current_user["user_id"], user_email=current_user.get("email", ""),
        action=status, entity_type="reservation", entity_id=booking_id,
        details={"old_status": old_status, "new_status": status, "school": booking.get("school_name", "")},
    )
    
    return {"message": "Status updated"}


@router.put("/{booking_id}")
async def update_booking(
    booking_id: str,
    update_data: BookingUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update booking - role-based access. Sends reschedule email when date/time changes."""
    user_repo = UserRepositorySupabase(db)
    booking_repo = BookingRepositorySupabase(db)
    
    # Get current user's role
    user = await user_repo.find_by_id(current_user["user_id"])
    user_role = user.get("role", "viewer") if user else "viewer"
    
    # Check booking exists
    booking = await booking_repo.find_by_id(booking_id, current_user["institution_id"])
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Save original date/time before update
    original_date = booking.get("date", "")
    original_time = booking.get("time_block", "")
    
    # Role-based field access
    update_fields = {}
    
    # Admin/Správce can update everything
    if user_role in ["admin", "spravce"]:
        if update_data.status is not None:
            update_fields["status"] = update_data.status
        if update_data.actual_students is not None:
            update_fields["actual_students"] = update_data.actual_students
        if update_data.actual_teachers is not None:
            update_fields["actual_teachers"] = update_data.actual_teachers
        if update_data.notes is not None:
            update_fields["notes"] = update_data.notes
        if update_data.date is not None:
            update_fields["date"] = update_data.date
        if update_data.time_block is not None:
            update_fields["time_block"] = update_data.time_block
        if update_data.contact_email is not None:
            update_fields["contact_email"] = update_data.contact_email
        if update_data.contact_phone is not None:
            update_fields["contact_phone"] = update_data.contact_phone
        if update_data.contact_name is not None:
            update_fields["contact_name"] = update_data.contact_name
    
    # Edukator can edit date and contact
    elif user_role == "edukator":
        if update_data.status is not None:
            update_fields["status"] = update_data.status
        if update_data.actual_students is not None:
            update_fields["actual_students"] = update_data.actual_students
        if update_data.actual_teachers is not None:
            update_fields["actual_teachers"] = update_data.actual_teachers
        if update_data.notes is not None:
            update_fields["notes"] = update_data.notes
        if update_data.date is not None:
            update_fields["date"] = update_data.date
        if update_data.contact_email is not None:
            update_fields["contact_email"] = update_data.contact_email
        if update_data.contact_phone is not None:
            update_fields["contact_phone"] = update_data.contact_phone
        if update_data.contact_name is not None:
            update_fields["contact_name"] = update_data.contact_name
    
    # Pokladní can only update actual attendance
    elif user_role == "pokladni":
        if update_data.actual_students is not None:
            update_fields["actual_students"] = update_data.actual_students
        if update_data.actual_teachers is not None:
            update_fields["actual_teachers"] = update_data.actual_teachers
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    if not update_fields:
        return {"message": "No fields to update"}
    
    await booking_repo.update(booking_id, current_user["institution_id"], update_fields)
    
    # Check if date or time changed — send reschedule email
    new_date = update_fields.get("date", original_date)
    new_time = update_fields.get("time_block", original_time)
    date_changed = "date" in update_fields and update_fields["date"] != original_date
    time_changed = "time_block" in update_fields and update_fields["time_block"] != original_time
    
    if date_changed or time_changed:
        # Capture values for background task (avoid using request-scoped db)
        program_id = booking.get("program_id")
        institution_id = current_user["institution_id"]
        updated_booking = {**booking, "date": new_date, "time_block": new_time}
        
        async def send_reschedule_email():
            try:
                async with AsyncSessionLocal() as bg_db:
                    program_repo = ProgramRepositorySupabase(bg_db)
                    institution_repo = InstitutionRepositorySupabase(bg_db)
                    
                    program = await program_repo.find_by_id(program_id, institution_id)
                    institution = await institution_repo.find_by_id_with_theme(institution_id)
                    
                    if program and institution:
                        await trigger_reservation_rescheduled_email(
                            booking_data=updated_booking,
                            program_data=program,
                            institution_data=institution,
                            original_date=original_date,
                            original_time=original_time,
                        )
                        logger.info(f"Reschedule email sent for booking {booking_id}")
            except Exception as e:
                logger.error(f"Failed to send reschedule email for booking {booking_id}: {e}")
        
        background_tasks.add_task(send_reschedule_email)
    
    return {"message": "Booking updated", "updated_fields": list(update_fields.keys())}


@router.post("/bulk-status")
async def bulk_update_booking_status(
    request: BulkStatusRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk update status for multiple bookings. Triggers emails for each."""
    if request.status not in ["confirmed", "cancelled", "completed"]:
        raise HTTPException(status_code=400, detail="Neplatný stav. Povolené: confirmed, cancelled, completed")
    
    if not request.booking_ids:
        raise HTTPException(status_code=400, detail="Žádné rezervace nebyly vybrány")
    
    user_repo = UserRepositorySupabase(db)
    booking_repo = BookingRepositorySupabase(db)
    program_repo = ProgramRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)
    log_repo = EmailLogRepositorySupabase(db)
    
    # Check permissions
    admin_user = await user_repo.find_by_id(current_user["user_id"])
    if not admin_user or admin_user.get("role") not in ["admin", "spravce", "edukator"]:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění pro hromadné akce")
    
    # Get bookings before update (for email sending)
    bookings_before = await booking_repo.find_by_ids(request.booking_ids, current_user["institution_id"])
    
    if not bookings_before:
        raise HTTPException(status_code=404, detail="Žádné rezervace nenalezeny")
    
    # Perform bulk update
    updated_count = await booking_repo.bulk_update_status(
        request.booking_ids, current_user["institution_id"], request.status
    )
    
    # Trigger emails in background for each booking
    async def send_bulk_emails():
        try:
            institution = await institution_repo.find_by_id_with_theme(current_user["institution_id"])
            for booking in bookings_before:
                old_status = booking.get("status")
                if old_status == request.status:
                    continue
                try:
                    program = await program_repo.find_by_id(
                        booking.get("program_id"), current_user["institution_id"]
                    )
                    if not program or not institution:
                        continue
                    
                    email_result = None
                    template_name = None
                    
                    if request.status == "confirmed" and old_status != "confirmed":
                        email_result = await trigger_reservation_confirmed_email(
                            booking_data=booking, program_data=program,
                            institution_data=institution,
                        )
                        template_name = "reservation_confirmed"
                    elif request.status == "cancelled" and old_status != "cancelled":
                        email_result = await trigger_reservation_cancelled_email(
                            booking_data=booking, program_data=program,
                            institution_data=institution, cancellation_reason="",
                        )
                        template_name = "reservation_cancelled"
                        
                        # Waitlist Phase 2: notify candidates about freed slot
                        try:
                            from services.waitlist_service import on_booking_cancelled
                            await on_booking_cancelled(
                                db,
                                program_id=booking.get("program_id", ""),
                                date=booking.get("date", ""),
                                time_block=booking.get("time_block", ""),
                                institution_id=current_user["institution_id"],
                            )
                        except Exception as wl_err:
                            logger.warning(f"Waitlist notify on cancel failed: {wl_err}")
                    
                    if email_result and template_name:
                        await log_repo.create({
                            "institution_id": current_user["institution_id"],
                            "program_id": booking.get("program_id"),
                            "reservation_id": booking.get("id"),
                            "recipient_email": booking.get("contact_email", ""),
                            "subject": f"bulk_{template_name}",
                            "status": email_result.get("status", "sent"),
                            "error_message": email_result.get("error"),
                            "email_id": email_result.get("email_id"),
                        })
                except Exception as e:
                    logger.error(f"Bulk email error for booking {booking.get('id')}: {str(e)}")
        except Exception as e:
            logger.error(f"Bulk email send failed: {str(e)}")
    
    background_tasks.add_task(send_bulk_emails)
    
    logger.info(f"Bulk status update: {updated_count} bookings -> {request.status}")
    return {
        "message": f"Stav {updated_count} rezervací byl změněn na '{request.status}'",
        "updated_count": updated_count,
        "status": request.status
    }


@router.post("/{booking_id}/assign-lecturer")
async def assign_lecturer_to_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Self-assign as lecturer to a booking."""
    user_repo = UserRepositorySupabase(db)
    booking_repo = BookingRepositorySupabase(db)
    
    # Get current user's role and name
    user = await user_repo.find_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_role = user.get("role", "viewer")
    user_name = user.get("name") or user.get("email", "Unknown")
    
    # Only lektor can self-assign
    if user_role not in ["lektor", "admin", "spravce", "edukator"]:
        raise HTTPException(status_code=403, detail="Only lecturers can assign themselves")
    
    # Check booking exists
    booking = await booking_repo.find_by_id(booking_id, current_user["institution_id"])
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Check if already assigned
    if booking.get("assigned_lecturer_id"):
        raise HTTPException(status_code=400, detail="Booking already has assigned lecturer")
    
    # Check for lecturer time collisions
    collision_error = await check_lecturer_collision_for_assignment(
        db, current_user["user_id"], current_user["institution_id"], booking_id
    )
    if collision_error:
        raise HTTPException(status_code=409, detail=collision_error)
    
    # Assign lecturer
    await booking_repo.assign_lecturer(
        booking_id,
        current_user["institution_id"],
        current_user["user_id"],
        user_name
    )
    
    logger.info(f"Lecturer {user_name} assigned to booking {booking_id}")
    return {"message": "Lecturer assigned", "lecturer_name": user_name}


@router.delete("/{booking_id}/unassign-lecturer")
async def unassign_lecturer_from_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unassign lecturer from booking."""
    user_repo = UserRepositorySupabase(db)
    booking_repo = BookingRepositorySupabase(db)
    
    user = await user_repo.find_by_id(current_user["user_id"])
    user_role = user.get("role", "viewer") if user else "viewer"
    
    booking = await booking_repo.find_by_id(booking_id, current_user["institution_id"])
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Only admin or the assigned lecturer can unassign
    if user_role not in ["admin", "spravce", "edukator"]:
        if booking.get("assigned_lecturer_id") != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Only admin or assigned lecturer can unassign")
    
    await booking_repo.unassign_lecturer(booking_id, current_user["institution_id"])
    return {"message": "Lecturer unassigned"}


@router.post("/{booking_id}/assign-lecturer-admin")
async def admin_assign_lecturer_to_booking(
    booking_id: str,
    request: AssignLecturerRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin assigns a specific lecturer to a booking."""
    user_repo = UserRepositorySupabase(db)
    booking_repo = BookingRepositorySupabase(db)
    
    # Check current user is admin
    admin_user = await user_repo.find_by_id(current_user["user_id"])
    if not admin_user or admin_user.get("role") not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Pouze admin může přiřadit lektora")
    
    # Check booking exists
    booking = await booking_repo.find_by_id(booking_id, current_user["institution_id"])
    if not booking:
        raise HTTPException(status_code=404, detail="Rezervace nenalezena")
    
    # Get lecturer details
    lecturer = await user_repo.find_by_id(request.lecturer_id)
    if not lecturer:
        raise HTTPException(status_code=404, detail="Lektor nenalezen")
    
    if lecturer.get("institution_id") != current_user["institution_id"]:
        raise HTTPException(status_code=403, detail="Lektor nepatří do vaší instituce")

    # Main-lecturer only — training lecturers cannot be assigned as main
    if lecturer.get("lecturer_mode") == "training":
        raise HTTPException(
            status_code=400,
            detail="Tento lektor je v režimu Náslech (training). Jako hlavního lektora lze přiřadit pouze lektora v hlavním režimu.",
        )

    # Check for lecturer time collisions
    collision_error = await check_lecturer_collision_for_assignment(
        db, request.lecturer_id, current_user["institution_id"], booking_id
    )
    if collision_error:
        raise HTTPException(status_code=409, detail=collision_error)

    lecturer_name = lecturer.get("name") or lecturer.get("email", "Unknown")
    
    # Assign lecturer
    await booking_repo.assign_lecturer(
        booking_id,
        current_user["institution_id"],
        request.lecturer_id,
        lecturer_name
    )
    
    logger.info(f"Admin assigned lecturer {lecturer_name} to booking {booking_id}")
    return {"message": "Lektor přiřazen", "lecturer_name": lecturer_name}
