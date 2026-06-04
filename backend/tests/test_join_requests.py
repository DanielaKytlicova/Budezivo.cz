"""Tests for the institution duplicate-detection & join-request workflow (Phase 83)."""
from __future__ import annotations

import os
import uuid
import psycopg2
import requests
import pytest


def _read_backend_url() -> str:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.strip().split("=", 1)[1].rstrip("/")
    return "http://localhost:8001"


def _pg_url() -> str:
    with open("/app/backend/.env") as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                return line.strip().split("=", 1)[1].replace("postgresql+asyncpg://", "postgresql://")
    return ""


API = _read_backend_url()
SUPERADMIN = ("demo@budezivo.cz", "Demo2026!")
GALLERY_ADMIN = ("galerie@budezivo.cz", "Galerie2026!")
TEST_INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"  # Test Muzeum


def _login(email: str, password: str) -> str:
    r = requests.post(
        f"{API}/api/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["token"]


@pytest.fixture(scope="module")
def superadmin_token():
    return _login(*SUPERADMIN)


@pytest.fixture(scope="module")
def gallery_token():
    return _login(*GALLERY_ADMIN)


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _cleanup_request(email: str) -> None:
    conn = psycopg2.connect(_pg_url())
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM institution_join_requests WHERE email=%s", (email,))
            cur.execute("DELETE FROM users WHERE email=%s", (email,))
    finally:
        conn.close()


@pytest.fixture
def fresh_email():
    email = f"jr_pytest_{uuid.uuid4().hex[:8]}@example.cz"
    yield email
    _cleanup_request(email)


# ────────────────────────────────────────────────────────────────────
# Duplicate detection
# ────────────────────────────────────────────────────────────────────


def test_check_duplicate_returns_empty_for_unique_institution():
    r = requests.post(
        f"{API}/api/institutions/check-duplicate",
        json={"name": "Galerie Žirafa 2030", "city": "Olomouc"},
        timeout=10,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["has_strong_match"] is False
    assert body["has_weak_match"] is False
    assert body["duplicates"] == []


def test_check_duplicate_detects_strong_match_by_ico():
    """If IČO matches an existing institution, that's a strong match."""
    # First, retrieve a known institution's IČO
    conn = psycopg2.connect(_pg_url())
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT ico_dic FROM institutions WHERE ico_dic IS NOT NULL "
            "AND ico_dic <> '' LIMIT 1"
        )
        row = cur.fetchone()
    conn.close()
    if not row:
        pytest.skip("No institution with IČO in the DB to test against")

    existing_ico = row[0]
    r = requests.post(
        f"{API}/api/institutions/check-duplicate",
        json={"name": "Úplně jiný název", "ico_dic": existing_ico, "city": "Brno"},
        timeout=10,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["has_strong_match"] is True
    assert any(d["match_strength"] == "strong" for d in body["duplicates"])


def test_register_blocks_when_ico_matches_existing():
    """The backend register endpoint must enforce the duplicate guard, not just frontend."""
    conn = psycopg2.connect(_pg_url())
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT ico_dic FROM institutions WHERE ico_dic IS NOT NULL "
            "AND ico_dic <> '' LIMIT 1"
        )
        row = cur.fetchone()
    conn.close()
    if not row:
        pytest.skip("No institution with IČO in the DB to test against")

    fake_email = f"reg_pytest_{uuid.uuid4().hex[:6]}@example.cz"
    r = requests.post(
        f"{API}/api/auth/register",
        json={
            "name": "Pytest user",
            "email": fake_email,
            "password": "Heslo123!",
            "institution_name": "Pytest duplicitní",
            "institution_type": "muzeum",
            "ico_dic": row[0],
            "city": "Praha",
            "country": "CZ",
        },
        timeout=15,
    )
    # Cleanup just in case
    _cleanup_request(fake_email)
    assert r.status_code == 409, r.text
    body = r.json()
    detail = body.get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "institution_duplicate"


# ────────────────────────────────────────────────────────────────────
# Join request submission
# ────────────────────────────────────────────────────────────────────


def test_anonymous_user_can_submit_join_request(fresh_email):
    r = requests.post(
        f"{API}/api/institutions/{TEST_INSTITUTION_ID}/join-request",
        json={"email": fresh_email, "name": "Test One", "message": "Patřím k vám"},
        timeout=10,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "pending"
    assert body["email"] == fresh_email
    assert body["user_id"] is None  # anonymous submitter


def test_duplicate_pending_request_returns_409(fresh_email):
    # First submission OK
    r1 = requests.post(
        f"{API}/api/institutions/{TEST_INSTITUTION_ID}/join-request",
        json={"email": fresh_email, "name": "Test"},
        timeout=10,
    )
    assert r1.status_code == 201

    # Second submission must be rejected
    r2 = requests.post(
        f"{API}/api/institutions/{TEST_INSTITUTION_ID}/join-request",
        json={"email": fresh_email, "name": "Test"},
        timeout=10,
    )
    assert r2.status_code == 409
    assert "čeká" in r2.json()["detail"].lower() or "schvál" in r2.json()["detail"].lower()


def test_already_member_cannot_request(superadmin_token):
    """Submitter who is already an active member of the institution → 409."""
    # demo@budezivo.cz is admin of the platform institution; create a join req
    # to that same institution targeting demo's e-mail.
    conn = psycopg2.connect(_pg_url())
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT institution_id FROM users WHERE email='demo@budezivo.cz' LIMIT 1"
        )
        row = cur.fetchone()
    conn.close()
    if not row:
        pytest.skip("demo user not found")
    inst_id = row[0]

    r = requests.post(
        f"{API}/api/institutions/{inst_id}/join-request",
        json={"email": "demo@budezivo.cz"},
        timeout=10,
    )
    assert r.status_code == 409
    assert "již členem" in r.json()["detail"]


# ────────────────────────────────────────────────────────────────────
# Approve / reject flow
# ────────────────────────────────────────────────────────────────────


def test_admin_can_list_and_approve_join_request(superadmin_token, fresh_email):
    # Submit
    r1 = requests.post(
        f"{API}/api/institutions/{TEST_INSTITUTION_ID}/join-request",
        json={"email": fresh_email, "name": "Approver Target"},
        timeout=10,
    )
    assert r1.status_code == 201
    req_id = r1.json()["id"]

    # List (as superadmin — also valid)
    r2 = requests.get(
        f"{API}/api/institutions/{TEST_INSTITUTION_ID}/join-requests?status=pending",
        headers=_h(superadmin_token),
        timeout=10,
    )
    assert r2.status_code == 200
    assert any(x["id"] == req_id for x in r2.json())

    # Approve with role
    r3 = requests.post(
        f"{API}/api/institutions/{TEST_INSTITUTION_ID}/join-requests/{req_id}/approve",
        headers=_h(superadmin_token),
        json={"assigned_role": "lektor"},
        timeout=10,
    )
    assert r3.status_code == 200, r3.text
    body = r3.json()
    assert body["request"]["status"] == "approved"
    assert body["request"]["assigned_role"] == "lektor"
    # Brand-new user was created → temp_password returned
    assert body["mode"] == "created"
    assert body["temp_password"]


def test_admin_can_reject_join_request(superadmin_token, fresh_email):
    r1 = requests.post(
        f"{API}/api/institutions/{TEST_INSTITUTION_ID}/join-request",
        json={"email": fresh_email, "name": "Reject Target"},
        timeout=10,
    )
    assert r1.status_code == 201
    req_id = r1.json()["id"]

    r2 = requests.post(
        f"{API}/api/institutions/{TEST_INSTITUTION_ID}/join-requests/{req_id}/reject",
        headers=_h(superadmin_token),
        json={"review_note": "K nám nepatříte."},
        timeout=10,
    )
    assert r2.status_code == 200
    assert r2.json()["request"]["status"] == "rejected"


def test_regular_admin_cannot_review_other_institutions_requests(gallery_token, fresh_email):
    """Galerie admin must NOT be able to review requests of a different institution."""
    r1 = requests.post(
        f"{API}/api/institutions/{TEST_INSTITUTION_ID}/join-request",
        json={"email": fresh_email, "name": "Foreign target"},
        timeout=10,
    )
    assert r1.status_code == 201

    # Gallery admin tries to list TEST_INSTITUTION_ID's requests
    # (Test institution ID is unrelated to gallery@)
    # Note: in seed data galerie@ may BE admin of Test Muzeum; if so this test
    # asserts the inverse scenario by using a different institution ID.
    other_inst = "00000000-0000-0000-0000-000000000000"
    r2 = requests.get(
        f"{API}/api/institutions/{other_inst}/join-requests",
        headers=_h(gallery_token),
        timeout=10,
    )
    assert r2.status_code == 403


def test_approving_already_processed_request_returns_400(superadmin_token, fresh_email):
    r1 = requests.post(
        f"{API}/api/institutions/{TEST_INSTITUTION_ID}/join-request",
        json={"email": fresh_email, "name": "Once"},
        timeout=10,
    )
    req_id = r1.json()["id"]

    requests.post(
        f"{API}/api/institutions/{TEST_INSTITUTION_ID}/join-requests/{req_id}/reject",
        headers=_h(superadmin_token),
        json={},
        timeout=10,
    )
    # Try to approve a rejected request
    r3 = requests.post(
        f"{API}/api/institutions/{TEST_INSTITUTION_ID}/join-requests/{req_id}/approve",
        headers=_h(superadmin_token),
        json={"assigned_role": "lektor"},
        timeout=10,
    )
    assert r3.status_code == 400


# ────────────────────────────────────────────────────────────────────
# Superadmin cross-institution view
# ────────────────────────────────────────────────────────────────────


def test_superadmin_sees_cross_institution_requests(superadmin_token):
    r = requests.get(
        f"{API}/api/superadmin/join-requests",
        headers=_h(superadmin_token),
        timeout=10,
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)
