"""
Security utilities: password hashing, JWT handling, refresh tokens.
Supports both httpOnly cookie and Authorization header for JWT extraction.
"""
import hashlib
import secrets
import bcrypt
import jwt as pyjwt
from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from .config import JWT_SECRET, JWT_ALGORITHM

security = HTTPBearer(auto_error=False)

# Access token: short-lived (15 min)
ACCESS_TOKEN_EXPIRE_MINUTES = 15
# Refresh token: long-lived (30 days)
REFRESH_TOKEN_EXPIRE_DAYS = 30

COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_jwt_token(
    user_id: str,
    institution_id: str,
    email: str,
    role: str = "viewer",
    *,
    impersonated_by_user_id: Optional[str] = None,
    impersonated_by_email: Optional[str] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """Create a short-lived JWT access token.

    When `impersonated_by_*` is set, the caller acts AS `user_id` but the
    audit/UI layer knows it is really `impersonated_by_*` behind the scenes.
    Impersonation tokens default to a shorter lifetime.
    """
    exp_minutes = expires_minutes if expires_minutes is not None else ACCESS_TOKEN_EXPIRE_MINUTES
    payload = {
        "user_id": user_id,
        "institution_id": institution_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=exp_minutes),
    }
    if impersonated_by_user_id and impersonated_by_email:
        payload["impersonated_by_user_id"] = impersonated_by_user_id
        payload["impersonated_by_email"] = impersonated_by_email
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_refresh_token() -> str:
    """Generate a cryptographically secure opaque refresh token."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hash of a refresh token for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> str:
    """Extract JWT from httpOnly cookie first, then fallback to Authorization header."""
    # 1. Try httpOnly cookie
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        return cookie_token

    # 2. Fallback to Authorization: Bearer header
    if credentials and credentials.credentials:
        return credentials.credentials

    raise HTTPException(status_code=401, detail="Přihlášení vyžadováno")


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Dependency that extracts and validates the current user from JWT token.
    Checks httpOnly cookie first, then Authorization header.

    SECURITY: Tokens minted for non-admin account types (e.g. `account_type='teacher'`)
    must be rejected here so admin route handlers don't crash with KeyError on
    missing `user_id`. We require either:
      - explicit `account_type` of admin/lecturer/staff/etc. (anything but 'teacher')
      - OR no `account_type` field (legacy admin tokens minted before that key existed)
      - AND a `user_id` field (mandatory for admin code paths).
    """
    token = _extract_token(request, credentials)
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Reject non-administrative account types up front.
    account_type = payload.get("account_type")
    if account_type and account_type != "admin":
        raise HTTPException(
            status_code=401,
            detail="Tento token nepatří administrátorovi platformy.",
        )
    if "user_id" not in payload:
        raise HTTPException(status_code=401, detail="Neplatný token")
    return payload
