"""Safety helpers for ad-hoc data scripts.

These scripts can create, update, or delete data. They must never run against
the production database by accident.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse


SAFE_APP_ENVS = {"test"}
PRODUCTION_URL_MARKERS = (
    "dhuujqpxazadbbdlwago",
)


def require_test_database_url(script_name: str) -> str:
    """Return TEST_DATABASE_URL only when the runtime is explicitly test-only."""
    app_env = (os.environ.get("APP_ENV") or "").strip().lower()
    if app_env not in SAFE_APP_ENVS:
        raise RuntimeError(
            f"{script_name} requires APP_ENV=test and refuses to run with APP_ENV={app_env or '<unset>'}."
        )

    db_url = (os.environ.get("TEST_DATABASE_URL") or "").strip()
    if not db_url:
        raise RuntimeError(f"{script_name} requires TEST_DATABASE_URL; DATABASE_URL is not accepted.")

    parsed = urlparse(db_url)
    if parsed.scheme not in {"postgresql", "postgresql+asyncpg"}:
        raise RuntimeError(f"{script_name} requires a PostgreSQL TEST_DATABASE_URL.")

    lowered = db_url.lower()
    if any(marker in lowered for marker in PRODUCTION_URL_MARKERS):
        raise RuntimeError(f"{script_name} refuses to run against the production Supabase project.")

    return db_url


def configure_sqlalchemy_test_database(script_name: str) -> str:
    """Set DATABASE_URL for modules that initialize SQLAlchemy from environment."""
    db_url = require_test_database_url(script_name)
    os.environ["DATABASE_URL"] = db_url
    return db_url


def asyncpg_url(db_url: str) -> str:
    """asyncpg expects postgresql://, not SQLAlchemy's postgresql+asyncpg://."""
    return db_url.replace("postgresql+asyncpg://", "postgresql://")


def sqlalchemy_async_url(db_url: str) -> str:
    """SQLAlchemy async engine expects postgresql+asyncpg://."""
    return db_url.replace("postgresql://", "postgresql+asyncpg://")
