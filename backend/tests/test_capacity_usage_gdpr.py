"""
Regression tests for the A10 (event capacity/waitlist), A11 (soft plan limits)
and A12 (GDPR cross-system anonymization) features.

Pure-logic + static source assertions (DB-dependent flows are covered by the
e2e testing agent).
"""
import os
import re
import pytest


def _read(rel_path: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, rel_path), encoding="utf-8") as f:
        return f.read()


# ---- A11: soft-limit quota math ----

def test_quota_block_unlimited():
    from services.usage_service import _quota_block
    q = _quota_block(99, -1)
    assert q["unlimited"] is True
    assert q["over_limit"] is False and q["near_limit"] is False


def test_quota_block_near_and_over():
    from services.usage_service import _quota_block
    near = _quota_block(8, 10)                              # 80%
    assert near["near_limit"] is True and near["over_limit"] is False
    over = _quota_block(10, 10)
    assert over["over_limit"] is True
    half = _quota_block(4, 10)
    assert half["near_limit"] is False and half["over_limit"] is False
    assert half["remaining"] == 6


def test_usage_is_soft_not_enforced():
    """A11 must remain SOFT (architecture-ready but non-blocking)."""
    src = _read("services/usage_service.py")
    assert '"enforced": False' in src


# ---- A10: capacity / waitlist ----

def test_apply_uses_race_safe_capacity():
    src = _read("routes/events.py")
    assert "_resolve_application_status" in src
    assert "pg_advisory_xact_lock" in src
    assert "OCCUPYING_STATUSES" in src
    # waitlist must not count toward occupancy
    assert "'waitlist'" in src


def test_status_update_is_tenant_scoped():
    """A10/IDOR: application status update must filter by institution_id."""
    src = _read("routes/events.py")
    block = src[src.index("def update_application_status"): src.index("def update_application_status") + 900]
    assert "EventApplication.institution_id ==" in block


# ---- A12: GDPR cross-system anonymization ----

def test_gdpr_anonymize_scrubs_related_pii():
    src = _read("routes/gdpr.py")
    assert "update(AuditLog)" in src
    assert "update(RefreshToken)" in src and "revoked=True" in src
    assert "UserCalendarIntegration" in src


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
