"""
Teacher account routes — B2C self-registration for external teachers / parents.

Architecture
------------
* Completely independent of `users` (institution staff) — separate model
  `TeacherAccount`, separate JWT cookie name (`teacher_token`), separate
  dependency `get_current_teacher`.
* Token payload includes `account_type="teacher"` so an admin endpoint that
  uses `get_current_user` will not silently accept a teacher token (it has no
  `user_id`/`institution_id` fields → admin code paths fail naturally).
* Architecture is ready for Google OAuth: the `auth_provider` and `google_sub`
  columns are pre-allocated; only a new endpoint will need to be added later.

Endpoints
---------
POST   /api/teacher/auth/register   — create account, set cookie, return profile
POST   /api/teacher/auth/login      — verify password, set cookie
POST   /api/teacher/auth/logout     — clear cookie
GET    /api/teacher/auth/me         — return profile (auth required)
PATCH  /api/teacher/me              — update name/school_name/phone
GET    /api/teacher/favorites       — list favourite programs (with program data)
POST   /api/teacher/favorites       — add favourite (idempotent)
DELETE /api/teacher/favorites/{program_id} — remove favourite
GET    /api/teacher/bookings        — list reservations matching teacher email
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

import bcrypt
import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select, and_, or_, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import JWT_SECRET, JWT_ALGORITHM
from database.supabase import get_db
from database.models import (
    TeacherAccount, TeacherFavorite, TeacherLoginAttempt,
    Program, Reservation, Institution,
)


router = APIRouter(prefix="/teacher", tags=["Teacher"])
logger = logging.getLogger(__name__)

# ----- Cookies / token config (independent of admin auth) ---------------------
TEACHER_COOKIE_NAME = "teacher_token"
ACCESS_TOKEN_TTL_MIN = 60 * 24 * 14  # 14 days — teachers are casual users, log in less often
LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15

_security = HTTPBearer(auto_error=False)


# ----- Schemas ----------------------------------------------------------------

class TeacherRegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=2, max_length=120)
    school_name: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v):
        return v.strip().lower()


class TeacherLoginIn(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v):
        return v.strip().lower()


class TeacherProfileUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    school_name: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=40)


class FavoriteIn(BaseModel):
    program_id: str


# ----- Helpers ----------------------------------------------------------------

def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(pw: str, hashed: str) -> bool:
    if not hashed:
        return False
    return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))


def _create_teacher_token(teacher_id: str, email: str) -> str:
    payload = {
        "teacher_id": teacher_id,
        "email": email,
        "account_type": "teacher",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_TTL_MIN),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _set_teacher_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=TEACHER_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_TTL_MIN * 60,
        path="/",
    )


def _extract_teacher_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> str:
    cookie = request.cookies.get(TEACHER_COOKIE_NAME)
    if cookie:
        return cookie
    if credentials and credentials.credentials:
        return credentials.credentials
    raise HTTPException(status_code=401, detail="Přihlášení vyžadováno")


async def get_current_teacher(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
    db: AsyncSession = Depends(get_db),
) -> TeacherAccount:
    token = _extract_teacher_token(request, credentials)
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Platnost přihlášení vypršela")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Neplatný token")

    if payload.get("account_type") != "teacher":
        raise HTTPException(status_code=401, detail="Tento token nepatří učitelskému účtu")
    teacher_id = payload.get("teacher_id")
    if not teacher_id:
        raise HTTPException(status_code=401, detail="Neplatný token")
    res = await db.execute(select(TeacherAccount).where(TeacherAccount.id == uuid.UUID(teacher_id)))
    teacher = res.scalar_one_or_none()
    if not teacher or not teacher.is_active or teacher.deleted_at is not None:
        raise HTTPException(status_code=401, detail="Účet nenalezen nebo deaktivován")
    return teacher


def _profile_dict(t: TeacherAccount) -> dict:
    return {
        "id": str(t.id),
        "email": t.email,
        "name": t.name,
        "school_name": t.school_name,
        "phone": t.phone,
        "auth_provider": t.auth_provider,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "last_login_at": t.last_login_at.isoformat() if t.last_login_at else None,
    }


# ----- Brute force tracking ---------------------------------------------------

async def _is_locked(db: AsyncSession, identifier: str) -> bool:
    res = await db.execute(select(TeacherLoginAttempt).where(TeacherLoginAttempt.identifier == identifier))
    row = res.scalar_one_or_none()
    if not row or not row.locked_until:
        return False
    return row.locked_until > datetime.now(timezone.utc)


async def _record_failed_attempt(db: AsyncSession, identifier: str) -> None:
    res = await db.execute(select(TeacherLoginAttempt).where(TeacherLoginAttempt.identifier == identifier))
    row = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None:
        row = TeacherLoginAttempt(identifier=identifier, failed_count=1, last_failed_at=now)
        db.add(row)
    else:
        row.failed_count = (row.failed_count or 0) + 1
        row.last_failed_at = now
        if row.failed_count >= LOCKOUT_THRESHOLD:
            row.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
    await db.commit()


async def _reset_attempts(db: AsyncSession, identifier: str) -> None:
    await db.execute(sa_delete(TeacherLoginAttempt).where(TeacherLoginAttempt.identifier == identifier))
    await db.commit()


# ----- Auth endpoints ---------------------------------------------------------

def _client_ip(request: Request) -> str:
    """Best-effort client IP detection — works behind Kubernetes ingress / load balancer.

    Falls back to ``request.client.host`` when the proxy header is missing.
    """
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


@router.post("/auth/register")
async def teacher_register(
    data: TeacherRegisterIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(TeacherAccount).where(TeacherAccount.email == data.email))
    if res.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Účet s tímto e-mailem již existuje")

    teacher = TeacherAccount(
        email=data.email,
        password_hash=_hash_password(data.password),
        name=data.name.strip(),
        school_name=(data.school_name or "").strip() or None,
        phone=(data.phone or "").strip() or None,
        auth_provider="password",
    )
    db.add(teacher)
    await db.commit()
    await db.refresh(teacher)

    token = _create_teacher_token(str(teacher.id), teacher.email)
    _set_teacher_cookie(response, token)
    profile = _profile_dict(teacher)
    profile["access_token"] = token  # also expose for non-cookie clients
    return profile


@router.post("/auth/login")
async def teacher_login(
    data: TeacherLoginIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Lockout key — primarily by email so a single attacker who rotates IPs
    # is still blocked. We also keep an IP-only secondary key for safety.
    email_key = f"email:{data.email}"
    ip = _client_ip(request)
    ip_key = f"ip:{ip}"

    if await _is_locked(db, email_key) or await _is_locked(db, ip_key):
        raise HTTPException(status_code=429, detail="Příliš mnoho neúspěšných pokusů. Zkuste to prosím za 15 minut.")

    res = await db.execute(select(TeacherAccount).where(TeacherAccount.email == data.email))
    teacher = res.scalar_one_or_none()
    valid = teacher is not None and teacher.is_active and teacher.deleted_at is None and _verify_password(data.password, teacher.password_hash or "")
    if not valid:
        await _record_failed_attempt(db, email_key)
        await _record_failed_attempt(db, ip_key)
        raise HTTPException(status_code=401, detail="Nesprávný e-mail nebo heslo")

    teacher.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await _reset_attempts(db, email_key)
    await _reset_attempts(db, ip_key)

    token = _create_teacher_token(str(teacher.id), teacher.email)
    _set_teacher_cookie(response, token)
    profile = _profile_dict(teacher)
    profile["access_token"] = token
    return profile


@router.post("/auth/logout")
async def teacher_logout(response: Response):
    response.delete_cookie(key=TEACHER_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/auth/me")
async def teacher_me(teacher: TeacherAccount = Depends(get_current_teacher)):
    return _profile_dict(teacher)


@router.patch("/me")
async def teacher_update_profile(
    data: TeacherProfileUpdateIn,
    teacher: TeacherAccount = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(teacher, k, (v or "").strip() or None if isinstance(v, str) else v)
    teacher.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(teacher)
    return _profile_dict(teacher)


# ----- Favorites --------------------------------------------------------------

@router.get("/favorites")
async def list_favorites(
    teacher: TeacherAccount = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """List teacher favorites with embedded program details (only programs still published)."""
    q = (
        select(TeacherFavorite, Program, Institution)
        .join(Program, TeacherFavorite.program_id == Program.id)
        .join(Institution, TeacherFavorite.institution_id == Institution.id)
        .where(TeacherFavorite.teacher_id == teacher.id)
        .order_by(TeacherFavorite.created_at.desc())
    )
    res = await db.execute(q)
    out: List[dict] = []
    for fav, program, institution in res.all():
        if program.deleted_at is not None or program.status == 'archived':
            continue
        out.append({
            "favorite_id": str(fav.id),
            "favorited_at": fav.created_at.isoformat() if fav.created_at else None,
            "program_id": str(program.id),
            "name": program.name_cs,
            "description": program.description_cs[:300] if program.description_cs else None,
            "duration": program.duration,
            "age_group": program.age_group,
            "target_groups": program.target_groups,
            "price": program.price,
            "pricing_info": program.pricing_info,
            "image_url": program.image_url,
            "institution_id": str(institution.id),
            "institution_name": institution.name,
            "institution_city": institution.city,
        })
    return out


@router.post("/favorites")
async def add_favorite(
    data: FavoriteIn,
    teacher: TeacherAccount = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    try:
        program_uuid = uuid.UUID(data.program_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Neplatné program_id")

    res = await db.execute(select(Program).where(Program.id == program_uuid))
    program = res.scalar_one_or_none()
    if not program or program.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Program nenalezen")

    # idempotent — return existing if present
    existing = await db.execute(
        select(TeacherFavorite).where(and_(
            TeacherFavorite.teacher_id == teacher.id,
            TeacherFavorite.program_id == program_uuid,
        ))
    )
    if existing.scalar_one_or_none() is not None:
        return {"ok": True, "already": True}

    fav = TeacherFavorite(
        teacher_id=teacher.id,
        program_id=program_uuid,
        institution_id=program.institution_id,
    )
    db.add(fav)
    await db.commit()
    return {"ok": True, "already": False, "favorite_id": str(fav.id)}


@router.delete("/favorites/{program_id}")
async def remove_favorite(
    program_id: str,
    teacher: TeacherAccount = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    try:
        program_uuid = uuid.UUID(program_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Neplatné program_id")

    await db.execute(sa_delete(TeacherFavorite).where(and_(
        TeacherFavorite.teacher_id == teacher.id,
        TeacherFavorite.program_id == program_uuid,
    )))
    await db.commit()
    return {"ok": True}


# ----- Booking history --------------------------------------------------------

@router.get("/bookings")
async def list_bookings(
    teacher: TeacherAccount = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """All reservations whose contact_email matches the teacher's email — newest first."""
    q = (
        select(Reservation, Program, Institution)
        .join(Program, Reservation.program_id == Program.id)
        .join(Institution, Reservation.institution_id == Institution.id)
        .where(Reservation.contact_email == teacher.email)
        .order_by(Reservation.date.desc(), Reservation.time_block.desc())
    )
    res = await db.execute(q)
    out: List[dict] = []
    for r, program, institution in res.all():
        out.append({
            "id": str(r.id),
            "date": r.date,
            "time_block": r.time_block,
            "status": r.status,
            "program_id": str(program.id),
            "program_name": program.name_cs,
            "program_image_url": program.image_url,
            "institution_id": str(institution.id),
            "institution_name": institution.name,
            "school_name": r.school_name,
            "num_students": r.num_students,
            "num_teachers": r.num_teachers,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return out
