"""
Authentication routes: register, login, refresh, logout, verify, forgot password.
Uses Supabase (PostgreSQL) for database operations.
"""
import logging
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from slowapi import Limiter
from slowapi.util import get_remote_address

from models.schemas import UserCreate, UserLogin, TokenResponse, ForgotPasswordRequest
from pydantic import BaseModel, EmailStr
from core.security import (
    hash_password, verify_password, create_jwt_token, get_current_user,
    generate_refresh_token, hash_refresh_token,
    REFRESH_TOKEN_EXPIRE_DAYS, ACCESS_TOKEN_EXPIRE_MINUTES,
    COOKIE_NAME, REFRESH_COOKIE_NAME,
)
from core.config import FRONTEND_URL, JWT_SECRET
from database.supabase import get_db
from database.models import RefreshToken, User
from database.supabase_repositories import (
    UserRepositorySupabase,
    InstitutionRepositorySupabase,
    ThemeRepositorySupabase,
)
from services.email_service import (
    trigger_user_registration_email,
    trigger_password_reset_email,
    EmailService,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


# ── Helpers ────────────────────────────────────────────────────────

async def _create_refresh_token(db: AsyncSession, user_id: str, request: Request) -> str:
    """Create a refresh token, store its hash in DB, return raw token."""
    raw_token = generate_refresh_token()
    token_hash = hash_refresh_token(raw_token)

    rt = RefreshToken(
        user_id=uuid.UUID(user_id),
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=(request.headers.get("user-agent", "")[:255] if request else None),
        ip_address=(request.client.host if request and request.client else None),
    )
    db.add(rt)
    await db.commit()
    return raw_token


async def _revoke_user_tokens(db: AsyncSession, user_id: str):
    """Revoke all refresh tokens for a user (e.g. after password change)."""
    await db.execute(
        delete(RefreshToken).where(RefreshToken.user_id == uuid.UUID(user_id))
    )
    await db.commit()


def _build_token_response(access_token: str, refresh_token: str, user_dict: dict) -> dict:
    return {
        "token": access_token,
        "refresh_token": refresh_token,
        "user": user_dict,
    }


def _set_auth_cookies(response: JSONResponse, access_token: str, refresh_token: str):
    """Set httpOnly secure cookies for both tokens."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/api",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/auth",
    )


def _clear_auth_cookies(response: JSONResponse):
    """Remove auth cookies."""
    response.delete_cookie(key=COOKIE_NAME, path="/api")
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/auth")


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Register new user and institution."""
    # Password strength validation
    if len(user_data.password) < 8:
        raise HTTPException(status_code=400, detail="Heslo musí mít alespoň 8 znaků")
    if not re.search(r'[A-Z]', user_data.password):
        raise HTTPException(status_code=400, detail="Heslo musí obsahovat alespoň jedno velké písmeno")
    if not re.search(r'[a-z]', user_data.password):
        raise HTTPException(status_code=400, detail="Heslo musí obsahovat alespoň jedno malé písmeno")
    if not re.search(r'[0-9]', user_data.password):
        raise HTTPException(status_code=400, detail="Heslo musí obsahovat alespoň jednu číslici")

    user_repo = UserRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)
    theme_repo = ThemeRepositorySupabase(db)

    existing = await user_repo.find_by_email(user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Phase 83: backend duplicate-institution guard. Frontend pre-flight check
    # may warn the user, but the final block must live here so it cannot be
    # bypassed by skipping the check.
    from services.institution_duplicate_service import find_duplicate_institutions
    duplicates = await find_duplicate_institutions(
        db,
        name=user_data.institution_name,
        ico_dic=user_data.ico_dic,
        city=user_data.city,
    )
    strong = [d for d in duplicates if d.match_strength == "strong"]
    if strong:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "institution_duplicate",
                "message": (
                    "Tato instituce je již v systému aktivní. Pokud k ní patříte, "
                    "můžete odeslat žádost o přijetí do týmu."
                ),
                "matches": [
                    {
                        "id": d.id, "name": d.name, "city": d.city,
                        "ico_dic": d.ico_dic, "reason": d.reason,
                    } for d in strong
                ],
            },
        )

    institution = await institution_repo.create({
        "name": user_data.institution_name,
        "type": user_data.institution_type,
        "country": user_data.country,
        "address": user_data.address,
        "city": user_data.city,
        "ico_dic": user_data.ico_dic,
        "logo_url": user_data.logo_url,
        "default_available_days": user_data.default_available_days or ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "default_time_blocks": user_data.default_time_blocks or [{"start": "09:00", "end": "10:00"}],
        "default_program_duration": user_data.default_program_duration or 60,
        "default_program_capacity": user_data.default_program_capacity or 30,
        "default_target_group": user_data.default_target_group or "schools",
        "plan": "free",
        "programs_limit": 3,
    })

    user = await user_repo.create({
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "institution_id": institution["id"],
        "role": "admin",
        "name": user_data.name,
        "gdpr_consent": user_data.gdpr_consent,
        "terms_accepted": user_data.terms_accepted,
    })

    await theme_repo.create_or_update(institution["id"], {
        "primary_color": user_data.primary_color or "#1E293B",
        "secondary_color": user_data.secondary_color or "#84A98C",
        "accent_color": "#E9C46A",
        "logo_url": user_data.logo_url,
        "header_style": "light",
        "footer_text": None,
    })

    # Send registration emails in background
    async def send_registration_emails():
        try:
            await trigger_user_registration_email(
                user_email=user_data.email,
                user_name=user_data.name or user_data.email.split('@')[0],
                institution_name=user_data.institution_name,
            )
            logger.info(f"Registration confirmation email sent to {user_data.email}")
            await EmailService.send_transactional_email(
                template_name="new_institution_registration",
                to_email="info@budezivo.cz",
                data={
                    "institution_name": user_data.institution_name,
                    "institution_type": user_data.institution_type,
                    "user_email": user_data.email,
                    "institution_city": user_data.city or "",
                },
            )
        except Exception as e:
            logger.error(f"Failed to send registration emails: {str(e)}")

    background_tasks.add_task(send_registration_emails)

    access_token = create_jwt_token(user["id"], institution["id"], user_data.email, "admin")
    refresh_tok = await _create_refresh_token(db, user["id"], request)

    logger.info(f"New institution registered: {user_data.institution_name} ({user_data.email})")

    body = _build_token_response(access_token, refresh_tok, {
        "id": user["id"],
        "email": user_data.email,
        "name": user_data.name,
        "institution_id": institution["id"],
        "institution_name": user_data.institution_name,
        "role": "admin",
    })
    response = JSONResponse(content=body)
    _set_auth_cookies(response, access_token, refresh_tok)
    return response


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login existing user."""
    user_repo = UserRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)

    user = await user_repo.find_by_email(credentials.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    result = await db.execute(select(User).where(User.email == credentials.email))
    user_obj = result.scalar_one_or_none()

    if not user_obj or not verify_password(credentials.password, user_obj.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    institution = await institution_repo.find_by_id(user["institution_id"])
    access_token = create_jwt_token(user["id"], user["institution_id"], user["email"], user["role"])
    refresh_tok = await _create_refresh_token(db, user["id"], request)

    body = _build_token_response(access_token, refresh_tok, {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name"),
        "institution_id": user["institution_id"],
        "institution_name": institution["name"] if institution else "",
        "role": user["role"],
    })
    response = JSONResponse(content=body)
    _set_auth_cookies(response, access_token, refresh_tok)
    return response


class RefreshRequest(BaseModel):
    refresh_token: str = ""


@router.post("/refresh")
@limiter.limit("30/minute")
async def refresh_access_token(request: Request, body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access token + rotated refresh token."""
    # Try body first, then cookie
    raw_refresh = body.refresh_token or request.cookies.get(REFRESH_COOKIE_NAME, "")
    if not raw_refresh:
        raise HTTPException(status_code=401, detail="Refresh token chybí")

    token_hash = hash_refresh_token(raw_refresh)

    result = await db.execute(
        select(RefreshToken).where(
            and_(RefreshToken.token_hash == token_hash, RefreshToken.revoked.is_(False))
        )
    )
    stored = result.scalar_one_or_none()

    if not stored:
        raise HTTPException(status_code=401, detail="Neplatný refresh token")

    if stored.expires_at < datetime.now(timezone.utc):
        await db.delete(stored)
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token vypršel")

    # Get user info for new access token
    user_repo = UserRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)
    user = await user_repo.find_by_id(str(stored.user_id))
    if not user:
        raise HTTPException(status_code=401, detail="Uživatel nenalezen")

    institution = await institution_repo.find_by_id(user["institution_id"])

    # Rotate: revoke old, create new
    await db.delete(stored)
    await db.commit()

    new_access = create_jwt_token(user["id"], user["institution_id"], user["email"], user["role"])
    new_refresh = await _create_refresh_token(db, user["id"], request)

    body_data = _build_token_response(new_access, new_refresh, {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name"),
        "institution_id": user["institution_id"],
        "institution_name": institution["name"] if institution else "",
        "role": user["role"],
    })
    response = JSONResponse(content=body_data)
    _set_auth_cookies(response, new_access, new_refresh)
    return response


@router.post("/logout")
async def logout(
    request: Request,
    body: RefreshRequest = RefreshRequest(),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the given refresh token (server-side logout)."""
    raw_refresh = body.refresh_token or request.cookies.get(REFRESH_COOKIE_NAME, "")
    if raw_refresh:
        token_hash = hash_refresh_token(raw_refresh)
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored = result.scalar_one_or_none()
        if stored:
            await db.delete(stored)
            await db.commit()

    response = JSONResponse(content={"message": "Odhlášení úspěšné"})
    _clear_auth_cookies(response)
    return response


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Request password reset using JWT token."""
    import jwt as pyjwt

    user_repo = UserRepositorySupabase(db)
    user = await user_repo.find_by_email(data.email)

    if not user:
        return {"message": "If email exists, password reset link has been sent"}

    token_payload = {
        "user_id": str(user["id"]),
        "email": data.email,
        "type": "password_reset",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    reset_token = pyjwt.encode(token_payload, JWT_SECRET, algorithm="HS256")
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}&email={data.email}"

    async def send_reset_email():
        try:
            await trigger_password_reset_email(user_email=data.email, reset_link=reset_link)
            logger.info(f"Password reset email sent to {data.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")

    background_tasks.add_task(send_reset_email)
    logger.info(f"Password reset requested for {data.email}")
    return {"message": "If email exists, password reset link has been sent"}


class ResetPasswordRequest(BaseModel):
    """Reset password request schema."""
    token: str
    email: EmailStr
    new_password: str


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Reset user password using JWT token from email. Revokes all sessions."""
    import jwt as pyjwt

    user_repo = UserRepositorySupabase(db)
    secret_key = os.environ.get("JWT_SECRET")
    if not secret_key:
        raise HTTPException(status_code=500, detail="Konfigurace serveru není kompletní")

    try:
        payload = pyjwt.decode(data.token, secret_key, algorithms=["HS256"])
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Neplatný token")
        if payload.get("email") != data.email:
            raise HTTPException(status_code=400, detail="E-mail neodpovídá tokenu")
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Token pro obnovu hesla vypršel")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Neplatný token pro obnovu hesla")

    user = await user_repo.find_by_email(data.email)
    if not user:
        raise HTTPException(status_code=400, detail="Uživatel nenalezen")

    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Heslo musí mít alespoň 8 znaků")

    hashed_password = hash_password(data.new_password)
    await user_repo.update(user["id"], {"password_hash": hashed_password})

    # Revoke ALL refresh tokens for this user (force re-login everywhere)
    await _revoke_user_tokens(db, user["id"])

    async def send_password_changed_email():
        try:
            await EmailService.send_transactional_email(
                template_name="password_changed",
                to_email=data.email,
                data={"user_name": user.get("name", ""), "user_email": data.email},
            )
        except Exception as e:
            logger.error(f"Failed to send password changed email: {str(e)}")

    background_tasks.add_task(send_password_changed_email)
    logger.info(f"Password reset successful for {data.email}")
    return {"message": "Heslo bylo úspěšně změněno"}


class ChangePasswordRequest(BaseModel):
    """Change password (authenticated) request schema."""
    current_password: str
    new_password: str


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the password for the currently authenticated user.

    Requires the current password. Enforces the same strength policy as
    registration, revokes all other sessions for security, then re-issues
    fresh cookies so this session stays logged in.
    """
    if current_user.get("impersonated_by_email"):
        raise HTTPException(status_code=403, detail="Změna hesla není při impersonaci povolena")

    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user["user_id"])))
    user_obj = result.scalar_one_or_none()
    if not user_obj:
        raise HTTPException(status_code=404, detail="Uživatel nenalezen")

    if not verify_password(data.current_password, user_obj.password_hash):
        raise HTTPException(status_code=400, detail="Současné heslo není správné")

    pwd = data.new_password
    if len(pwd) < 8:
        raise HTTPException(status_code=400, detail="Heslo musí mít alespoň 8 znaků")
    if not re.search(r'[A-Z]', pwd):
        raise HTTPException(status_code=400, detail="Heslo musí obsahovat alespoň jedno velké písmeno")
    if not re.search(r'[a-z]', pwd):
        raise HTTPException(status_code=400, detail="Heslo musí obsahovat alespoň jedno malé písmeno")
    if not re.search(r'[0-9]', pwd):
        raise HTTPException(status_code=400, detail="Heslo musí obsahovat alespoň jednu číslici")
    if verify_password(pwd, user_obj.password_hash):
        raise HTTPException(status_code=400, detail="Nové heslo musí být odlišné od současného")

    user_repo = UserRepositorySupabase(db)
    await user_repo.update(str(user_obj.id), {"password_hash": hash_password(pwd)})

    # Invalidate all refresh tokens (logs out other devices), then mint fresh
    # tokens for THIS session so the current user is not kicked out.
    await _revoke_user_tokens(db, str(user_obj.id))
    access_token = create_jwt_token(
        current_user["user_id"],
        current_user["institution_id"],
        current_user["email"],
        current_user.get("role", "viewer"),
    )
    refresh_tok = await _create_refresh_token(db, str(user_obj.id), request)

    email = current_user["email"]
    name = getattr(user_obj, "name", "") or ""

    async def send_password_changed_email():
        try:
            await EmailService.send_transactional_email(
                template_name="password_changed",
                to_email=email,
                data={"user_name": name, "user_email": email},
            )
        except Exception as e:
            logger.error(f"Failed to send password changed email: {str(e)}")

    background_tasks.add_task(send_password_changed_email)

    response = JSONResponse(content={"message": "Heslo bylo úspěšně změněno"})
    _set_auth_cookies(response, access_token, refresh_tok)
    logger.info(f"Password changed for {email}")
    return response



@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """Verify JWT token validity."""
    return {"valid": True, "user": current_user}


@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user info including role and impersonation state."""
    user_repo = UserRepositorySupabase(db)
    user = await user_repo.find_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Surface impersonation info so the frontend can render a persistent banner
    if current_user.get("impersonated_by_email"):
        user["impersonation"] = {
            "active": True,
            "original_email": current_user["impersonated_by_email"],
            "original_user_id": current_user.get("impersonated_by_user_id"),
        }
    else:
        user["impersonation"] = {"active": False}
    return user
