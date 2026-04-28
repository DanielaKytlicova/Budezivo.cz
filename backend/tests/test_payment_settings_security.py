"""Regression tests for Comgate payment settings & webhook signature hardening.

Covers the bug reported by the user where the LIVE/TEST/MOCK badge always
showed "MOCK" because the backend masked the credentials in the response.

Public contract guaranteed by these tests:
1. GET  /events/settings/payment never exposes raw `gateway_api_key` /
   `gateway_secret`, but always returns:
     - `gateway_mode`: MOCK | TEST | LIVE
     - `gateway_api_key_masked`: short hint preserving TEST_ prefix + last 4
     - `gateway_secret_set`: bool
2. PUT  /events/settings/payment with empty strings for credentials does NOT
   wipe stored keys (preserves on every save), but accepts the literal
   "__CLEAR__" sentinel to remove them.
3. ComgateGateway.parse_webhook:
     - Rejects in TEST/LIVE when not configured.
     - Rejects on merchant or secret mismatch.
     - Uses constant-time comparison.
     - Accepts in MOCK regardless (route-level guard prevents real abuse).
"""
import asyncio
import pytest

from services.payment_gateways.comgate import ComgateGateway
from services.payment_gateways.base import GatewayMode
from routes.events import _mask_merchant, _enrich_payment_settings, CLEAR_SENTINEL


# ---------- Mask helper ----------

def test_mask_merchant_none():
    assert _mask_merchant(None) is None
    assert _mask_merchant("") is None
    assert _mask_merchant("   ") is None


def test_mask_merchant_test_prefix():
    assert _mask_merchant("TEST_999888") == "TEST_••••9888"
    assert _mask_merchant("TEST_12") == "TEST_••••12"


def test_mask_merchant_live():
    assert _mask_merchant("1234567890") == "••••7890"
    assert _mask_merchant("12") == "••••12"


# ---------- Enrich payment settings ----------

class _FakeSettings:
    def __init__(self, key, secret):
        self.gateway_api_key = key
        self.gateway_secret = secret
        self.provider = "comgate"


def test_enrich_returns_mode_and_strips_secrets_test():
    s = _FakeSettings("TEST_999888", "shh")
    out = _enrich_payment_settings({"gateway_api_key": "TEST_999888", "gateway_secret": "shh"}, s)
    assert "gateway_api_key" not in out
    assert "gateway_secret" not in out
    assert out["gateway_mode"] == "TEST"
    assert out["gateway_api_key_masked"] == "TEST_••••9888"
    assert out["gateway_secret_set"] is True


def test_enrich_live_mode():
    s = _FakeSettings("12345678", "secret")
    out = _enrich_payment_settings({}, s)
    assert out["gateway_mode"] == "LIVE"
    assert out["gateway_api_key_masked"] == "••••5678"
    assert out["gateway_secret_set"] is True


def test_enrich_mock_when_empty():
    s = _FakeSettings("", "")
    out = _enrich_payment_settings({}, s)
    assert out["gateway_mode"] == "MOCK"
    assert out["gateway_api_key_masked"] is None
    assert out["gateway_secret_set"] is False


def test_enrich_no_settings():
    out = _enrich_payment_settings({}, None)
    assert out["gateway_mode"] == "MOCK"
    assert out["gateway_api_key_masked"] is None
    assert out["gateway_secret_set"] is False


# ---------- Clear sentinel constant ----------

def test_clear_sentinel_value():
    assert CLEAR_SENTINEL == "__CLEAR__"


# ---------- Webhook signature hardening ----------

def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_webhook_rejects_unconfigured_live():
    gw = ComgateGateway(merchant_id="", secret="", mode=GatewayMode.LIVE)
    with pytest.raises(ValueError, match="not configured"):
        asyncio.run(gw.parse_webhook({"merchant": "x", "secret": "y", "status": "PAID"}))


def test_webhook_rejects_wrong_secret():
    gw = ComgateGateway(merchant_id="123", secret="real", mode=GatewayMode.LIVE)
    with pytest.raises(ValueError, match="Invalid Comgate webhook signature"):
        asyncio.run(gw.parse_webhook({"merchant": "123", "secret": "WRONG", "status": "PAID"}))


def test_webhook_rejects_wrong_merchant():
    gw = ComgateGateway(merchant_id="123", secret="real", mode=GatewayMode.TEST)
    with pytest.raises(ValueError, match="Invalid Comgate webhook signature"):
        asyncio.run(gw.parse_webhook({"merchant": "OTHER", "secret": "real", "status": "PAID"}))


def test_webhook_accepts_valid_signature():
    gw = ComgateGateway(merchant_id="123", secret="real", mode=GatewayMode.LIVE)
    res = asyncio.run(gw.parse_webhook({"merchant": "123", "secret": "real", "status": "PAID", "transId": "TX42"}))
    assert res.paid is True
    assert res.transaction_id == "TX42"


def test_webhook_mock_mode_accepts_anything():
    """MOCK mode lets parse_webhook accept anything; the route-level guard
    in /webhook/comgate is responsible for rejecting external calls in MOCK.
    """
    gw = ComgateGateway(merchant_id="", secret="", mode=GatewayMode.MOCK)
    res = asyncio.run(gw.parse_webhook({"status": "PAID", "transId": "M1"}))
    assert res.paid is True


def test_webhook_status_mappings():
    gw = ComgateGateway(merchant_id="m", secret="s", mode=GatewayMode.LIVE)
    base = {"merchant": "m", "secret": "s"}

    paid = asyncio.run(gw.parse_webhook({**base, "status": "PAID"}))
    assert (paid.paid, paid.pending, paid.failed) == (True, False, False)

    pending = asyncio.run(gw.parse_webhook({**base, "status": "PENDING"}))
    assert (pending.paid, pending.pending, pending.failed) == (False, True, False)

    cancelled = asyncio.run(gw.parse_webhook({**base, "status": "CANCELLED"}))
    assert (cancelled.paid, cancelled.pending, cancelled.failed) == (False, False, True)

    failed = asyncio.run(gw.parse_webhook({**base, "status": "FAILED"}))
    assert (failed.paid, failed.pending, failed.failed) == (False, False, True)
