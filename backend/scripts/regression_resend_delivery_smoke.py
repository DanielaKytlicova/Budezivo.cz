"""Smoke-test Resend webhook persistence in an isolated regression database.

Guards:
- APP_ENV must be test
- TEST_DATABASE_URL must be present
- the known production Supabase project is refused by scripts.safety

Run after alembic upgrade head and regression_core_seed.py.
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import timezone
from pathlib import Path
from typing import Dict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from scripts.safety import asyncpg_url, configure_sqlalchemy_test_database, require_test_database_url
    from scripts.regression_core_seed import IDS, SCHOOL_EMAIL, seed, generated_admin_password
except ModuleNotFoundError:
    from safety import asyncpg_url, configure_sqlalchemy_test_database, require_test_database_url
    from regression_core_seed import IDS, SCHOOL_EMAIL, seed, generated_admin_password


PROVIDER_EMAIL_ID = "resend_regression_email_1"
SVIX_ID = "msg_regression_resend_bounce_1"
BOUNCE_REASON = "Regression mailbox does not exist"


def bounced_payload() -> dict:
    return {
        "type": "email.bounced",
        "created_at": "2026-08-13T10:00:00Z",
        "data": {
            "email_id": PROVIDER_EMAIL_ID,
            "to": [SCHOOL_EMAIL],
            "bounce": {
                "type": "Permanent",
                "message": BOUNCE_REASON,
            },
        },
    }


def expected_checks() -> tuple[str, ...]:
    return (
        "core_seed_present",
        "webhook_event_recorded",
        "duplicate_is_idempotent",
        "recipient_marked_bounced",
        "central_contact_marked_bounced",
        "school_contact_marked_invalid",
        "permanent_suppression_visible",
    )


async def reset_delivery_state(conn) -> None:
    await conn.execute(
        """
        UPDATE mailing_campaign_recipients
        SET email_provider_id = $1,
            status = 'sent',
            failure_reason = NULL,
            delivery_status = 'unknown',
            delivery_event_at = NULL
        WHERE id = $2::uuid
        """,
        PROVIDER_EMAIL_ID,
        IDS["mailing_recipient"],
    )
    await conn.execute(
        """
        UPDATE contacts
        SET deliverability_status = 'unknown',
            deliverability_reason = NULL,
            deliverability_updated_at = NULL
        WHERE id = $1::uuid
        """,
        IDS["contact"],
    )
    await conn.execute(
        """
        UPDATE school_contacts
        SET status = 'active',
            email_validation_error = NULL,
            last_email_bounced = FALSE,
            deliverability_status = 'unknown',
            deliverability_reason = NULL,
            deliverability_updated_at = NULL
        WHERE id = $1::uuid
        """,
        IDS["school_contact"],
    )
    await conn.execute("DELETE FROM resend_webhook_events WHERE svix_id = $1", SVIX_ID)


async def collect_rows(conn) -> Dict[str, object]:
    recipient = await conn.fetchrow(
        """
        SELECT delivery_status, failure_reason, delivery_event_at
        FROM mailing_campaign_recipients
        WHERE id = $1::uuid
        """,
        IDS["mailing_recipient"],
    )
    contact = await conn.fetchrow(
        """
        SELECT deliverability_status, deliverability_reason, deliverability_updated_at
        FROM contacts
        WHERE id = $1::uuid
        """,
        IDS["contact"],
    )
    school_contact = await conn.fetchrow(
        """
        SELECT status, email_validation_error, last_email_bounced,
               deliverability_status, deliverability_reason, deliverability_updated_at
        FROM school_contacts
        WHERE id = $1::uuid
        """,
        IDS["school_contact"],
    )
    webhook_count = await conn.fetchval(
        "SELECT count(*) FROM resend_webhook_events WHERE svix_id = $1",
        SVIX_ID,
    )
    return {
        "recipient": dict(recipient) if recipient else None,
        "contact": dict(contact) if contact else None,
        "school_contact": dict(school_contact) if school_contact else None,
        "webhook_count": webhook_count,
    }


async def run_webhook_update() -> tuple[dict, dict]:
    configure_sqlalchemy_test_database("regression_resend_delivery_smoke.py")
    from database.supabase import AsyncSessionLocal
    from services.resend_delivery import apply_delivery_update, delivery_update_from_payload

    if AsyncSessionLocal is None:
        raise RuntimeError("SQLAlchemy test database session is not configured.")

    delivery_update = delivery_update_from_payload(bounced_payload())
    async with AsyncSessionLocal() as db:
        first = await apply_delivery_update(db, delivery_update, svix_id=SVIX_ID)
    async with AsyncSessionLocal() as db:
        duplicate = await apply_delivery_update(db, delivery_update, svix_id=SVIX_ID)
    return first, duplicate


async def collect_report() -> Dict[str, object]:
    db_url = require_test_database_url("regression_resend_delivery_smoke.py")

    import asyncpg

    conn = await asyncpg.connect(asyncpg_url(db_url), statement_cache_size=0)
    try:
        await seed(conn, generated_admin_password())
        await reset_delivery_state(conn)
        first, duplicate = await run_webhook_update()
        rows = await collect_rows(conn)
    finally:
        await conn.close()

    recipient = rows["recipient"] or {}
    contact = rows["contact"] or {}
    school_contact = rows["school_contact"] or {}
    checks = {
        "core_seed_present": bool(recipient and contact and school_contact),
        "webhook_event_recorded": rows["webhook_count"] == 1,
        "duplicate_is_idempotent": duplicate.get("duplicate") is True and rows["webhook_count"] == 1,
        "recipient_marked_bounced": (
            first.get("matched_recipients") == 1
            and recipient.get("delivery_status") == "bounced_hard"
            and recipient.get("failure_reason") == BOUNCE_REASON
            and recipient.get("delivery_event_at") is not None
        ),
        "central_contact_marked_bounced": (
            contact.get("deliverability_status") == "bounced_hard"
            and contact.get("deliverability_reason") == BOUNCE_REASON
            and contact.get("deliverability_updated_at") is not None
        ),
        "school_contact_marked_invalid": (
            school_contact.get("status") == "invalid"
            and school_contact.get("last_email_bounced") is True
            and school_contact.get("email_validation_error") == BOUNCE_REASON
        ),
        "permanent_suppression_visible": (
            school_contact.get("deliverability_status") == "bounced_hard"
            and school_contact.get("deliverability_reason") == BOUNCE_REASON
            and school_contact.get("deliverability_updated_at") is not None
        ),
    }
    return {
        "checks": checks,
        "details": {
            "provider_email_id": PROVIDER_EMAIL_ID,
            "svix_id": SVIX_ID,
            "recipient_email": SCHOOL_EMAIL,
            "first_result": first,
            "duplicate_result": duplicate,
        },
        "status": "ok" if all(checks.values()) else "attention_required",
    }


async def main() -> None:
    report = await collect_report()
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
