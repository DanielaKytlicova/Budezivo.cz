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


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
