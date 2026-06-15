"""
Regression test for VS (variable symbol) uniqueness within an institution.
A duplicate VS could mis-link a manual/QR bank transfer to the wrong application.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from routes import events


def _result(scalar_value):
    """Build a fake SQLAlchemy Result whose scalar_one_or_none returns value."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = scalar_value
    return r


def test_vs_format_is_10_digits():
    vs = events._generate_variable_symbol()
    assert vs.isdigit() and len(vs) == 10


def test_unique_vs_skips_collision(monkeypatch):
    # Force deterministic candidates: first collides, second is free.
    seq = iter(["1111111111", "2222222222"])
    monkeypatch.setattr(events, "_generate_variable_symbol", lambda: next(seq))

    db = MagicMock()
    # 1st DB check -> existing row (collision); 2nd -> None (free)
    db.execute = AsyncMock(side_effect=[_result("existing-app-id"), _result(None)])

    vs = asyncio.run(events._generate_unique_variable_symbol(db, "inst-uuid"))
    assert vs == "2222222222"
    assert db.execute.await_count == 2


def test_unique_vs_returns_first_when_free(monkeypatch):
    monkeypatch.setattr(events, "_generate_variable_symbol", lambda: "3333333333")
    db = MagicMock()
    db.execute = AsyncMock(return_value=_result(None))
    vs = asyncio.run(events._generate_unique_variable_symbol(db, "inst-uuid"))
    assert vs == "3333333333"
    assert db.execute.await_count == 1


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
