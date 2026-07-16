"""
Unified Availability API endpoints.
Provides program/lecturer slot evaluation and exception management.
"""
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database.supabase import get_db
from database.models import AvailabilityException, Program
from core.security import get_current_user
from core.permissions import ensure_role, BLOCK_MANAGE_ROLES
from services.availability_service import evaluate_program_slots, evaluate_lecturer_slots

router = APIRouter(prefix="/availability-unified", tags=["Unified Availability"])
logger = logging.getLogger(__name__)

# Who may create/delete institution blocks (excludes ucetni; includes staff roles).
BLOCK_EDIT_ROLES = BLOCK_MANAGE_ROLES | {"edukator", "lektor"}


class ExceptionCreate(BaseModel):
    scope_type: str  # 'program' or 'lecturer'
    scope_id: str
    date: str  # "2026-05-15"
    start_time: Optional[str] = None  # "09:00" or null for all-day
    end_time: Optional[str] = None
    reason: Optional[str] = None


# ============ Slot Evaluation ============

@router.get("/program/{program_id}/slots")
async def get_program_slots(
    program_id: str,
    date: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get evaluated slots for a program on a date.
    Each slot has: {time, status, reason}
    Status: available, booked, blocked_exception, blocked_lecturer,
            blocked_room, blocked_parallel, blocked_program, outside_base_availability
    """
    slots = await evaluate_program_slots(
        db, current_user["institution_id"], program_id, date
    )
    return {"program_id": program_id, "date": date, "slots": slots}


@router.get("/lecturer/{lecturer_id}/slots")
async def get_lecturer_slots(
    lecturer_id: str,
    date: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get evaluated slots for a lecturer on a date.
    Each slot has: {time, status, reason}
    """
    slots = await evaluate_lecturer_slots(
        db, current_user["institution_id"], lecturer_id, date
    )
    return {"lecturer_id": lecturer_id, "date": date, "slots": slots}


# ============ Exceptions CRUD ============

@router.get("/exceptions")
async def list_exceptions(
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List availability exceptions for the institution."""
    inst_uuid = uuid.UUID(current_user["institution_id"])
    query = select(AvailabilityException).where(
        AvailabilityException.institution_id == inst_uuid
    )
    if scope_type:
        query = query.where(AvailabilityException.scope_type == scope_type)
    if scope_id:
        query = query.where(AvailabilityException.scope_id == uuid.UUID(scope_id))
    if date:
        query = query.where(AvailabilityException.date == date)

    query = query.order_by(AvailabilityException.date, AvailabilityException.start_time)
    result = await db.execute(query)
    exceptions = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "scope_type": e.scope_type,
            "scope_id": str(e.scope_id),
            "date": e.date,
            "start_time": e.start_time,
            "end_time": e.end_time,
            "reason": e.reason,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in exceptions
    ]


@router.post("/exceptions")
async def create_exception(
    data: ExceptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a one-off availability exception (block a slot)."""
    ensure_role(current_user, BLOCK_EDIT_ROLES)
    if data.scope_type not in ('program', 'lecturer'):
        raise HTTPException(status_code=400, detail="scope_type musí být 'program' nebo 'lecturer'")

    inst_uuid = uuid.UUID(current_user["institution_id"])

    # Program blocks must reference a program that belongs to this tenant.
    if data.scope_type == 'program':
        prog_res = await db.execute(
            select(Program.id).where(
                and_(Program.id == uuid.UUID(data.scope_id), Program.institution_id == inst_uuid)
            )
        )
        if not prog_res.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Program nenalezen")

    exc = AvailabilityException(
        institution_id=inst_uuid,
        scope_type=data.scope_type,
        scope_id=uuid.UUID(data.scope_id),
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        reason=data.reason,
        created_by=uuid.UUID(current_user["user_id"]),
    )
    db.add(exc)
    await db.commit()
    await db.refresh(exc)

    return {
        "id": str(exc.id),
        "scope_type": exc.scope_type,
        "scope_id": str(exc.scope_id),
        "date": exc.date,
        "start_time": exc.start_time,
        "end_time": exc.end_time,
        "reason": exc.reason,
    }


@router.delete("/exceptions/{exception_id}")
async def delete_exception(
    exception_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete an availability exception (restore slot)."""
    ensure_role(current_user, BLOCK_EDIT_ROLES)
    inst_uuid = uuid.UUID(current_user["institution_id"])
    result = await db.execute(
        select(AvailabilityException).where(and_(
            AvailabilityException.id == uuid.UUID(exception_id),
            AvailabilityException.institution_id == inst_uuid,
        ))
    )
    exc = result.scalar_one_or_none()
    if not exc:
        raise HTTPException(status_code=404, detail="Výjimka nenalezena")

    # Save info before deletion for waitlist hook
    scope_type = exc.scope_type
    scope_id = str(exc.scope_id)
    exc_date = exc.date
    exc_time = exc.start_time or ''

    await db.delete(exc)
    await db.commit()

    # Waitlist Phase 2: if program exception removed, notify waitlist
    if scope_type == 'program':
        try:
            from services.waitlist_service import on_slot_freed
            await on_slot_freed(db, scope_id, exc_date, exc_time)
        except Exception as e:
            logger.warning(f"Waitlist on_slot_freed failed: {e}")

    return {"message": "Výjimka odstraněna"}
