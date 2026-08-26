"""
Unified Availability API endpoints.
Provides program/lecturer slot evaluation and exception management.
"""
import uuid
import logging
from datetime import date as date_class, datetime, timedelta
from typing import List, Optional
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
    scope_id: Optional[str] = None
    date: Optional[str] = None  # "2026-05-15"
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    program_ids: Optional[List[str]] = None
    repeat_weekdays: Optional[List[int]] = None  # 0 = Monday, 6 = Sunday
    start_time: Optional[str] = None  # "09:00" or null for all-day
    end_time: Optional[str] = None
    reason: Optional[str] = None


def _parse_date(value: Optional[str], field_name: str) -> date_class:
    if not value:
        raise HTTPException(status_code=400, detail=f"{field_name} je povinné")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field_name} musí být ve formátu RRRR-MM-DD")


def _iter_dates(date_from: date_class, date_to: date_class) -> List[str]:
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="Datum do nesmí být před datem od")
    days = (date_to - date_from).days + 1
    if days > 366:
        raise HTTPException(status_code=400, detail="Blokaci lze vytvořit maximálně na 366 dní")
    return [(date_from + timedelta(days=i)).isoformat() for i in range(days)]


def _filter_dates_by_weekdays(dates: List[str], weekdays: Optional[List[int]]) -> List[str]:
    if weekdays is None:
        return dates
    unique_weekdays = set(weekdays)
    if not unique_weekdays or any(day < 0 or day > 6 for day in unique_weekdays):
        raise HTTPException(status_code=400, detail="Vyberte platné dny opakování")
    filtered = [
        value
        for value in dates
        if datetime.strptime(value, "%Y-%m-%d").date().weekday() in unique_weekdays
    ]
    if not filtered:
        raise HTTPException(status_code=400, detail="Ve zvoleném období není žádný vybraný den opakování")
    return filtered


def _validate_time_range(start_time: Optional[str], end_time: Optional[str]) -> None:
    if bool(start_time) != bool(end_time):
        raise HTTPException(status_code=400, detail="Zadejte začátek i konec, nebo nechte obojí prázdné")
    if not start_time or not end_time:
        return
    try:
        start = datetime.strptime(start_time, "%H:%M").time()
        end = datetime.strptime(end_time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Čas musí být ve formátu HH:MM")
    if end <= start:
        raise HTTPException(status_code=400, detail="Čas do musí být později než čas od")


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
    _validate_time_range(data.start_time, data.end_time)

    inst_uuid = uuid.UUID(current_user["institution_id"])
    date_from = _parse_date(data.date_from or data.date, "Datum od")
    date_to = _parse_date(data.date_to or data.date_from or data.date, "Datum do")
    dates = _filter_dates_by_weekdays(_iter_dates(date_from, date_to), data.repeat_weekdays)

    scope_ids = data.program_ids if data.scope_type == 'program' and data.program_ids else None
    if scope_ids is None:
        if not data.scope_id:
            raise HTTPException(status_code=400, detail="Vyberte program")
        scope_ids = [data.scope_id]

    scope_ids = list(dict.fromkeys(scope_ids))
    try:
        scope_uuids = [uuid.UUID(scope_id) for scope_id in scope_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Neplatné ID programu")

    # Program blocks must reference a program that belongs to this tenant.
    if data.scope_type == 'program':
        prog_res = await db.execute(
            select(Program.id).where(
                and_(Program.id.in_(scope_uuids), Program.institution_id == inst_uuid)
            )
        )
        found_programs = {program_id for program_id in prog_res.scalars().all()}
        if found_programs != set(scope_uuids):
            raise HTTPException(status_code=404, detail="Program nenalezen")

    exceptions = []
    for scope_uuid in scope_uuids:
        for exception_date in dates:
            exc = AvailabilityException(
                institution_id=inst_uuid,
                scope_type=data.scope_type,
                scope_id=scope_uuid,
                date=exception_date,
                start_time=data.start_time,
                end_time=data.end_time,
                reason=data.reason,
                created_by=uuid.UUID(current_user["user_id"]),
            )
            db.add(exc)
            exceptions.append(exc)
    await db.commit()
    for exc in exceptions:
        await db.refresh(exc)

    created = [
        {
            "id": str(exc.id),
            "scope_type": exc.scope_type,
            "scope_id": str(exc.scope_id),
            "date": exc.date,
            "start_time": exc.start_time,
            "end_time": exc.end_time,
            "reason": exc.reason,
        }
        for exc in exceptions
    ]
    if len(created) == 1:
        return created[0]
    return {"count": len(created), "exceptions": created}


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
