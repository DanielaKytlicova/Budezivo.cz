"""Náslech — lecturer joins a reservation as observer (non-blocking, no collisions)."""
import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from core.security import get_current_user
from database.supabase import get_db
from database.models import ReservationObserver, Reservation, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bookings", tags=["Náslech"])


def _observer_dict(obs: ReservationObserver, lecturer_name: str | None = None) -> dict:
    return {
        "id": str(obs.id),
        "reservation_id": str(obs.reservation_id),
        "lecturer_id": str(obs.lecturer_id),
        "lecturer_name": lecturer_name,
        "role": obs.role,
        "status": obs.status,
        "note": obs.note,
        "created_at": obs.created_at.isoformat() if obs.created_at else None,
        "approved_at": obs.approved_at.isoformat() if obs.approved_at else None,
    }


@router.get("/{booking_id}/naslech")
async def list_observers(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all observers (náslech) attached to a reservation."""
    inst = current_user["institution_id"]
    rows = await db.execute(
        select(ReservationObserver, User.name)
        .join(User, User.id == ReservationObserver.lecturer_id)
        .where(and_(
            ReservationObserver.reservation_id == uuid.UUID(booking_id),
            ReservationObserver.institution_id == uuid.UUID(inst),
        ))
        .order_by(ReservationObserver.created_at)
    )
    return [_observer_dict(obs, name) for obs, name in rows.all()]


@router.post("/{booking_id}/naslech")
async def add_observer(
    booking_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a lecturer as observer. Admin adds with status='approved'; a lecturer
    requesting for themselves gets status='pending'."""
    lecturer_id = payload.get("lecturer_id") or current_user["user_id"]
    note = payload.get("note")

    # Verify reservation exists in the same institution
    res = await db.execute(select(Reservation).where(and_(
        Reservation.id == uuid.UUID(booking_id),
        Reservation.institution_id == uuid.UUID(current_user["institution_id"]),
    )))
    booking = res.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Rezervace nenalezena")

    # Verify lecturer belongs to institution
    lect = (await db.execute(select(User).where(and_(
        User.id == uuid.UUID(lecturer_id),
        User.institution_id == uuid.UUID(current_user["institution_id"]),
    )))).scalar_one_or_none()
    if not lect:
        raise HTTPException(status_code=404, detail="Lektor nenalezen")

    # Prevent duplicate
    existing = (await db.execute(select(ReservationObserver).where(and_(
        ReservationObserver.reservation_id == booking.id,
        ReservationObserver.lecturer_id == lect.id,
    )))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Tento lektor je již přidán na náslech")

    is_admin = current_user.get("role") in ("admin", "spravce")
    status = "approved" if is_admin else "pending"

    obs = ReservationObserver(
        id=uuid.uuid4(),
        reservation_id=booking.id,
        lecturer_id=lect.id,
        institution_id=uuid.UUID(current_user["institution_id"]),
        role="naslech",
        status=status,
        requested_by=uuid.UUID(current_user["user_id"]),
        approved_by=uuid.UUID(current_user["user_id"]) if is_admin else None,
        approved_at=datetime.now(timezone.utc) if is_admin else None,
        note=note,
    )
    db.add(obs)
    await db.commit()
    return _observer_dict(obs, lect.name)


@router.patch("/{booking_id}/naslech/{observer_id}/approve")
async def approve_observer(
    booking_id: str,
    observer_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin approves a pending náslech request."""
    if current_user.get("role") not in ("admin", "spravce"):
        raise HTTPException(status_code=403, detail="Pouze admin může schvalovat náslech")

    obs = (await db.execute(select(ReservationObserver).where(and_(
        ReservationObserver.id == uuid.UUID(observer_id),
        ReservationObserver.reservation_id == uuid.UUID(booking_id),
        ReservationObserver.institution_id == uuid.UUID(current_user["institution_id"]),
    )))).scalar_one_or_none()
    if not obs:
        raise HTTPException(status_code=404, detail="Náslech nenalezen")

    obs.status = "approved"
    obs.approved_by = uuid.UUID(current_user["user_id"])
    obs.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return _observer_dict(obs)


@router.delete("/{booking_id}/naslech/{observer_id}")
async def remove_observer(
    booking_id: str,
    observer_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a náslech entry. Admin or the lecturer themselves can delete."""
    obs = (await db.execute(select(ReservationObserver).where(and_(
        ReservationObserver.id == uuid.UUID(observer_id),
        ReservationObserver.reservation_id == uuid.UUID(booking_id),
        ReservationObserver.institution_id == uuid.UUID(current_user["institution_id"]),
    )))).scalar_one_or_none()
    if not obs:
        raise HTTPException(status_code=404, detail="Náslech nenalezen")

    is_admin = current_user.get("role") in ("admin", "spravce")
    if str(obs.lecturer_id) != current_user["user_id"] and not is_admin:
        raise HTTPException(status_code=403, detail="Nemůžete odebrat cizí náslech")

    await db.delete(obs)
    await db.commit()
    return {"message": "Náslech odebrán"}


@router.get("/me/naslech-upcoming")
async def my_upcoming_observers(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upcoming náslech entries for the logged-in lecturer."""
    today = datetime.now(timezone.utc).date().isoformat()
    rows = await db.execute(
        select(ReservationObserver, Reservation)
        .join(Reservation, Reservation.id == ReservationObserver.reservation_id)
        .where(and_(
            ReservationObserver.lecturer_id == uuid.UUID(current_user["user_id"]),
            ReservationObserver.institution_id == uuid.UUID(current_user["institution_id"]),
            Reservation.date >= today,
            Reservation.status != "cancelled",
        ))
        .order_by(Reservation.date, Reservation.time_block)
    )
    out = []
    for obs, res in rows.all():
        out.append({
            **_observer_dict(obs),
            "date": res.date,
            "time_block": res.time_block,
            "school_name": res.school_name,
            "program_id": str(res.program_id),
        })
    return out
