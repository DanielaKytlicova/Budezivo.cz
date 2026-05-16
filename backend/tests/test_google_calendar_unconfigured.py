"""Tests for the Google Calendar integration (Phase 80).

Live-server tests against the running backend. Verifies the graceful
"not configured" state when GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are unset,
plus parity with the existing Outlook integration shape.
"""
from __future__ import annotations

import os
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
SUPERADMIN_EMAIL = "demo@budezivo.cz"
SUPERADMIN_PASSWORD = "Demo2026!"


@pytest.fixture(scope="module")
def token():
    r = requests.post(
        f"{API}/api/auth/login",
        json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_google_status_returns_not_connected_and_not_configured(token):
    r = requests.get(f"{API}/api/google-calendar/status", headers=_h(token), timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["connected"] is False
    # GOOGLE_CLIENT_ID/SECRET not set in this environment
    assert body["configured"] is False


def test_google_connect_returns_503_when_not_configured(token):
    r = requests.get(f"{API}/api/google-calendar/connect", headers=_h(token), timeout=10)
    assert r.status_code == 503
    assert "Google" in r.json().get("detail", "")


def test_google_blocks_returns_empty_list(token):
    r = requests.get(f"{API}/api/google-calendar/blocks", headers=_h(token), timeout=10)
    assert r.status_code == 200
    assert r.json() == []


def test_google_disconnect_idempotent(token):
    """Disconnect on a non-existing integration should not crash."""
    r = requests.post(f"{API}/api/google-calendar/disconnect", headers=_h(token), timeout=10)
    assert r.status_code == 200
    assert "odpojen" in r.json().get("message", "").lower()


def test_outlook_endpoints_still_work(token):
    """Parity check: MS endpoints must keep responding after Google was added."""
    r = requests.get(f"{API}/api/microsoft-calendar/status", headers=_h(token), timeout=10)
    assert r.status_code == 200
    assert "connected" in r.json()
