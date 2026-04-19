"""
Room management routes.
CRUD for institution rooms used in collision checking.
"""
import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel

from core.security import get_current_user
from database.supabase import get_db
from database.models import Room
from routes.audit import log_action
from services.plan_service import require_feature

router = APIRouter(prefix="/rooms", tags=["Rooms"], dependencies=[Depends(require_feature("collision_system"))])
logger = logging.getLogger(__name__)


def _to_dict(room) -> dict:
    return {
        "id": str(room.id),
        "institution_id": str(room.institution_id),
        "name": room.name,
        "capacity": room.capacity,
        "equipment": room.equipment,
        "is_active": room.is_active,
        "created_at": room.created_at.isoformat() if room.created_at else None,
    }


class RoomCreate(BaseModel):
    name: str
    capacity: Optional[int] = None
    equipment: Optional[str] = None


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = None
    equipment: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_rooms(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all rooms for the institution."""
    inst_id = uuid.UUID(current_user["institution_id"])
    result = await db.execute(
        select(Room)
        .where(Room.institution_id == inst_id)
        .order_by(Room.name)
    )
    rooms = result.scalars().all()
    return [_to_dict(r) for r in rooms]


@router.post("")
async def create_room(
    data: RoomCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new room."""
    inst_id = uuid.UUID(current_user["institution_id"])
    room = Room(
        institution_id=inst_id,
        name=data.name,
        capacity=data.capacity,
        equipment=data.equipment,
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    
    await log_action(db, institution_id=current_user["institution_id"], user_id=current_user["user_id"], user_email=current_user.get("email",""), action="create", entity_type="room", entity_id=str(room.id), details={"name": data.name})
    
    return _to_dict(room)


@router.patch("/{room_id}")
async def update_room(
    room_id: str,
    data: RoomUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a room."""
    inst_id = uuid.UUID(current_user["institution_id"])
    result = await db.execute(
        select(Room).where(and_(Room.id == uuid.UUID(room_id), Room.institution_id == inst_id))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Místnost nenalezena")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(room, key, value)
    
    await db.commit()
    await db.refresh(room)
    
    await log_action(db, institution_id=current_user["institution_id"], user_id=current_user["user_id"], user_email=current_user.get("email",""), action="update", entity_type="room", entity_id=room_id, details=update_data)
    
    return _to_dict(room)


@router.delete("/{room_id}")
async def delete_room(
    room_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a room."""
    inst_id = uuid.UUID(current_user["institution_id"])
    result = await db.execute(
        select(Room).where(and_(Room.id == uuid.UUID(room_id), Room.institution_id == inst_id))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Místnost nenalezena")
    
    room_name = room.name
    await db.delete(room)
    await db.commit()
    
    await log_action(db, institution_id=current_user["institution_id"], user_id=current_user["user_id"], user_email=current_user.get("email",""), action="delete", entity_type="room", entity_id=room_id, details={"name": room_name})
    
    return {"message": f"Místnost '{room_name}' smazána"}
