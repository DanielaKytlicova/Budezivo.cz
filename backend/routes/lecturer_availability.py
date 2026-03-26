"""
Routes for lecturer availability management.
Handles recurring availability and time-off (blockages).
"""
import uuid
import logging
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from database.supabase import get_db
from database.models import LecturerAvailability, LecturerTimeOff, User
from models.schemas import (
    LecturerAvailabilityCreate,
    LecturerAvailabilityUpdate,
    LecturerAvailabilityResponse,
    LecturerTimeOffCreate,
    LecturerTimeOffUpdate,
    LecturerTimeOffResponse,
)
from core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lecturer-availability", tags=["Lecturer Availability"])


def to_dict(obj, exclude: set = None):
    """Convert SQLAlchemy model to dict."""
    result = {}
    for c in obj.__table__.columns:
        if exclude and c.name in exclude:
            continue
        value = getattr(obj, c.name)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, datetime):
            value = value.isoformat()
        result[c.name] = value
    return result


# ========================
# RECURRING AVAILABILITY
# ========================

@router.get("/recurring", response_model=List[LecturerAvailabilityResponse])
async def get_recurring_availability(
    lecturer_id: str = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recurring availability for a lecturer."""
    target_id = lecturer_id or current_user["user_id"]
    institution_id = current_user["institution_id"]

    result = await db.execute(
        select(LecturerAvailability).where(and_(
            LecturerAvailability.lecturer_id == uuid.UUID(target_id),
            LecturerAvailability.institution_id == uuid.UUID(institution_id)
        )).order_by(LecturerAvailability.day_of_week, LecturerAvailability.start_time)
    )
    items = result.scalars().all()
    return [to_dict(item) for item in items]


@router.post("/recurring", response_model=List[LecturerAvailabilityResponse])
async def create_recurring_availability(
    data: LecturerAvailabilityCreate,
    lecturer_id: str = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create recurring availability for one or more days."""
    target_id = lecturer_id or current_user["user_id"]
    institution_id = current_user["institution_id"]

    # Validate role - admins can set for anyone, lecturers only for themselves
    if target_id != current_user["user_id"] and current_user["role"] not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění upravovat dostupnost jiného lektora.")

    created = []
    for dow in data.days_of_week:
        if dow < 0 or dow > 6:
            continue
        avail = LecturerAvailability(
            id=uuid.uuid4(),
            lecturer_id=uuid.UUID(target_id),
            institution_id=uuid.UUID(institution_id),
            day_of_week=dow,
            start_time=data.start_time,
            end_time=data.end_time,
            is_recurring=True,
        )
        db.add(avail)
        created.append(avail)

    await db.commit()
    for a in created:
        await db.refresh(a)
    return [to_dict(a) for a in created]


@router.put("/recurring/{avail_id}", response_model=LecturerAvailabilityResponse)
async def update_recurring_availability(
    avail_id: str,
    data: LecturerAvailabilityUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a recurring availability block."""
    result = await db.execute(
        select(LecturerAvailability).where(and_(
            LecturerAvailability.id == uuid.UUID(avail_id),
            LecturerAvailability.institution_id == uuid.UUID(current_user["institution_id"])
        ))
    )
    avail = result.scalar_one_or_none()
    if not avail:
        raise HTTPException(status_code=404, detail="Blok dostupnosti nenalezen.")

    if str(avail.lecturer_id) != current_user["user_id"] and current_user["role"] not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění.")

    avail.day_of_week = data.day_of_week
    avail.start_time = data.start_time
    avail.end_time = data.end_time
    avail.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(avail)
    return to_dict(avail)


@router.delete("/recurring/{avail_id}")
async def delete_recurring_availability(
    avail_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a recurring availability block."""
    result = await db.execute(
        select(LecturerAvailability).where(and_(
            LecturerAvailability.id == uuid.UUID(avail_id),
            LecturerAvailability.institution_id == uuid.UUID(current_user["institution_id"])
        ))
    )
    avail = result.scalar_one_or_none()
    if not avail:
        raise HTTPException(status_code=404, detail="Blok dostupnosti nenalezen.")

    if str(avail.lecturer_id) != current_user["user_id"] and current_user["role"] not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění.")

    await db.delete(avail)
    await db.commit()
    return {"message": "Blok dostupnosti smazán."}


# ========================
# TIME OFF / BLOCKAGES
# ========================

@router.get("/time-off", response_model=List[LecturerTimeOffResponse])
async def get_time_off(
    lecturer_id: str = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get time-off blocks for a lecturer."""
    target_id = lecturer_id or current_user["user_id"]
    institution_id = current_user["institution_id"]

    result = await db.execute(
        select(LecturerTimeOff).where(and_(
            LecturerTimeOff.lecturer_id == uuid.UUID(target_id),
            LecturerTimeOff.institution_id == uuid.UUID(institution_id)
        )).order_by(LecturerTimeOff.start_date, LecturerTimeOff.start_time)
    )
    items = result.scalars().all()
    return [to_dict(item) for item in items]


@router.post("/time-off", response_model=LecturerTimeOffResponse)
async def create_time_off(
    data: LecturerTimeOffCreate,
    lecturer_id: str = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a time-off / blockage."""
    target_id = lecturer_id or current_user["user_id"]
    institution_id = current_user["institution_id"]

    if target_id != current_user["user_id"] and current_user["role"] not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění.")

    time_off = LecturerTimeOff(
        id=uuid.uuid4(),
        lecturer_id=uuid.UUID(target_id),
        institution_id=uuid.UUID(institution_id),
        start_date=data.start_date,
        end_date=data.end_date,
        start_time=data.start_time,
        end_time=data.end_time,
        reason=data.reason,
    )
    db.add(time_off)
    await db.commit()
    await db.refresh(time_off)
    return to_dict(time_off)


@router.put("/time-off/{time_off_id}", response_model=LecturerTimeOffResponse)
async def update_time_off(
    time_off_id: str,
    data: LecturerTimeOffUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a time-off block."""
    result = await db.execute(
        select(LecturerTimeOff).where(and_(
            LecturerTimeOff.id == uuid.UUID(time_off_id),
            LecturerTimeOff.institution_id == uuid.UUID(current_user["institution_id"])
        ))
    )
    time_off = result.scalar_one_or_none()
    if not time_off:
        raise HTTPException(status_code=404, detail="Blokace nenalezena.")

    if str(time_off.lecturer_id) != current_user["user_id"] and current_user["role"] not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění.")

    if data.start_date is not None:
        time_off.start_date = data.start_date
    if data.end_date is not None:
        time_off.end_date = data.end_date
    if data.start_time is not None:
        time_off.start_time = data.start_time
    if data.end_time is not None:
        time_off.end_time = data.end_time
    if data.reason is not None:
        time_off.reason = data.reason
    time_off.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(time_off)
    return to_dict(time_off)


@router.delete("/time-off/{time_off_id}")
async def delete_time_off(
    time_off_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a time-off block."""
    result = await db.execute(
        select(LecturerTimeOff).where(and_(
            LecturerTimeOff.id == uuid.UUID(time_off_id),
            LecturerTimeOff.institution_id == uuid.UUID(current_user["institution_id"])
        ))
    )
    time_off = result.scalar_one_or_none()
    if not time_off:
        raise HTTPException(status_code=404, detail="Blokace nenalezena.")

    if str(time_off.lecturer_id) != current_user["user_id"] and current_user["role"] not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění.")

    await db.delete(time_off)
    await db.commit()
    return {"message": "Blokace smazána."}


# ========================
# COMPUTED AVAILABILITY CHECK
# ========================

@router.get("/check")
async def check_lecturer_available(
    lecturer_id: str,
    date: str,
    start_time: str,
    end_time: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if a lecturer is available at a specific date+time.
    Returns { available: bool, reason: str | null }
    """
    from datetime import date as date_type
    d = date_type.fromisoformat(date)
    day_of_week = d.weekday()  # 0=Monday
    institution_id = current_user["institution_id"]

    # 1. Check recurring availability
    result = await db.execute(
        select(LecturerAvailability).where(and_(
            LecturerAvailability.lecturer_id == uuid.UUID(lecturer_id),
            LecturerAvailability.institution_id == uuid.UUID(institution_id),
            LecturerAvailability.day_of_week == day_of_week
        ))
    )
    avail_blocks = result.scalars().all()

    def time_to_min(t):
        h, m = map(int, t.split(':'))
        return h * 60 + m

    req_start = time_to_min(start_time)
    req_end = time_to_min(end_time)

    # Check if requested time fits in any availability block
    in_availability = False
    for block in avail_blocks:
        block_start = time_to_min(block.start_time)
        block_end = time_to_min(block.end_time)
        if req_start >= block_start and req_end <= block_end:
            in_availability = True
            break

    if not in_availability:
        return {"available": False, "reason": "Lektor nemá nastavenou dostupnost pro tento čas."}

    # 2. Check time-off / blockages
    result = await db.execute(
        select(LecturerTimeOff).where(and_(
            LecturerTimeOff.lecturer_id == uuid.UUID(lecturer_id),
            LecturerTimeOff.institution_id == uuid.UUID(institution_id),
            LecturerTimeOff.start_date <= date,
            LecturerTimeOff.end_date >= date
        ))
    )
    blockages = result.scalars().all()

    for block in blockages:
        if block.start_time is None or block.end_time is None:
            # All-day blockage
            reason = block.reason or "Celodenní blokace"
            return {"available": False, "reason": reason}

        block_start = time_to_min(block.start_time)
        block_end = time_to_min(block.end_time)
        # Check overlap
        if req_start < block_end and req_end > block_start:
            reason = block.reason or "Blokace v tomto čase"
            return {"available": False, "reason": reason}

    return {"available": True, "reason": None}


# ========================
# WEEKLY VIEW DATA
# ========================

@router.get("/week-view")
async def get_week_view(
    lecturer_id: str = None,
    week_start: str = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get combined weekly view data for the calendar.
    Returns recurring blocks + time-offs for the given week.
    """
    from datetime import date as date_type, timedelta
    target_id = lecturer_id or current_user["user_id"]
    institution_id = current_user["institution_id"]

    if week_start:
        start_date = date_type.fromisoformat(week_start)
    else:
        from datetime import date as dt
        today = dt.today()
        start_date = today - timedelta(days=today.weekday())  # Monday

    end_date = start_date + timedelta(days=6)  # Sunday

    # Get recurring availability
    result = await db.execute(
        select(LecturerAvailability).where(and_(
            LecturerAvailability.lecturer_id == uuid.UUID(target_id),
            LecturerAvailability.institution_id == uuid.UUID(institution_id)
        )).order_by(LecturerAvailability.day_of_week, LecturerAvailability.start_time)
    )
    recurring = [to_dict(r) for r in result.scalars().all()]

    # Get time-offs that overlap this week
    result = await db.execute(
        select(LecturerTimeOff).where(and_(
            LecturerTimeOff.lecturer_id == uuid.UUID(target_id),
            LecturerTimeOff.institution_id == uuid.UUID(institution_id),
            LecturerTimeOff.start_date <= str(end_date),
            LecturerTimeOff.end_date >= str(start_date)
        )).order_by(LecturerTimeOff.start_date, LecturerTimeOff.start_time)
    )
    time_offs = [to_dict(t) for t in result.scalars().all()]

    return {
        "week_start": str(start_date),
        "week_end": str(end_date),
        "recurring": recurring,
        "time_offs": time_offs,
    }
