"""Regression tests for the upgraded /api/team/invite endpoint.

The endpoint now handles four distinct cases (Phase 82):
1. Brand-new e-mail → classic create
2. Soft-deleted user → reactivate + reassign (preserve name & password)
3. Already a member of the same institution → idempotent friendly noop
4. Active in a different institution → 409 for regular admin, force-move
   allowed for superadmin

Tests run against the live backend using the seeded demo credentials.
"""
from __future__ import annotations

import os
import uuid
import requests
import pytest


def _read_backend_url() -> str:
    p = "/app/frontend/.env"
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.strip().split("=", 1)[1].rstrip("/")
    return os.environ.get("TEST_BASE_URL", "http://localhost:8001")


API = _read_backend_url()
SUPERADMIN = ("demo@budezivo.cz", "Demo2026!")


def _login(email: str, password: str) -> str:
    r = requests.post(
        f"{API}/api/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(*SUPERADMIN)


@pytest.fixture
def unique_email():
    return f"pytest_invite_{uuid.uuid4().hex[:8]}@example.cz"


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _cleanup_user(email: str) -> None:
    """Hard-delete a test user from the DB if it exists (sync psycopg2 — avoids
    asyncpg pool conflicts with the live backend)."""
    import psycopg2
    raw_url = ""
    with open("/app/backend/.env") as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                raw_url = line.strip().split("=", 1)[1]
                break
    if not raw_url:
        return
    pg_url = raw_url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = psycopg2.connect(pg_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE email=%s", (email,))
        conn.close()
    except Exception:
        pass


def test_brand_new_user_creates_invite(admin_token, unique_email):
    """Case 1: brand-new e-mail → classic create with temp password."""
    try:
        r = requests.post(
            f"{API}/api/team/invite",
            headers=_h(admin_token),
            json={"name": "Test One", "email": unique_email, "role": "lektor"},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "created"
        assert "temp_password" in body and len(body["temp_password"]) >= 6
    finally:
        _cleanup_user(unique_email)


def test_existing_member_returns_idempotent_noop(admin_token, unique_email):
    """Case 3: user already in this institution → noop_already_member."""
    try:
        # First invite — creates the user
        r1 = requests.post(
            f"{API}/api/team/invite",
            headers=_h(admin_token),
            json={"name": "Twice", "email": unique_email, "role": "lektor"},
            timeout=10,
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["mode"] == "created"

        # Second invite of the same e-mail to the same institution
        r2 = requests.post(
            f"{API}/api/team/invite",
            headers=_h(admin_token),
            json={"name": "Twice", "email": unique_email, "role": "lektor"},
            timeout=10,
        )
        assert r2.status_code == 200, r2.text
        body2 = r2.json()
        assert body2["mode"] == "noop_already_member"
        # And critically: no English "already exists" / no 400 error
        assert "exists" not in body2["message"].lower()
    finally:
        _cleanup_user(unique_email)


def test_soft_deleted_user_is_reactivated_with_credentials_preserved(admin_token, unique_email):
    """Case 2: invite a soft-deleted user → reactivate + reassign,
    preserve name & password_hash."""
    import os
    import psycopg2
    from datetime import datetime, timezone

    # Use a sync psycopg2 connection for test introspection so we don't fight
    # with the live backend's asyncpg pool.
    raw_url = ""
    env_path = "/app/backend/.env"
    with open(env_path) as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                raw_url = line.strip().split("=", 1)[1]
                break
    assert raw_url, "DATABASE_URL not set"
    pg_url = raw_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        # 1. Create the user via the API
        r1 = requests.post(
            f"{API}/api/team/invite",
            headers=_h(admin_token),
            json={"name": "Recovered User", "email": unique_email, "role": "lektor"},
            timeout=10,
        )
        assert r1.status_code == 200, r1.text

        # 2. Snapshot password_hash + name, then soft-delete via sync DB
        conn = psycopg2.connect(pg_url)
        try:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT password_hash, name FROM users WHERE email=%s",
                    (unique_email,),
                )
                original_hash, original_name = cur.fetchone()
                assert original_hash and original_name == "Recovered User"

                cur.execute(
                    "UPDATE users SET deleted_at=%s WHERE email=%s",
                    (datetime.now(timezone.utc), unique_email),
                )
        finally:
            conn.close()

        # 3. Re-invite — must reactivate, NOT fail with "exists"
        r2 = requests.post(
            f"{API}/api/team/invite",
            headers=_h(admin_token),
            json={"name": "IgnoredName", "email": unique_email, "role": "edukator"},
            timeout=10,
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["mode"] == "reactivated"

        # 4. Verify state
        conn = psycopg2.connect(pg_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT deleted_at, role, password_hash, name "
                    "FROM users WHERE email=%s",
                    (unique_email,),
                )
                deleted_at, role, pwd_hash, name = cur.fetchone()
        finally:
            conn.close()

        assert deleted_at is None
        assert role == "edukator"
        assert pwd_hash == original_hash, "password must be preserved"
        assert name == original_name, "name must be preserved"
    finally:
        _cleanup_user(unique_email)


def test_invalid_role_rejected(admin_token, unique_email):
    r = requests.post(
        f"{API}/api/team/invite",
        headers=_h(admin_token),
        json={"name": "X", "email": unique_email, "role": "wizard"},
        timeout=10,
    )
    assert r.status_code == 400
    assert "role" in r.json()["detail"].lower()


def test_missing_email_rejected(admin_token):
    r = requests.post(
        f"{API}/api/team/invite",
        headers=_h(admin_token),
        json={"name": "X", "email": "", "role": "lektor"},
        timeout=10,
    )
    # Either pydantic 422 (empty email) or our 400 — both acceptable; never 500.
    assert r.status_code in (400, 422)
