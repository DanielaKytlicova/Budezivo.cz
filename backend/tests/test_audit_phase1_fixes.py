"""
Security audit FÁZE 1-2 regression tests (Budeživo.cz).

Fixes covered:
- P0 #1: unauthenticated `POST /api/plan/setup-columns` DDL/mass-update removed.
- P2 #2: temp passwords use secrets.token_urlsafe, not low-entropy uuid slice.
"""
import os
import re
import pytest


def _read(rel_path: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, rel_path), encoding="utf-8") as f:
        return f.read()


def test_setup_columns_endpoint_removed():
    src = _read("routes/plan.py")
    no_comments = re.sub(r"#.*", "", src)
    assert '@router.post("/setup-columns")' not in no_comments
    assert "ALTER TABLE institutions" not in no_comments
    assert "SET plan='pro_plus'" not in no_comments


def test_no_low_entropy_temp_passwords():
    for rel in ("routes/team.py", "routes/institution_join.py"):
        src = _read(rel)
        assert "uuid.uuid4())[:" not in src, f"low-entropy temp password in {rel}"
        assert "secrets.token_urlsafe" in src, f"secrets generator missing in {rel}"


def test_secrets_generator_entropy():
    import secrets
    samples = {secrets.token_urlsafe(12) for _ in range(1000)}
    assert len(samples) == 1000


def test_byref_email_is_masked():
    """P2 #3: public by-ref lookup must mask the applicant e-mail."""
    from routes.event_payments import _mask_email
    assert _mask_email("jan.novak@skola.cz") == "ja***@skola.cz"
    assert _mask_email("a@x.cz") == "a***@x.cz"
    assert _mask_email(None) is None
    # the route response must use the masking helper, not the raw column
    src = _read("routes/event_payments.py")
    assert '"applicant_email": _mask_email(' in src


def test_prefill_rate_limit_tightened():
    """P2 #4: prefill enumeration cap lowered from 20 to <=6/min."""
    src = _read("routes/public.py")
    assert "PREFILL_MAX_PER_WINDOW = 6" in src
    assert '@limiter.limit("6/minute")' in src


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
