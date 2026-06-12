"""Institution join-request workflow (Phase 83).

Endpoints:
* ``POST /api/institutions/check-duplicate``  — pre-flight check before signup
* ``POST /api/institutions/{id}/join-request`` — submit a request (public if
  not logged in; current user gets `user_id` filled in)
* ``GET  /api/institutions/{id}/join-requests`` — admin lists pending+history
* ``POST /api/institutions/{id}/join-requests/{req_id}/approve`` — approve + role
* ``POST /api/institutions/{id}/join-requests/{req_id}/reject`` — reject
* ``GET  /api/superadmin/join-requests`` — cross-institution view (superadmin)

The team-invite endpoint reused for adding existing users is unchanged (kept
from Phase 82). Approve reuses the same reactivate/reassign helper.
"""
from __future__ import annotations

import logging
import uuid
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user, get_current_user_optional, hash_password
from database.supabase import get_db
from database.models import Institution, InstitutionJoinRequest, User
from database.supabase_repositories import UserRepositorySupabase
from services.institution_duplicate_service import (
    find_duplicate_institutions, match_to_dict,
)
from services.email_service import EmailService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/institutions", tags=["Institution Join"])


VALID_ROLES = ["spravce", "edukator", "lektor", "pokladni", "admin", "staff", "viewer"]


# ── Schemas ─────────────────────────────────────────────────────────


class DuplicateCheckRequest(BaseModel):
    name: Optional[str] = None
    ico_dic: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None


class JoinRequestCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    message: Optional[str] = Field(None, max_length=500)


class JoinRequestApprove(BaseModel):
    assigned_role: str

    @validator("assigned_role")
    def _validate_role(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Neplatná role. Povolené: {', '.join(VALID_ROLES)}")
        return v


class JoinRequestReject(BaseModel):
    review_note: Optional[str] = Field(None, max_length=500)


# ── Helpers ─────────────────────────────────────────────────────────


def _is_superadmin(user: dict) -> bool:
    import os
    superadmins = {
        e.strip().lower() for e in
        os.environ.get("SUPERADMIN_EMAILS", "demo@budezivo.cz").split(",")
        if e.strip()
    }
    return (user.get("email") or "").lower() in superadmins


def _request_to_dict(req: InstitutionJoinRequest,
                      institution_name: Optional[str] = None) -> dict:
    return {
        "id": str(req.id),
        "institution_id": str(req.institution_id),
        "institution_name": institution_name,
        "user_id": str(req.user_id) if req.user_id else None,
        "email": req.email,
        "name": req.name,
        "message": req.message,
        "status": req.status,
        "assigned_role": req.assigned_role,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "reviewed_by": str(req.reviewed_by) if req.reviewed_by else None,
        "reviewed_at": req.reviewed_at.isoformat() if req.reviewed_at else None,
        "review_note": req.review_note,
    }


# ── Endpoints ───────────────────────────────────────────────────────


@router.post("/check-duplicate")
async def check_duplicate(
    payload: DuplicateCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """Pre-flight: is this institution already in the system?

    Public endpoint — used by the registration form to warn before submission.
    The same logic is enforced inside ``POST /auth/register`` so it can't be
    bypassed by skipping this call.
    """
    matches = await find_duplicate_institutions(
        db,
        name=payload.name,
        ico_dic=payload.ico_dic,
        city=payload.city,
        address=payload.address,
    )
    return {
        "duplicates": [match_to_dict(m) for m in matches],
        "has_strong_match": any(m.match_strength == "strong" for m in matches),
        "has_weak_match": any(m.match_strength == "weak" for m in matches),
    }


@router.post("/{institution_id}/join-request", status_code=201)
async def submit_join_request(
    institution_id: uuid.UUID,
    payload: JoinRequestCreate,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Submit a request to join an institution. Available to anonymous visitors
    AND to logged-in users (in which case ``user_id`` is auto-filled)."""
    # 1. Verify the institution exists
    inst = (await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )).scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Instituce nebyla nalezena")

    email = payload.email.strip().lower()

    # 2. If the e-mail is already a member of this institution → friendly msg
    existing_user = (await db.execute(
        select(User).where(User.email == email)
    )).scalar_one_or_none()
    if existing_user and str(existing_user.institution_id) == str(institution_id) and not existing_user.deleted_at:
        raise HTTPException(
            status_code=409,
            detail="Tento účet je již členem dané instituce.",
        )

    # 3. Reject duplicate pending requests
    dup = (await db.execute(
        select(InstitutionJoinRequest).where(and_(
            InstitutionJoinRequest.institution_id == institution_id,
            InstitutionJoinRequest.email == email,
            InstitutionJoinRequest.status == "pending",
        ))
    )).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status_code=409,
            detail="Žádost už byla odeslána a čeká na schválení administrátorem.",
        )

    # 4. Create the request
    req = InstitutionJoinRequest(
        institution_id=institution_id,
        user_id=uuid.UUID(current_user["user_id"]) if current_user else None,
        email=email,
        name=(payload.name or "").strip() or None,
        message=(payload.message or "").strip() or None,
        status="pending",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    # 5. Notify the institution admins
    try:
        admin_emails = await _admin_emails_for_institution(db, institution_id)
        for admin_email in admin_emails:
            await EmailService.send_transactional_email(
                template_name="join_request_received",
                to_email=admin_email,
                data={
                    "institution_name": inst.name,
                    "requester_name": req.name or req.email,
                    "requester_email": req.email,
                    "message": req.message or "",
                    "review_url": f"{_frontend_origin()}/admin/team#join-requests",
                },
            )
    except Exception as e:
        logger.warning(f"Failed to send join_request_received email: {e}")

    logger.info(
        f"New join request id={req.id} email={email} → inst={institution_id}"
    )
    return _request_to_dict(req, institution_name=inst.name)


@router.get("/{institution_id}/join-requests")
async def list_join_requests(
    institution_id: uuid.UUID,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List join requests for an institution. Admin of the inst OR superadmin only."""
    if str(current_user["institution_id"]) != str(institution_id) and not _is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění")
    if current_user.get("role") not in ("admin", "spravce") and not _is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Pouze administrátoři")

    conds = [InstitutionJoinRequest.institution_id == institution_id]
    if status:
        conds.append(InstitutionJoinRequest.status == status)

    q = await db.execute(
        select(InstitutionJoinRequest).where(and_(*conds))
        .order_by(InstitutionJoinRequest.created_at.desc())
    )
    rows = q.scalars().all()
    return [_request_to_dict(r) for r in rows]


@router.post("/{institution_id}/join-requests/{request_id}/approve")
async def approve_join_request(
    institution_id: uuid.UUID,
    request_id: uuid.UUID,
    payload: JoinRequestApprove,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a request: add user as a member with the chosen role."""
    if str(current_user["institution_id"]) != str(institution_id) and not _is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění")
    if current_user.get("role") not in ("admin", "spravce") and not _is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Pouze administrátoři")

    req = (await db.execute(
        select(InstitutionJoinRequest).where(and_(
            InstitutionJoinRequest.id == request_id,
            InstitutionJoinRequest.institution_id == institution_id,
        ))
    )).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Žádost nebyla nalezena")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Žádost už byla zpracována (stav: {req.status})")

    inst = (await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )).scalar_one()

    # Either reactivate/reassign existing user, OR create a fresh invite
    existing_user = (await db.execute(
        select(User).where(User.email == req.email)
    )).scalar_one_or_none()

    temp_password: Optional[str] = None
    if existing_user:
        # Reactivate + reassign (mirrors Phase 82 invite flow)
        await db.execute(
            update(User).where(User.id == existing_user.id).values(
                institution_id=institution_id,
                role=payload.assigned_role,
                status="active",
                deleted_at=None,
                updated_at=datetime.now(timezone.utc),
            )
        )
        mode = "reactivated"
    else:
        # Create a fresh account so the requester can log in immediately
        # Security audit P2: strong temporary password (was low-entropy uuid slice).
        temp_password = secrets.token_urlsafe(12)
        user_repo = UserRepositorySupabase(db)
        await user_repo.create({
            "name": req.name or req.email.split("@")[0],
            "email": req.email,
            "password_hash": hash_password(temp_password),
            "institution_id": str(institution_id),
            "role": payload.assigned_role,
            "status": "active",
        })
        mode = "created"

    req.status = "approved"
    req.assigned_role = payload.assigned_role
    req.reviewed_by = uuid.UUID(current_user["user_id"])
    req.reviewed_at = datetime.now(timezone.utc)
    await db.commit()

    # Notify the requester
    try:
        await EmailService.send_transactional_email(
            template_name="join_request_approved",
            to_email=req.email,
            data={
                "institution_name": inst.name,
                "assigned_role": payload.assigned_role,
                "temp_password": temp_password,   # only present for fresh creates
                "login_url": f"{_frontend_origin()}/login",
            },
        )
    except Exception as e:
        logger.warning(f"Failed to send join_request_approved email: {e}")

    logger.info(
        f"Join request {request_id} approved → mode={mode} role={payload.assigned_role}"
    )
    return {
        "message": "Žádost schválena, uživatel přidán do instituce",
        "mode": mode,
        "temp_password": temp_password,
        "request": _request_to_dict(req, institution_name=inst.name),
    }


@router.post("/{institution_id}/join-requests/{request_id}/reject")
async def reject_join_request(
    institution_id: uuid.UUID,
    request_id: uuid.UUID,
    payload: JoinRequestReject = Body(default_factory=JoinRequestReject),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a join request and (optionally) attach a note."""
    if str(current_user["institution_id"]) != str(institution_id) and not _is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění")
    if current_user.get("role") not in ("admin", "spravce") and not _is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Pouze administrátoři")

    req = (await db.execute(
        select(InstitutionJoinRequest).where(and_(
            InstitutionJoinRequest.id == request_id,
            InstitutionJoinRequest.institution_id == institution_id,
        ))
    )).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Žádost nebyla nalezena")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Žádost už byla zpracována (stav: {req.status})")

    inst = (await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )).scalar_one()

    req.status = "rejected"
    req.review_note = (payload.review_note or "").strip() or None
    req.reviewed_by = uuid.UUID(current_user["user_id"])
    req.reviewed_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        await EmailService.send_transactional_email(
            template_name="join_request_rejected",
            to_email=req.email,
            data={
                "institution_name": inst.name,
                "review_note": req.review_note or "",
            },
        )
    except Exception as e:
        logger.warning(f"Failed to send join_request_rejected email: {e}")

    return {
        "message": "Žádost byla zamítnuta",
        "request": _request_to_dict(req, institution_name=inst.name),
    }


# ── Internal utilities ──────────────────────────────────────────────


async def _admin_emails_for_institution(db: AsyncSession, institution_id: uuid.UUID) -> list[str]:
    q = await db.execute(
        select(User.email).where(and_(
            User.institution_id == institution_id,
            User.role.in_(["admin", "spravce"]),
            User.deleted_at.is_(None),
        ))
    )
    return [row[0] for row in q.fetchall() if row[0]]


def _frontend_origin() -> str:
    import os
    return os.environ.get("FRONTEND_URL", "https://budezivo.cz").rstrip("/")
