#!/usr/bin/env python3
"""Concurrency smoke for public booking overbooking protection.

Runs against TEST_DATABASE_URL only. It seeds isolated fixtures, calls the real
FastAPI public booking endpoint concurrently through ASGI, and verifies that a
program with max_concurrent_bookings=N creates exactly N active reservations.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.regression_core_seed import insert_row
from scripts.safety import asyncpg_url, configure_sqlalchemy_test_database, require_test_database_url


SCRIPT_NAME = "regression_public_booking_concurrency.py"
PREFIX = "[PUBLIC BOOKING RACE TEST]"
TEST_NAMESPACE = uuid.UUID("afd3aa7b-f6c4-4ad3-908f-2f11fbfbb90a")
INSTITUTION_ID = str(uuid.uuid5(TEST_NAMESPACE, "institution"))
ADMIN_ID = str(uuid.uuid5(TEST_NAMESPACE, "admin"))
SCHOOL_ID = str(uuid.uuid5(TEST_NAMESPACE, "school"))
SCHOOL_CONTACT_ID = str(uuid.uuid5(TEST_NAMESPACE, "school-contact"))
PROGRAM_IDS = {
    1: str(uuid.uuid5(TEST_NAMESPACE, "program-limit-1")),
    2: str(uuid.uuid5(TEST_NAMESPACE, "program-limit-2")),
}
DATE = "2026-09-15"
TIME_BLOCK = "10:00-11:00"
CONTACT_EMAIL = "public-booking-race@budezivo.cz"
ADMIN_EMAIL = "public-booking-race-admin@budezivo.cz"


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((percent / 100) * (len(ordered) - 1))))
    return ordered[index]


async def cleanup(conn: asyncpg.Connection) -> None:
    program_ids = list(PROGRAM_IDS.values())
    has_email_logs = await conn.fetchval("SELECT to_regclass('public.email_logs') IS NOT NULL")
    if has_email_logs:
        await conn.execute("DELETE FROM email_logs WHERE institution_id = $1::uuid", INSTITUTION_ID)
    await conn.execute("DELETE FROM reservations WHERE institution_id = $1::uuid", INSTITUTION_ID)
    await conn.execute("DELETE FROM school_contacts WHERE institution_id = $1::uuid", INSTITUTION_ID)
    await conn.execute("DELETE FROM schools WHERE institution_id = $1::uuid", INSTITUTION_ID)
    await conn.execute("DELETE FROM programs WHERE id = ANY($1::uuid[])", program_ids)
    await conn.execute("DELETE FROM users WHERE institution_id = $1::uuid", INSTITUTION_ID)
    await conn.execute("DELETE FROM institutions WHERE id = $1::uuid", INSTITUTION_ID)


async def seed(conn: asyncpg.Connection) -> None:
    now = datetime.now(timezone.utc)
    notification_settings = {
        "customer": {
            "reservation_created": False,
            "reservation_confirmed": False,
            "reservation_cancelled": False,
            "visit_reminder": False,
            "event_registration_received": False,
            "event_registration_confirmed": False,
            "event_registration_cancelled": False,
        },
        "admin": {"new_reservation": False, "recipient_user_ids": []},
    }
    await insert_row(
        conn,
        "institutions",
        {
            "id": INSTITUTION_ID,
            "name": f"{PREFIX} Institution",
            "type": "gallery",
            "country": "CZ",
            "email": ADMIN_EMAIL,
            "plan": "pro",
            "plan_status": "active",
            "programs_limit": 50,
            "bookings_monthly_limit": 500,
            "default_available_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "default_time_blocks": json.dumps([{"start": "10:00", "end": "11:00"}]),
            "notification_settings": json.dumps(notification_settings),
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "::uuid",
            "default_time_blocks": "::json",
            "notification_settings": "::json",
        },
    )
    await insert_row(
        conn,
        "users",
        {
            "id": ADMIN_ID,
            "institution_id": INSTITUTION_ID,
            "email": ADMIN_EMAIL,
            "password_hash": "not-used",
            "name": "Race Test Admin",
            "role": "admin",
            "status": "active",
            "gdpr_consent": True,
            "gdpr_consent_date": now,
            "terms_accepted": True,
            "created_at": now,
            "updated_at": now,
        },
        {"id": "::uuid", "institution_id": "::uuid"},
    )
    await insert_row(
        conn,
        "schools",
        {
            "id": SCHOOL_ID,
            "institution_id": INSTITUTION_ID,
            "name": f"{PREFIX} School",
            "contact_person": "Race Teacher",
            "email": CONTACT_EMAIL,
            "phone": "+420 600 111 222",
            "source": "reservation",
            "booking_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {"id": "::uuid", "institution_id": "::uuid"},
    )
    await insert_row(
        conn,
        "school_contacts",
        {
            "id": SCHOOL_CONTACT_ID,
            "school_id": SCHOOL_ID,
            "institution_id": INSTITUTION_ID,
            "email": CONTACT_EMAIL,
            "name": "Race Teacher",
            "phone": "+420 600 111 222",
            "is_primary": True,
            "status": "active",
            "deliverability_status": "unknown",
            "created_at": now,
            "updated_at": now,
        },
        {"id": "::uuid", "school_id": "::uuid", "institution_id": "::uuid"},
    )

    for limit, program_id in PROGRAM_IDS.items():
        await insert_row(
            conn,
            "programs",
            {
                "id": program_id,
                "institution_id": INSTITUTION_ID,
                "name_cs": f"{PREFIX} Limit {limit}",
                "name_en": f"{PREFIX} Limit {limit}",
                "description_cs": "Concurrency regression fixture",
                "description_en": "Concurrency regression fixture",
                "duration": 60,
                "age_group": "zs1_7_12",
                "min_capacity": 1,
                "max_capacity": 30,
                "required_lecturers": 1,
                "target_group": "schools",
                "target_groups": json.dumps(["zs1_7_12"]),
                "status": "active",
                "is_published": True,
                "send_email_notification": False,
                "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "time_blocks": json.dumps([TIME_BLOCK]),
                "min_days_before_booking": 1,
                "max_days_before_booking": 365,
                "allow_parallel": True,
                "max_concurrent_bookings": limit,
                "collision_resources": json.dumps([]),
                "collision_lecturer_ids": json.dumps([]),
                "blocked_program_ids": json.dumps([]),
                "created_by": ADMIN_ID,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "::uuid",
                "institution_id": "::uuid",
                "target_groups": "::json",
                "time_blocks": "::json",
                "collision_resources": "::json",
                "collision_lecturer_ids": "::json",
                "blocked_program_ids": "::json",
                "created_by": "::uuid",
            },
        )


async def reset_reservations(conn: asyncpg.Connection, limit: int) -> None:
    await conn.execute(
        """
        DELETE FROM reservations
        WHERE institution_id = $1::uuid AND program_id = $2::uuid
        """,
        INSTITUTION_ID,
        PROGRAM_IDS[limit],
    )
    await conn.execute(
        "UPDATE schools SET booking_count = 0 WHERE id = $1::uuid",
        SCHOOL_ID,
    )


def booking_payload(program_id: str, idx: int) -> dict[str, Any]:
    return {
        "program_id": program_id,
        "date": DATE,
        "time_block": TIME_BLOCK,
        "school_name": f"{PREFIX} School",
        "group_type": "zs1_7_12",
        "age_or_class": "4.A",
        "num_students": 20,
        "num_teachers": 2,
        "special_requirements": f"concurrency attempt {idx}",
        "contact_name": "Race Teacher",
        "contact_email": CONTACT_EMAIL,
        "contact_phone": "+420 600 111 222",
        "gdpr_consent": True,
        "marketing_consent": False,
        "terms_accepted": True,
        "terms_accepted_text_version": "v1",
    }


async def active_reservations(conn: asyncpg.Connection, limit: int) -> int:
    return int(await conn.fetchval(
        """
        SELECT count(*)
        FROM reservations
        WHERE institution_id = $1::uuid
          AND program_id = $2::uuid
          AND date = $3
          AND time_block = $4
          AND status != 'cancelled'
        """,
        INSTITUTION_ID,
        PROGRAM_IDS[limit],
        DATE,
        TIME_BLOCK,
    ) or 0)


async def run_burst(client, conn: asyncpg.Connection, limit: int, requests: int) -> dict[str, Any]:
    await reset_reservations(conn, limit)
    url = f"/api/bookings/public/{INSTITUTION_ID}"
    latencies: list[float] = []

    async def one(idx: int) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            response = await client.post(url, json=booking_payload(PROGRAM_IDS[limit], idx), timeout=30)
            elapsed = time.perf_counter() - started
            latencies.append(elapsed)
            return {
                "status_code": response.status_code,
                "body": response.text[:300],
                "elapsed": elapsed,
            }
        except Exception as exc:  # noqa: BLE001
            elapsed = time.perf_counter() - started
            latencies.append(elapsed)
            return {
                "status_code": "exception",
                "body": f"{type(exc).__name__}: {exc}",
                "elapsed": elapsed,
            }

    results = await asyncio.gather(*(one(i) for i in range(requests)))
    active_count = await active_reservations(conn, limit)
    status_counts: dict[str, int] = {}
    for result in results:
        key = str(result["status_code"])
        status_counts[key] = status_counts.get(key, 0) + 1

    success = status_counts.get("200", 0)
    business_rejections = sum(status_counts.get(str(code), 0) for code in (400, 404, 409, 422))
    technical_failures = sum(
        count for status, count in status_counts.items()
        if status == "exception" or (status.isdigit() and int(status) >= 500)
    )
    expected_ok = active_count == limit and success == limit and technical_failures == 0
    return {
        "limit": limit,
        "requests": requests,
        "success": success,
        "business_rejections": business_rejections,
        "technical_failures": technical_failures,
        "status_counts": status_counts,
        "active_reservations": active_count,
        "duplicate_or_overbooked": active_count > limit,
        "passed": expected_ok,
        "latency_ms": {
            "p50": round(statistics.median(latencies) * 1000, 2) if latencies else 0,
            "p95": round(percentile(latencies, 95) * 1000, 2),
            "p99": round(percentile(latencies, 99) * 1000, 2),
            "max": round(max(latencies) * 1000, 2) if latencies else 0,
        },
        "sample_failures": [
            r for r in results
            if r["status_code"] == "exception"
            or (
                str(r["status_code"]).isdigit()
                and (int(r["status_code"]) >= 500 or int(r["status_code"]) in {400, 404, 422})
            )
        ][:3],
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", default="10,25,50,100", help="Comma-separated burst sizes.")
    args = parser.parse_args()
    request_counts = [int(item.strip()) for item in args.requests.split(",") if item.strip()]

    configure_sqlalchemy_test_database(SCRIPT_NAME)
    db_url = require_test_database_url(SCRIPT_NAME)
    conn = await asyncpg.connect(asyncpg_url(db_url))
    try:
        await cleanup(conn)
        await seed(conn)

        from httpx import ASGITransport, AsyncClient

        os.environ.setdefault("JWT_SECRET", "test-public-booking-concurrency-secret")
        import routes.bookings as booking_routes

        booking_routes._booking_limiter.enabled = False
        from main import app

        report = {
            "status": "ok",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "institution_id": INSTITUTION_ID,
            "date": DATE,
            "time_block": TIME_BLOCK,
            "checks": [],
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            for limit in (1, 2):
                for requests in request_counts:
                    report["checks"].append(await run_burst(client, conn, limit, requests))

        failures = [check for check in report["checks"] if not check["passed"]]
        if failures:
            report["status"] = "attention_required"
            report["failures"] = failures

        print(json.dumps(report, ensure_ascii=False, indent=2))
        print("\n=== Public booking concurrency summary ===")
        print(f"Status: {report['status']} | checks {len(report['checks']) - len(failures)}/{len(report['checks'])} passed")
        for check in report["checks"]:
            print(
                f"- limit={check['limit']} requests={check['requests']}: "
                f"success={check['success']} rejections={check['business_rejections']} "
                f"5xx/exc={check['technical_failures']} active={check['active_reservations']} "
                f"p95={check['latency_ms']['p95']}ms passed={check['passed']}"
            )
    finally:
        await cleanup(conn)
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
