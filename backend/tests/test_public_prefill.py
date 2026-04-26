"""
Tests for the public prefill endpoint.

Privacy guarantees:
- Returns 200 even for unknown emails (no enumeration via 404).
- Never returns reservation IDs or program/institution IDs.
- Case-insensitive email match against past confirmed/pending reservations.
- Strict rate-limit (5/min/IP) — covered by slowapi (not unit-tested here).
"""
import os
import uuid

import httpx
import pytest

API = os.environ.get("E2E_API_URL", "http://localhost:8001/api")


def test_prefill_unknown_email_returns_200_not_found():
    r = httpx.get(f"{API}/public/prefill", params={"email": f"neexistuje-{uuid.uuid4()}@x.cz"}, timeout=10.0)
    assert r.status_code == 200
    body = r.json()
    assert body == {"found": False}


def test_prefill_invalid_email_returns_not_found():
    for bad in ["", "no-at-sign", "a@", "x" * 300 + "@y.cz"]:
        r = httpx.get(f"{API}/public/prefill", params={"email": bad}, timeout=10.0)
        assert r.status_code == 200
        assert r.json() == {"found": False}, f"Failed for: {bad!r}"


def test_prefill_returns_safe_subset_only():
    """If a reservation exists for the email, response keys are restricted."""
    test_email = "jana.novakova@zs-botanicka.cz"  # seeded in main agent flow
    r = httpx.get(f"{API}/public/prefill", params={"email": test_email}, timeout=10.0)
    assert r.status_code == 200
    body = r.json()
    if not body.get("found"):
        pytest.skip("No seed reservation present in this DB")
    data = body["data"]
    allowed_keys = {
        "school_name", "contact_name", "contact_phone", "group_type",
        "age_or_class", "num_students", "num_teachers", "special_requirements",
    }
    extra = set(data.keys()) - allowed_keys
    assert not extra, f"Prefill leaked unexpected fields: {extra}"
    # Ensure no IDs were exposed
    for k, v in data.items():
        assert "id" not in k
        if isinstance(v, str):
            try:
                uuid.UUID(v)
                pytest.fail(f"Prefill leaked a UUID in field {k!r}: {v}")
            except (ValueError, AttributeError):
                pass


def test_prefill_case_insensitive():
    """Same email in different case should yield the same prefill."""
    a = httpx.get(f"{API}/public/prefill", params={"email": "jana.novakova@zs-botanicka.cz"}, timeout=10.0).json()
    b = httpx.get(f"{API}/public/prefill", params={"email": "Jana.NOVAKOVA@ZS-Botanicka.CZ"}, timeout=10.0).json()
    if not a.get("found"):
        pytest.skip("No seed reservation present")
    assert a == b
