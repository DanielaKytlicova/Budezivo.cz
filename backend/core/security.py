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


def create_jwt_token(user_id: str, institution_id: str, email: str, role: str = "viewer") -> str:
    """Create a short-lived JWT access token."""
    payload = {
        "user_id": user_id,
        "institution_id": institution_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
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
    """
    token = _extract_token(request, credentials)
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
