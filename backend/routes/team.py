"""
Team management routes.
Uses Supabase (PostgreSQL) for database operations.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import TeamMember, TeamInvite, RoleUpdate
from core.security import hash_password, get_current_user
from database.supabase import get_db
from database.supabase_repositories import UserRepositorySupabase
from database.models import User

# Mirror the same source of truth used by routes/superadmin.py — kept inline
# to avoid a cross-import cycle.
import os
SUPERADMIN_EMAILS = {
    e.strip().lower() for e in
    os.environ.get("SUPERADMIN_EMAILS", "demo@budezivo.cz").split(",")
    if e.strip()
}


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
    """Invite a team member.

    Behaviour:
    * **New e-mail**     → create a fresh user with a temporary password.
    * **Existing user, soft-deleted** → reactivate and reassign to the inviting
      admin's institution while preserving name & password (so the user keeps
      their original login).
    * **Existing user in the SAME institution** → return an idempotent friendly
      message; never raise "user already exists".
    * **Existing user in ANOTHER institution** → blocked for regular admins
      with a clear instruction to contact superadmin; superadmins may force-move.
    """
    user_repo = UserRepositorySupabase(db)
    inviting_user = await user_repo.find_by_id(current_user["user_id"])
    if inviting_user.get("role") not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Pouze administrátoři mohou zvát členy týmu")

    if invite_data.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Neplatná role")

    is_superadmin = (current_user.get("email") or "").lower() in SUPERADMIN_EMAILS
    target_inst = current_user["institution_id"]
    target_inst_uuid = uuid.UUID(target_inst)
    email = (invite_data.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="E-mail je povinný")

    existing = await user_repo.find_by_email(email)

    # ── Case A: brand-new user — classic invite ──
    if not existing:
        temp_password = str(uuid.uuid4())[:8]
        await user_repo.create({
            "name": invite_data.name,
            "email": email,
            "password_hash": hash_password(temp_password),
            "institution_id": target_inst,
            "role": invite_data.role,
            "status": "active",
            "lecturer_mode": invite_data.lecturer_mode or "main",
            "invited_by": current_user["user_id"],
        })
        logger.info(f"Team member invited: {email} role={invite_data.role}")
        return {
            "message": "Pozvánka vytvořena",
            "temp_password": temp_password,
            "mode": "created",
        }

    # ── Case B: existing user, already in this institution ──
    existing_inst = str(existing.get("institution_id") or "")
    soft_deleted = bool(existing.get("deleted_at"))

    if existing_inst == target_inst and not soft_deleted:
        return {
            "message": (
                f"Uživatel {email} je již členem této instituce — pozvánka je tedy "
                f"zbytečná. Pokud potřebujete změnit jeho roli, použijte tlačítko "
                f"„Změnit roli\u201c v seznamu členů."
            ),
            "mode": "noop_already_member",
        }

    # ── Case C: existing user is soft-deleted (own institution or any other) ──
    # Reactivate and reassign to the inviting admin's institution. Preserve
    # password_hash and name so the user keeps their original login.
    if soft_deleted:
        await db.execute(
            update(User)
            .where(User.id == uuid.UUID(existing["id"]))
            .values(
                institution_id=target_inst_uuid,
                role=invite_data.role,
                status="active",
                deleted_at=None,
                lecturer_mode=invite_data.lecturer_mode or "main",
                invited_by=uuid.UUID(current_user["user_id"]),
                updated_at=datetime.now(timezone.utc),
                # name kept; password_hash kept
            )
        )
        await db.commit()
        logger.info(
            f"Team invite reactivated soft-deleted user {email} → inst {target_inst}"
        )
        return {
            "message": (
                f"Uživatel {email} byl reaktivován a přiřazen k vaší instituci. "
                f"Jeho původní jméno a heslo zůstávají zachovány — může se přihlásit "
                f"stejně jako dříve."
            ),
            "mode": "reactivated",
        }

    # ── Case D: existing user is active in a DIFFERENT institution ──
    if not is_superadmin:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Uživatel s e-mailem {email} je již členem jiné instituce. "
                f"Pro přesun mezi institucemi kontaktujte správce platformy."
            ),
        )

    # Superadmin force-move: relocate the user to the target institution.
    await db.execute(
        update(User)
        .where(User.id == uuid.UUID(existing["id"]))
        .values(
            institution_id=target_inst_uuid,
            role=invite_data.role,
            status="active",
            deleted_at=None,
            invited_by=uuid.UUID(current_user["user_id"]),
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    logger.info(
        f"Superadmin force-moved {email}: {existing_inst} → {target_inst}"
    )
    return {
        "message": (
            f"Uživatel {email} byl jako superadmin přesunut z předchozí instituce do vaší. "
            f"Jeho přihlašovací údaje zůstávají zachovány."
        ),
        "mode": "moved_by_superadmin",
    }


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
    mode: str  # deprecated, kept for schema back-compat


@router.patch("/{member_id}/lecturer-profile")
async def update_lecturer_profile(
    member_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update extended lecturer profile fields.
    Lecturers may edit their own profile; admins may edit anyone's (including admin_note)."""
    user_repo = UserRepositorySupabase(db)
    me = await user_repo.find_by_id(current_user["user_id"])
    is_admin = me.get("role") in ("admin", "spravce")

    if member_id != current_user["user_id"] and not is_admin:
        raise HTTPException(status_code=403, detail="Můžete upravovat pouze svůj profil")

    allowed = {"preferred_age_groups", "supported_program_ids",
               "learning_program_ids", "name"}
    if is_admin:
        allowed.add("admin_note")
    patch = {k: v for k, v in payload.items() if k in allowed and v is not None}
    if not patch:
        raise HTTPException(status_code=400, detail="Žádná platná pole k uložení")

    result = await user_repo.update_profile(
        member_id, current_user["institution_id"], patch,
    )
    if result == 0:
        raise HTTPException(status_code=404, detail="Člen týmu nenalezen")
    return {"message": "Profil lektora aktualizován", "updated": list(patch.keys())}


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
