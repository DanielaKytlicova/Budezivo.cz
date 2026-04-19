"""
Waitlist API routes.
Public: POST /api/waitlist (create entry)
Admin: GET /api/waitlist, PATCH /api/waitlist/{id}
"""
import uuid
import logging
from datetime import datetime, timezone, date as date_type
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from database.supabase import get_db
from database.models import WaitlistEntry, Program
from core.security import get_current_user
from services.plan_service import require_feature

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])
logger = logging.getLogger(__name__)


# ============ Schemas ============

class WaitlistCreate(BaseModel):
    institution_id: str
    program_id: str
    teacher_name: str
    school_name: str
    email: str
    phone: Optional[str] = None
    participant_count: int = 1
    request_type: str = "specific_date"  # specific_date, date_range
    requested_date: Optional[str] = None
    range_start_date: Optional[str] = None
    range_end_date: Optional[str] = None
    preferred_time_of_day: str = "any"  # morning, midday, afternoon, any
    notes: Optional[str] = None


class WaitlistStatusUpdate(BaseModel):
    status: Optional[str] = None
    admin_note: Optional[str] = None


# ============ Helpers ============

def _to_dict(obj) -> dict:
    result = {}
    for c in obj.__table__.columns:
        value = getattr(obj, c.name)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, datetime):
            value = value.isoformat()
        result[c.name] = value
    return result


# ============ Public endpoint ============

@router.post("")
async def create_waitlist_entry(
    data: WaitlistCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new waitlist entry (public, no auth)."""
    # Validate program exists
    prog_result = await db.execute(
        select(Program).where(and_(
            Program.id == uuid.UUID(data.program_id),
            Program.institution_id == uuid.UUID(data.institution_id),
        ))
    )
    program = prog_result.scalar_one_or_none()
    if not program:
        raise HTTPException(status_code=404, detail="Program nenalezen")

    # Validate participant_count
    if data.participant_count < 1:
        raise HTTPException(status_code=400, detail="Počet účastníků musí být alespoň 1")

    # Validate request_type specifics
    today = date_type.today().isoformat()

    if data.request_type == 'specific_date':
        if not data.requested_date:
            raise HTTPException(status_code=400, detail="Pro konkrétní datum je nutné zadat requested_date")
        if data.requested_date < today:
            raise HTTPException(status_code=400, detail="Nelze zadat zájem o datum v minulosti")

    elif data.request_type == 'date_range':
        if not data.range_start_date or not data.range_end_date:
            raise HTTPException(status_code=400, detail="Pro časový rozsah je nutné zadat range_start_date a range_end_date")
        if data.range_start_date > data.range_end_date:
            raise HTTPException(status_code=400, detail="Začátek rozsahu musí být před koncem")
        if data.range_end_date < today:
            raise HTTPException(status_code=400, detail="Nelze zadat zájem o rozsah v minulosti")

    # Check for duplicate (same email + program + date)
    dup_query = select(WaitlistEntry).where(and_(
        WaitlistEntry.email == data.email,
        WaitlistEntry.program_id == uuid.UUID(data.program_id),
        WaitlistEntry.status == 'active',
    ))
    if data.request_type == 'specific_date':
        dup_query = dup_query.where(WaitlistEntry.requested_date == data.requested_date)
    dup_result = await db.execute(dup_query)
    if dup_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Pro tento program a termín již máte aktivní zájem")

    entry = WaitlistEntry(
        institution_id=uuid.UUID(data.institution_id),
        program_id=uuid.UUID(data.program_id),
        teacher_name=data.teacher_name,
        school_name=data.school_name,
        email=data.email,
        phone=data.phone,
        participant_count=data.participant_count,
        request_type=data.request_type,
        requested_date=data.requested_date,
        range_start_date=data.range_start_date,
        range_end_date=data.range_end_date,
        preferred_time_of_day=data.preferred_time_of_day,
        notes=data.notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    # Send confirmation email
    try:
        from services.email_service import EmailService
        from templates.emails.templates import waitlist_confirmation
        email_data = waitlist_confirmation({
            'teacher_name': data.teacher_name,
            'program_name': program.name_cs,
            'request_type': data.request_type,
            'requested_date': data.requested_date,
            'range_start_date': data.range_start_date,
            'range_end_date': data.range_end_date,
            'preferred_time': data.preferred_time_of_day,
            'participant_count': data.participant_count,
        })
        if EmailService.is_configured():
            await EmailService.send_email(
                to_email=data.email,
                subject=email_data['subject'],
                html_content=email_data['html'],
            )
    except Exception as e:
        logger.warning(f"Waitlist confirmation email failed: {e}")

    return _to_dict(entry)


# ============ Admin endpoints ============

@router.get("")
async def list_waitlist(
    program_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _guard=Depends(require_feature("waitlist")),
):
    """List waitlist entries for admin."""
    inst_uuid = uuid.UUID(current_user["institution_id"])
    query = select(WaitlistEntry).where(WaitlistEntry.institution_id == inst_uuid)

    if program_id:
        query = query.where(WaitlistEntry.program_id == uuid.UUID(program_id))
    if status:
        query = query.where(WaitlistEntry.status == status)

    query = query.order_by(WaitlistEntry.created_at.desc())
    result = await db.execute(query)
    entries = result.scalars().all()

    # Enrich with program names
    out = []
    for e in entries:
        d = _to_dict(e)
        prog = await db.execute(select(Program.name_cs).where(Program.id == e.program_id))
        d['program_name'] = prog.scalar_one_or_none() or ''
        out.append(d)

    return out


@router.get("/count/{program_id}")
async def get_waitlist_count(
    program_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get active waitlist count for a program (public)."""
    result = await db.execute(
        select(func.count(WaitlistEntry.id)).where(and_(
            WaitlistEntry.program_id == uuid.UUID(program_id),
            WaitlistEntry.status == 'active',
        ))
    )
    return {"count": result.scalar() or 0}


@router.patch("/{entry_id}")
async def update_waitlist_entry(
    entry_id: str,
    data: WaitlistStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _guard=Depends(require_feature("waitlist")),
):
    """Update waitlist entry status (admin)."""
    inst_uuid = uuid.UUID(current_user["institution_id"])
    result = await db.execute(
        select(WaitlistEntry).where(and_(
            WaitlistEntry.id == uuid.UUID(entry_id),
            WaitlistEntry.institution_id == inst_uuid,
        ))
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Záznam nenalezen")

    if data.status:
        if data.status not in ('active', 'contacted', 'booked', 'cancelled', 'expired'):
            raise HTTPException(status_code=400, detail="Neplatný status")
        entry.status = data.status

    if data.admin_note is not None:
        entry.admin_note = data.admin_note

    entry.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return _to_dict(entry)
