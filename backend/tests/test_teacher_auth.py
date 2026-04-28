"""Tests for Teacher (B2C) auth + favorites + bookings — Etapa 4.

Coverage:
- Register / duplicate-409 / login / wrong-pw / 5x lockout-429
- /auth/me with cookie + Bearer
- PATCH /me
- Favorites add/idempotent/list/delete + 400/404
- Bookings empty list
- Cross-token rejection: teacher token on admin endpoint
"""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

API = f"{BASE_URL}/api"


def _rand_email():
    # backend lowercases via EmailStr validator, so use lowercase to allow round-trip equality
    return f"test_t_{uuid.uuid4().hex[:10]}@example.cz"


@pytest.fixture(scope="module")
def teacher():
    s = requests.Session()
    email = _rand_email()
    pw = "TestUcitel2026!"
    r = s.post(f"{API}/teacher/auth/register", json={
        "email": email, "password": pw, "name": "Učitel Test",
        "school_name": "ZŠ Test", "phone": "+420111222333",
    })
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    assert "access_token" in data and data["email"] == email
    return {"session": s, "email": email, "password": pw, "token": data["access_token"], "id": data["id"]}


@pytest.fixture(scope="module")
def program_id():
    r = requests.get(f"{API}/public/catalog?limit=3")
    assert r.status_code == 200, r.text
    items = r.json()
    if isinstance(items, dict):
        items = items.get("items") or items.get("results") or items.get("data") or []
    assert items, "no catalog programs"
    return items[0]["id"]


# -------- Register / Login --------

def test_register_duplicate_returns_409(teacher):
    r = requests.post(f"{API}/teacher/auth/register", json={
        "email": teacher["email"], "password": "AnotherPw123!", "name": "Dup",
    })
    assert r.status_code == 409


def test_register_sets_httponly_cookie():
    s = requests.Session()
    email = _rand_email()
    r = s.post(f"{API}/teacher/auth/register", json={
        "email": email, "password": "Strong1234!", "name": "Cookie Test",
    })
    assert r.status_code == 200
    set_cookie_hdr = r.headers.get("set-cookie", "")
    assert "teacher_token=" in set_cookie_hdr
    assert "HttpOnly" in set_cookie_hdr


def test_login_email_normalized_lowercase():
    s = requests.Session()
    email = _rand_email()
    s.post(f"{API}/teacher/auth/register", json={
        "email": email, "password": "Strong1234!", "name": "Norm",
    })
    r = s.post(f"{API}/teacher/auth/login", json={
        "email": email.upper(), "password": "Strong1234!",
    })
    assert r.status_code == 200
    assert r.json()["email"] == email.lower()


def test_login_wrong_password_401(teacher):
    r = requests.post(f"{API}/teacher/auth/login", json={
        "email": teacher["email"], "password": "WrongPassword!",
    })
    assert r.status_code == 401


def test_lockout_after_5_failed_attempts():
    s = requests.Session()
    email = _rand_email()
    s.post(f"{API}/teacher/auth/register", json={
        "email": email, "password": "Strong1234!", "name": "Lock Test",
    })
    last = None
    for _ in range(5):
        last = s.post(f"{API}/teacher/auth/login", json={
            "email": email, "password": "BadPwBadPw!",
        })
    # 5th may already be 429 if lockout triggered AT the 5th attempt
    assert last.status_code in (401, 429)
    r = s.post(f"{API}/teacher/auth/login", json={
        "email": email, "password": "Strong1234!",
    })
    assert r.status_code == 429, f"expected 429, got {r.status_code}"


# -------- /auth/me --------

def test_me_with_bearer_token(teacher):
    r = requests.get(f"{API}/teacher/auth/me", headers={
        "Authorization": f"Bearer {teacher['token']}"
    })
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == teacher["email"]
    assert "password_hash" not in body


def test_me_without_auth_401():
    r = requests.get(f"{API}/teacher/auth/me")
    assert r.status_code == 401


def test_me_with_cookie(teacher):
    # Login via session cookie
    s = requests.Session()
    s.post(f"{API}/teacher/auth/login", json={
        "email": teacher["email"], "password": teacher["password"],
    })
    r = s.get(f"{API}/teacher/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == teacher["email"]


# -------- PATCH /me --------

def test_patch_profile_updates_fields(teacher):
    h = {"Authorization": f"Bearer {teacher['token']}"}
    r = requests.patch(f"{API}/teacher/me", headers=h, json={
        "name": "Updated Name", "school_name": "Updated School", "phone": "+420999",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Updated Name"
    assert body["school_name"] == "Updated School"
    # verify persisted
    me = requests.get(f"{API}/teacher/auth/me", headers=h).json()
    assert me["school_name"] == "Updated School"


# -------- Cross-token: teacher token must NOT pass admin auth --------

def test_teacher_token_rejected_on_admin_endpoint(teacher):
    h = {"Authorization": f"Bearer {teacher['token']}"}
    r = requests.get(f"{API}/auth/me", headers=h)
    assert r.status_code in (401, 403, 422), f"got {r.status_code}: {r.text}"


# -------- Favorites --------

def test_favorite_add_idempotent_list_delete(teacher, program_id):
    h = {"Authorization": f"Bearer {teacher['token']}"}

    r1 = requests.post(f"{API}/teacher/favorites", headers=h, json={"program_id": program_id})
    assert r1.status_code == 200, r1.text
    assert r1.json().get("ok") is True
    assert r1.json().get("already") is False

    r2 = requests.post(f"{API}/teacher/favorites", headers=h, json={"program_id": program_id})
    assert r2.status_code == 200
    assert r2.json().get("already") is True

    rl = requests.get(f"{API}/teacher/favorites", headers=h)
    assert rl.status_code == 200
    favs = rl.json()
    assert isinstance(favs, list) and len(favs) >= 1
    fav = next((f for f in favs if f["program_id"] == program_id), None)
    assert fav is not None
    assert "name" in fav and "institution_name" in fav and "image_url" in fav

    rd = requests.delete(f"{API}/teacher/favorites/{program_id}", headers=h)
    assert rd.status_code == 200


def test_favorite_invalid_uuid_400(teacher):
    h = {"Authorization": f"Bearer {teacher['token']}"}
    r = requests.post(f"{API}/teacher/favorites", headers=h, json={"program_id": "not-a-uuid"})
    assert r.status_code == 400


def test_favorite_nonexistent_404(teacher):
    h = {"Authorization": f"Bearer {teacher['token']}"}
    r = requests.post(f"{API}/teacher/favorites", headers=h, json={
        "program_id": str(uuid.uuid4()),
    })
    assert r.status_code == 404


# -------- Bookings (empty for fresh teacher) --------

def test_bookings_empty_for_new_teacher(teacher):
    h = {"Authorization": f"Bearer {teacher['token']}"}
    r = requests.get(f"{API}/teacher/bookings", headers=h)
    assert r.status_code == 200
    assert r.json() == []


# -------- Regression: admin login works --------

def test_admin_login_still_works():
    r = requests.post(f"{API}/auth/login", json={
        "email": "demo@budezivo.cz", "password": "Demo2026!",
    })
    assert r.status_code == 200, r.text
    assert "access_token" in r.json() or "token" in r.json()
