"""Tests for the Contacts module whitelist (Phase 79).

Covers:
- /api/contacts/check-access returns False when flag missing/off and inst not whitelisted.
- /api/contacts (any CRUD) returns 403 with Czech detail when not whitelisted.
- /api/mailings/preview-contacts returns 403 when not whitelisted.
- After whitelisting via superadmin, all endpoints return 200.

Uses the existing demo superadmin credentials and the live test backend.
"""
from __future__ import annotations

import os
import requests
import pytest


BASE = os.environ.get("REACT_APP_BACKEND_URL") or os.environ.get(
    "TEST_BASE_URL"
) or "http://localhost:8001"
SUPERADMIN_EMAIL = "demo@budezivo.cz"
SUPERADMIN_PASSWORD = "Demo2026!"
PLATFORM_INST = "c18a10b9-4dd0-4779-86b9-b68dae21c71f"
FLAG_KEY = "contacts_module"


def _read_backend_url():
    """Prefer REACT_APP_BACKEND_URL from frontend/.env so tests hit the real ingress."""
    p = "/app/frontend/.env"
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.strip().split("=", 1)[1]
    return BASE


API = _read_backend_url().rstrip("/")


def _login() -> str:
    r = requests.post(
        f"{API}/api/auth/login",
        json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["token"]


def _set_whitelist(token: str, *, allow: bool) -> None:
    body = (
        {"add_institution_ids": [PLATFORM_INST]}
        if allow
        else {"remove_institution_ids": [PLATFORM_INST]}
    )
    r = requests.put(
        f"{API}/api/superadmin/feature-flags/{FLAG_KEY}",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=15,
    )
    r.raise_for_status()


@pytest.fixture(scope="module")
def token():
    return _login()


@pytest.fixture(autouse=True)
def _clean_state(token):
    # Always start each test with the flag DISABLED for the platform inst.
    _set_whitelist(token, allow=False)
    yield
    _set_whitelist(token, allow=False)


def test_check_access_returns_false_when_disabled(token):
    r = requests.get(
        f"{API}/api/contacts/check-access",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json() == {"enabled": False}


def test_list_contacts_returns_403_when_disabled(token):
    r = requests.get(
        f"{API}/api/contacts",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r.status_code == 403
    assert "Kontakty" in r.json().get("detail", "")


def test_preview_contacts_returns_403_when_disabled(token):
    r = requests.post(
        f"{API}/api/mailings/preview-contacts",
        headers={"Authorization": f"Bearer {token}"},
        json={},
        timeout=10,
    )
    assert r.status_code == 403


def test_endpoints_return_200_after_whitelist(token):
    _set_whitelist(token, allow=True)
    # check-access reflects the change
    r = requests.get(
        f"{API}/api/contacts/check-access",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json() == {"enabled": True}

    # list passes
    r = requests.get(
        f"{API}/api/contacts",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # preview-contacts passes
    r = requests.post(
        f"{API}/api/mailings/preview-contacts",
        headers={"Authorization": f"Bearer {token}"},
        json={},
        timeout=10,
    )
    assert r.status_code == 200
    body = r.json()
    assert "total" in body and "recipients" in body
