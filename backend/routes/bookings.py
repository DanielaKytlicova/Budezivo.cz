"""
Booking/Reservation management routes.
Uses Supabase (PostgreSQL) for database operations.
"""
import logging
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import BookingCreate, Booking, BookingUpdate
from core.security import get_current_user
from database.supabase import get_db
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
)

router = APIRouter(prefix="/bookings", tags=["Bookings"])
logger = logging.getLogger(__name__)


@router.post("", response_model=Booking)
async def create_booking(
    booking_data: BookingCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create booking for authenticated user."""
    booking_repo = BookingRepositorySupabase(db)
    booking = await booking_repo.create(
        booking_data.model_dump(),
        current_user["institution_id"]
    )
    return booking


@router.post("/public/{institution_id}", response_model=Booking)
async def create_public_booking(
    institution_id: str,
    booking_data: BookingCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create public booking without authentication."""
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
        return demo_booking
    
    # Create booking
    booking = await booking_repo.create(booking_data.model_dump(), institution_id)
    
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
    
    # Send confirmation emails in background (if program has email enabled)
    try:
        program = await program_repo.find_by_id(booking_data.program_id, institution_id)
        institution = await institution_repo.find_by_id(institution_id)
        
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
    
    return booking


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
            institution = await institution_repo.find_by_id(current_user["institution_id"])
            
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
    
    return {"message": "Status updated"}


@router.put("/{booking_id}")
async def update_booking(
    booking_id: str,
    update_data: BookingUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update booking - role-based access."""
    user_repo = UserRepositorySupabase(db)
    booking_repo = BookingRepositorySupabase(db)
    
    # Get current user's role
    user = await user_repo.find_by_id(current_user["user_id"])
    user_role = user.get("role", "viewer") if user else "viewer"
    
    # Check booking exists
    booking = await booking_repo.find_by_id(booking_id, current_user["institution_id"])
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
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
    return {"message": "Booking updated", "updated_fields": list(update_fields.keys())}


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
