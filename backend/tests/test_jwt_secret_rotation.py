import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("JWT_SECRET", "current-secret")

import jwt
import pytest

from core.config import JWT_ALGORITHM
from core.security import decode_jwt_token
from routes import calendar_export


def _token(secret: str, exp: datetime | None = None) -> str:
    return jwt.encode(
        {
            "sub": "user-1",
            "exp": exp or datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm=JWT_ALGORITHM,
    )


def test_decode_accepts_previous_jwt_secret():
    token = _token("previous-secret")

    payload = decode_jwt_token(
        token,
        secrets_to_try=["current-secret", "previous-secret"],
    )

    assert payload["sub"] == "user-1"


def test_decode_rejects_expired_previous_jwt_secret():
    token = _token("previous-secret", datetime.now(timezone.utc) - timedelta(minutes=1))

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_jwt_token(
            token,
            secrets_to_try=["current-secret", "previous-secret"],
        )


def test_ics_feed_accepts_previous_jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "current-secret")
    monkeypatch.setenv("JWT_PREVIOUS_SECRET", "previous-secret")

    msg = b"institution:inst-1"
    old_key = hashlib.sha256(b"ics-feed-previous-secret").digest()
    old_token = hmac.new(old_key, msg, hashlib.sha256).hexdigest()[:32]

    assert calendar_export._verify_feed_token("institution", "inst-1", old_token)
    assert calendar_export._sign_feed_token("institution", "inst-1") != old_token
