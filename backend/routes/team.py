"""
Team management routes.
Uses Supabase (PostgreSQL) for database operations.
"""
import uuid
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import TeamMember, TeamInvite, RoleUpdate
from core.security import hash_password, get_current_user
from database.supabase import get_db
from database.supabase_repositories import UserRepositorySupabase

router = APIRouter(prefix="/team", tags=["Team"])
logger = logging.getLogger(__name__)

VALID_ROLES = ["spravce", "edukator", "lektor", "pokladni", "admin", "staff", "viewer"]


@router.get("", response_model=List[TeamMember])
async def get_team_members(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all team members for the institution."""
    user_repo = UserRepositorySupabase(db)
    return await user_repo.find_by_institution(current_user["institution_id"])


@router.post("/invite")
async def invite_team_member(
    invite_data: TeamInvite,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Invite a new team member (admin only)."""
    user_repo = UserRepositorySupabase(db)
    
    # Check if current user is admin
    user = await user_repo.find_by_id(current_user["user_id"])
    if user.get("role") not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Only admins can invite team members")
    
    # Check if email already exists
    existing = await user_repo.find_by_email(invite_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Validate role
    if invite_data.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Create user with temporary password
    temp_password = str(uuid.uuid4())[:8]
    
    await user_repo.create({
        "name": invite_data.name,
        "email": invite_data.email,
        "password_hash": hash_password(temp_password),
        "institution_id": current_user["institution_id"],
        "role": invite_data.role,
        "status": "active",
        "lecturer_mode": invite_data.lecturer_mode or "main",
        "invited_by": current_user["user_id"],
    })
    
    logger.info(f"Team member invited: {invite_data.email} with role {invite_data.role}")
    return {"message": "Invitation sent", "temp_password": temp_password}


@router.patch("/{member_id}/role")
async def update_member_role(
    member_id: str,
    role_data: RoleUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a team member's role (admin only)."""
    user_repo = UserRepositorySupabase(db)
    
    # Check if current user is admin
    user = await user_repo.find_by_id(current_user["user_id"])
    if user.get("role") not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Only admins can change roles")
    
    # Can't change own role
    if member_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    # Validate role
    if role_data.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    result = await user_repo.update_role(
        member_id,
        current_user["institution_id"],
        role_data.role
    )
    
    if result == 0:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    return {"message": "Role updated"}


class LecturerModeUpdate(RoleUpdate):
    mode: str  # "main" | "training"


@router.patch("/{member_id}/lecturer-mode")
async def update_lecturer_mode(
    member_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle lecturer mode (main ↔ training/náslech). Admin only."""
    user_repo = UserRepositorySupabase(db)
    user = await user_repo.find_by_id(current_user["user_id"])
    if user.get("role") not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Pouze admin může měnit režim lektora")

    mode = payload.get("lecturer_mode")
    if mode not in ("main", "training"):
        raise HTTPException(status_code=400, detail="lecturer_mode musí být 'main' nebo 'training'")

    result = await user_repo.update_lecturer_mode(
        member_id, current_user["institution_id"], mode,
    )
    if result == 0:
        raise HTTPException(status_code=404, detail="Člen týmu nenalezen")
    return {"message": "Režim lektora aktualizován", "lecturer_mode": mode}


@router.delete("/{member_id}")
async def remove_team_member(
    member_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a team member (admin only)."""
    user_repo = UserRepositorySupabase(db)
    
    # Check if current user is admin
    user = await user_repo.find_by_id(current_user["user_id"])
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can remove team members")
    
    # Can't remove self
    if member_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    
    result = await user_repo.delete_by_id(member_id, current_user["institution_id"])
    
    if result == 0:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    return {"message": "Team member removed"}


from pydantic import BaseModel

class NameUpdate(BaseModel):
    name: str


@router.patch("/{member_id}/name")
async def update_member_name(
    member_id: str,
    name_data: NameUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a team member's name (admin or self)."""
    user_repo = UserRepositorySupabase(db)
    
    # Check if current user is admin or updating self
    user = await user_repo.find_by_id(current_user["user_id"])
    is_admin = user.get("role") in ["admin", "spravce"]
    is_self = member_id == current_user["user_id"]
    
    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění měnit jméno tohoto uživatele")
    
    result = await user_repo.update_name(
        member_id,
        current_user["institution_id"],
        name_data.name
    )
    
    if result == 0:
        raise HTTPException(status_code=404, detail="Člen týmu nenalezen")
    
    return {"message": "Jméno aktualizováno"}
