"""Readiness checks for production monitoring.

The lightweight /health endpoint is intentionally dependency-free for
container liveness. This module powers /ready, which checks runtime
dependencies without exposing secret values.
"""
import os
from typing import Mapping, Optional


REQUIRED_ENV_VARS = ("DATABASE_URL", "JWT_SECRET")
OPTIONAL_ENV_VARS = ("RESEND_API_KEY",)


def _is_present(value: object) -> bool:
    return bool(str(value or "").strip())


def check_environment(env: Optional[Mapping[str, object]] = None) -> dict:
    env = env or os.environ
    required = {
        name: "present" if _is_present(env.get(name)) else "missing"
        for name in REQUIRED_ENV_VARS
    }
    optional = {
        name: "present" if _is_present(env.get(name)) else "missing"
        for name in OPTIONAL_ENV_VARS
    }
    missing_required = [name for name, status in required.items() if status == "missing"]
    missing_optional = [name for name, status in optional.items() if status == "missing"]

    return {
        "status": "ok" if not missing_required else "error",
        "required": required,
        "optional": optional,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
    }


def _select_one_statement():
    from sqlalchemy import text

    return text("SELECT 1")


async def check_database(engine, statement_factory=_select_one_statement) -> dict:
    if engine is None:
        return {"status": "error", "detail": "engine_not_configured"}

    try:
        async with engine.begin() as conn:
            await conn.execute(statement_factory())
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": type(exc).__name__}


async def collect_readiness(
    engine,
    env: Optional[Mapping[str, object]] = None,
    statement_factory=_select_one_statement,
) -> dict:
    environment = check_environment(env)
    database = await check_database(engine, statement_factory)

    required_ok = environment["status"] == "ok" and database["status"] == "ok"
    optional_missing = bool(environment["missing_optional"])

    if not required_ok:
        status = "not_ready"
    elif optional_missing:
        status = "degraded"
    else:
        status = "ok"

    return {
        "status": status,
        "ready": required_ok,
        "checks": {
            "environment": environment,
            "database": database,
            "email": {
                "status": "degraded" if "RESEND_API_KEY" in environment["missing_optional"] else "ok",
                "required": False,
            },
        },
    }
