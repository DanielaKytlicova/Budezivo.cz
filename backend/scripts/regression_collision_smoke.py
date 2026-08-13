"""Smoke-test collision rules in an isolated regression database.

Guards:
- APP_ENV must be test
- TEST_DATABASE_URL must be present
- the known production Supabase project is refused by scripts.safety
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from scripts.safety import asyncpg_url, configure_sqlalchemy_test_database, require_test_database_url
    from scripts.regression_core_seed import IDS, seed, generated_admin_password, insert_row, hash_seed_password
except ModuleNotFoundError:
    from safety import asyncpg_url, configure_sqlalchemy_test_database, require_test_database_url
    from regression_core_seed import IDS, seed, generated_admin_password, insert_row, hash_seed_password


EXTRA = {
    "room": "11111111-2222-4333-8444-555555555555",
    "room_other": "11111111-2222-4333-8444-555555555556",
    "lecturer_a": "12121212-1212-4121-8121-121212121212",
    "lecturer_b": "13131313-1313-4131-8131-131313131313",
    "program_room": "14141414-1414-4141-8141-141414141414",
    "program_lecturer": "15151515-1515-4151-8151-151515151515",
    "program_blocked": "16161616-1616-4161-8161-161616161616",
    "program_non_parallel": "17171717-1717-4171-8171-171717171717",
    "program_exception": "18181818-1818-4181-8181-181818181818",
    "program_free": "19191919-1919-4191-8191-191919191919",
    "target_reservation": "20202020-2020-4202-8202-202020202020",
    "exception": "21212121-2121-4212-8212-212121212121",
}


def expected_checks() -> tuple[str, ...]:
    return (
        "room_collision_blocked",
        "multilecturer_creation_blocked",
        "blocked_program_blocked",
        "non_parallel_blocked",
        "availability_exception_blocked",
        "free_parallel_allowed",
        "assignment_multilecturer_blocked",
        "availability_view_marks_lecturer_collision",
    )


async def seed_collision_fixture(conn) -> Dict[str, str]:
    await seed(conn, generated_admin_password())

    now = datetime.now(timezone.utc)
    password_hash = hash_seed_password("RegressionCollisionOnly-123")
    base = await conn.fetchrow(
        "SELECT date, time_block FROM reservations WHERE id = $1::uuid",
        IDS["reservation"],
    )
    date = base["date"]
    time_block = base["time_block"]

    for table, column, values in (
        ("availability_exceptions", "id", [EXTRA["exception"]]),
        ("reservations", "id", [EXTRA["target_reservation"]]),
        ("programs", "id", [
            EXTRA["program_room"], EXTRA["program_lecturer"], EXTRA["program_blocked"],
            EXTRA["program_non_parallel"], EXTRA["program_exception"], EXTRA["program_free"],
        ]),
        ("rooms", "id", [EXTRA["room"], EXTRA["room_other"]]),
        ("users", "id", [EXTRA["lecturer_a"], EXTRA["lecturer_b"]]),
    ):
        await conn.execute(
            f'DELETE FROM "{table}" WHERE "{column}" = ANY($1::uuid[])',
            values,
        )

    for room_id, name in ((EXTRA["room"], "Regression Room A"), (EXTRA["room_other"], "Regression Room B")):
        await insert_row(
            conn,
            "rooms",
            {
                "id": room_id,
                "institution_id": IDS["institution"],
                "name": name,
                "capacity": 30,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {"id": "::uuid", "institution_id": "::uuid"},
        )

    for user_id, email, name in (
        (EXTRA["lecturer_a"], "regression-lecturer-a@example.test", "Regression Lecturer A"),
        (EXTRA["lecturer_b"], "regression-lecturer-b@example.test", "Regression Lecturer B"),
    ):
        await insert_row(
            conn,
            "users",
            {
                "id": user_id,
                "institution_id": IDS["institution"],
                "email": email,
                "password_hash": password_hash,
                "name": name,
                "role": "lektor",
                "lecturer_mode": "main",
                "supported_program_ids": json.dumps([
                    IDS["program"],
                    EXTRA["program_room"],
                    EXTRA["program_lecturer"],
                    EXTRA["program_blocked"],
                    EXTRA["program_non_parallel"],
                    EXTRA["program_exception"],
                    EXTRA["program_free"],
                ]),
                "status": "active",
                "gdpr_consent": True,
                "terms_accepted": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "::uuid",
                "institution_id": "::uuid",
                "supported_program_ids": "::jsonb",
            },
        )

    await conn.execute(
        """
        UPDATE programs
        SET allow_parallel = TRUE,
            room_id = $1::uuid,
            collision_resources = $2::json,
            assigned_lecturer_id = $3::uuid,
            collision_lecturer_ids = $4::json,
            updated_at = $5
        WHERE id = $6::uuid
        """,
        EXTRA["room"],
        json.dumps(["room", "lecturer"]),
        EXTRA["lecturer_a"],
        json.dumps([EXTRA["lecturer_b"]]),
        now,
        IDS["program"],
    )
    await conn.execute(
        """
        UPDATE reservations
        SET assigned_lecturer_id = $1::uuid,
            assigned_lecturer_name = 'Regression Lecturer A',
            assigned_lecturer_ids = $2::jsonb,
            updated_at = $3
        WHERE id = $4::uuid
        """,
        EXTRA["lecturer_a"],
        json.dumps([EXTRA["lecturer_a"], EXTRA["lecturer_b"]]),
        now,
        IDS["reservation"],
    )

    async def add_program(program_id: str, name: str, allow_parallel: bool, room_id: str | None, collision_resources: list[str], blocked: list[str], lecturer_id: str | None = None):
        await insert_row(
            conn,
            "programs",
            {
                "id": program_id,
                "institution_id": IDS["institution"],
                "name_cs": name,
                "description_cs": "Collision regression fixture.",
                "duration": 90,
                "age_group": "zs1_7_12",
                "min_capacity": 5,
                "max_capacity": 30,
                "required_lecturers": 1,
                "target_group": "schools",
                "target_groups": json.dumps(["zs1_7_12"]),
                "price": 0,
                "status": "active",
                "is_published": True,
                "requires_approval": False,
                "send_email_notification": False,
                "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "time_blocks": json.dumps([time_block]),
                "end_date": now + timedelta(days=365),
                "min_days_before_booking": 0,
                "max_days_before_booking": 365,
                "preparation_time": 0,
                "cleanup_time": 0,
                "allow_parallel": allow_parallel,
                "collision_resources": json.dumps(collision_resources),
                "collision_lecturer_ids": json.dumps([]),
                "blocked_program_ids": json.dumps(blocked),
                "assigned_lecturer_id": lecturer_id,
                "room_id": room_id,
                "created_by": IDS["admin"],
                "feedback_enabled": True,
                "feedback_questions": json.dumps([]),
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "::uuid",
                "institution_id": "::uuid",
                "target_groups": "::json",
                "available_days": "::text[]",
                "time_blocks": "::json",
                "collision_resources": "::json",
                "collision_lecturer_ids": "::json",
                "blocked_program_ids": "::json",
                "assigned_lecturer_id": "::uuid",
                "room_id": "::uuid",
                "created_by": "::uuid",
                "feedback_questions": "::json",
            },
        )

    await add_program(EXTRA["program_room"], "Regression Room Collision", True, EXTRA["room"], ["room"], [])
    await add_program(EXTRA["program_lecturer"], "Regression Lecturer Collision", True, EXTRA["room_other"], ["lecturer"], [], EXTRA["lecturer_b"])
    await add_program(EXTRA["program_blocked"], "Regression Blocked Program", True, EXTRA["room_other"], [], [IDS["program"]])
    await add_program(EXTRA["program_non_parallel"], "Regression Non Parallel", False, EXTRA["room_other"], [], [])
    await add_program(EXTRA["program_exception"], "Regression Exception Program", True, EXTRA["room_other"], [], [])
    await add_program(EXTRA["program_free"], "Regression Free Parallel", True, EXTRA["room_other"], [], [])

    await insert_row(
        conn,
        "availability_exceptions",
        {
            "id": EXTRA["exception"],
            "institution_id": IDS["institution"],
            "scope_type": "program",
            "scope_id": EXTRA["program_exception"],
            "date": date,
            "start_time": "09:00",
            "end_time": "10:30",
            "reason": "Regression one-off closure",
            "created_by": IDS["admin"],
            "created_at": now,
        },
        {"id": "::uuid", "institution_id": "::uuid", "scope_id": "::uuid", "created_by": "::uuid"},
    )

    await insert_row(
        conn,
        "reservations",
        {
            "id": EXTRA["target_reservation"],
            "institution_id": IDS["institution"],
            "program_id": EXTRA["program_free"],
            "date": date,
            "time_block": time_block,
            "school_name": "Regression Target School",
            "group_type": "zs1_7_12",
            "age_or_class": "4.B",
            "num_students": 18,
            "num_teachers": 2,
            "contact_name": "Regression Target Teacher",
            "contact_email": "regression-target@example.test",
            "contact_phone": "+420000000001",
            "status": "confirmed",
            "gdpr_consent": True,
            "terms_accepted": True,
            "terms_accepted_at": now,
            "terms_accepted_text_version": "v1",
            "created_at": now,
            "updated_at": now,
        },
        {"id": "::uuid", "institution_id": "::uuid", "program_id": "::uuid"},
    )

    return {"date": date, "time_block": time_block}


async def collect_report() -> Dict[str, object]:
    db_url = require_test_database_url("regression_collision_smoke.py")

    import asyncpg

    conn = await asyncpg.connect(asyncpg_url(db_url), statement_cache_size=0)
    try:
        fixture = await seed_collision_fixture(conn)
    finally:
        await conn.close()

    configure_sqlalchemy_test_database("regression_collision_smoke.py")
    from database.supabase import AsyncSessionLocal
    from services.availability_service import evaluate_program_slots
    from services.collision_service import check_booking_collision, check_lecturer_collision_for_assignment

    date = fixture["date"]
    time_block = fixture["time_block"]
    async with AsyncSessionLocal() as db:
        room = await check_booking_collision(db, IDS["institution"], EXTRA["program_room"], date, time_block)
        multilecturer = await check_booking_collision(db, IDS["institution"], EXTRA["program_lecturer"], date, time_block)
        blocked = await check_booking_collision(db, IDS["institution"], EXTRA["program_blocked"], date, time_block)
        non_parallel = await check_booking_collision(db, IDS["institution"], EXTRA["program_non_parallel"], date, time_block)
        exception = await check_booking_collision(db, IDS["institution"], EXTRA["program_exception"], date, time_block)
        free = await check_booking_collision(db, IDS["institution"], EXTRA["program_free"], date, "10:30-12:00")
        assignment = await check_lecturer_collision_for_assignment(
            db, EXTRA["lecturer_b"], IDS["institution"], EXTRA["target_reservation"]
        )
        slots = await evaluate_program_slots(db, IDS["institution"], EXTRA["program_lecturer"], date)

    slot = next((item for item in slots if item.get("time") == time_block), {})
    checks = {
        "room_collision_blocked": bool(room and "Kolize místnosti" in room),
        "multilecturer_creation_blocked": bool(multilecturer and "Kolize lektora" in multilecturer),
        "blocked_program_blocked": bool(blocked and "Kolize programů" in blocked),
        "non_parallel_blocked": bool(non_parallel and "neumožňuje paralelní provoz" in non_parallel),
        "availability_exception_blocked": bool(exception and "jednorázově" in exception),
        "free_parallel_allowed": free is None,
        "assignment_multilecturer_blocked": bool(assignment and "Kolize lektora" in assignment),
        "availability_view_marks_lecturer_collision": slot.get("status") == "blocked_lecturer",
    }
    return {
        "checks": checks,
        "details": {
            "date": date,
            "time_block": time_block,
            "room_collision": room,
            "multilecturer_collision": multilecturer,
            "blocked_program_collision": blocked,
            "non_parallel_collision": non_parallel,
            "exception_collision": exception,
            "assignment_collision": assignment,
            "availability_slot": slot,
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
