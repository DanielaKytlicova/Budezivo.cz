"""Regression tests for payment return-URL routing.

Ensures that the customer-return URL handed to Comgate (`url_paid` /
`url_cancelled`) points at the FRONTEND host and not the API host.

Bug fixed in iter71: when the SPA called POST /api/event-payments/initiate,
`request.host` resolved to ``api.budezivo.cz`` (the backend host), so Comgate
redirected paying customers back to ``https://api.budezivo.cz/payment/return``
which is JSON-only and returned ``{"detail":"Not Found"}``.
"""
from types import SimpleNamespace
import os

from routes.event_payments import (
    _build_public_base_url,
    _build_frontend_base_url,
)


def _req(headers: dict, scheme: str = "https", host: str = "api.budezivo.cz"):
    """Cheap stand-in for fastapi.Request — only the bits the helpers read."""
    norm = {k.lower(): v for k, v in headers.items()}

    class _H:
        def get(self, key, default=None):
            return norm.get(key.lower(), default)

    return SimpleNamespace(
        headers=_H(),
        url=SimpleNamespace(scheme=scheme, hostname=host, query=""),
    )


# ---------- Public (webhook) base URL ----------

def test_public_base_url_uses_request_host():
    r = _req({"host": "api.budezivo.cz", "x-forwarded-proto": "https"})
    assert _build_public_base_url(r) == "https://api.budezivo.cz"


def test_public_base_url_env_override(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://api.staging.example.com/")
    r = _req({"host": "api.budezivo.cz"})
    assert _build_public_base_url(r) == "https://api.staging.example.com"


# ---------- Frontend base URL ----------

def test_frontend_url_prefers_origin_header():
    r = _req({
        "host": "api.budezivo.cz",
        "origin": "https://budezivo.cz",
        "referer": "https://budezivo.cz/akce/test",
    })
    assert _build_frontend_base_url(r) == "https://budezivo.cz"


def test_frontend_url_falls_back_to_referer_when_no_origin():
    r = _req({
        "host": "api.budezivo.cz",
        "referer": "https://budezivo.cz/akce/test",
    })
    assert _build_frontend_base_url(r) == "https://budezivo.cz"


def test_frontend_url_strips_api_prefix_as_last_resort():
    r = _req({"host": "api.budezivo.cz", "x-forwarded-proto": "https"})
    # No Origin / Referer / FRONTEND_BASE_URL → strip api.
    assert _build_frontend_base_url(r) == "https://budezivo.cz"


def test_frontend_url_env_override_wins(monkeypatch):
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://www.budezivo.cz/")
    r = _req({
        "host": "api.budezivo.cz",
        "origin": "https://other.example.com",
    })
    assert _build_frontend_base_url(r) == "https://www.budezivo.cz"
    monkeypatch.delenv("FRONTEND_BASE_URL", raising=False)


def test_frontend_url_no_change_when_host_already_frontend():
    r = _req({"host": "budezivo.cz", "x-forwarded-proto": "https"})
    # No api. prefix to strip → returns as-is
    assert _build_frontend_base_url(r) == "https://budezivo.cz"


def test_frontend_url_handles_localhost_dev():
    """Local dev: same host for API and SPA → returns the request host unchanged."""
    if "FRONTEND_BASE_URL" in os.environ:
        del os.environ["FRONTEND_BASE_URL"]
    r = _req({"host": "localhost:3000", "x-forwarded-proto": "http"}, scheme="http")
    assert _build_frontend_base_url(r) == "http://localhost:3000"
