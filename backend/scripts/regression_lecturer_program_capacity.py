#!/usr/bin/env python3
"""Isolated lecturer/program collision regression for the pilot test database.

This script seeds only prefixed test fixtures into an existing test institution
and verifies the real collision/availability services against deterministic
scenarios. It refuses production databases through scripts.safety.
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from database.models import Program
from database.supabase import AsyncSessionLocal
from scripts.regression_core_seed import hash_seed_password, insert_row
from scripts.safety import (
    asyncpg_url,
    configure_sqlalchemy_test_database,
    require_test_database_url,
)
from services.availability_service import STATUS_BLOCKED_EXCEPTION, evaluate_program_slots
from services.collision_service import check_booking_collision, check_lecturer_collision_for_assignment
from services.lecturer_assignment_service import pick_main_lecturer


SCRIPT_NAME = "regression_lecturer_program_capacity.py"
PREFIX = "[KOLIZE TEST]"
TARGET_INSTITUTION_NAME = "Galerie U Zlatého kohouta"
TARGET_ADMIN_EMAIL = "galerie@budezivo.cz"
SCENARIO_DATE = "2026-09-15"  # Tuesday, inside normal weekday availability.
EXCEPTION_DATE = "2026-09-16"
MAIN_TIME = "10:00-11:00"
PASSWORD = "RegressionOnly-123"
TEST_NAMESPACE = uuid.UUID("4c116f3f-f18a-4e10-bd53-c28cc9cc3f8b")


def stable_id(key: str) -> str:
    return str(uuid.uuid5(TEST_NAMESPACE, key))


LECTURERS = {
    "L1": {"name": "Anna Dvořáková", "email": "kolize-test-anna@example.test", "programs": ["P01", "P02", "P03", "P07"]},
    "L2": {"name": "Petr Kučera", "email": "kolize-test-petr@example.test", "programs": ["P01", "P04", "P05", "P08"]},
    "L3": {"name": "Klára Nováková", "email": "kolize-test-klara@example.test", "programs": ["P02", "P04", "P06", "P09", "P10"]},
    "L4": {"name": "David Marek", "email": "kolize-test-david@example.test", "programs": ["P03", "P05", "P06", "P10", "P11"]},
    "L5": {"name": "Eliška Černá", "email": "kolize-test-eliska@example.test", "programs": ["P01", "P06", "P07", "P11", "P12"]},
}


ROOMS = {
    "R1": "Ateliér",
    "R2": "Hlavní výstavní sál",
    "R3": "Edukační místnost",
    "R4": "Přednáškový sál",
}


PROGRAMS = {
    "P01": {"name": "P01 - Výtvarná laboratoř", "lecturers": ["L1", "L2", "L5"], "room": "R1", "limit": 2, "resources": ["lecturer"]},
    "P02": {"name": "P02 - Galerie hrou", "lecturers": ["L1", "L3"], "room": "R2", "limit": 1, "resources": ["lecturer"]},
    "P03": {"name": "P03 - Barvy a světlo", "lecturers": ["L1", "L4"], "room": "R3", "limit": 1, "resources": ["lecturer"]},
    "P04": {"name": "P04 - Experimentální dílna", "lecturers": ["L2", "L3"], "room": "R4", "limit": 2, "resources": ["lecturer"]},
    "P05": {"name": "P05 - Příběh předmětu", "lecturers": ["L2", "L4"], "room": "R1", "limit": 1, "resources": ["room"]},
    "P06": {"name": "P06 - Technologie kolem nás", "lecturers": ["L3", "L4", "L5"], "room": "R2", "limit": 2, "resources": ["lecturer"]},
    "P07": {"name": "P07 - Malý kurátor", "lecturers": ["L1", "L5"], "room": "R3", "limit": 1, "resources": ["lecturer"]},
    "P08": {"name": "P08 - Historická dílna", "lecturers": ["L2"], "room": "R4", "limit": 1, "resources": ["lecturer"]},
    "P09": {"name": "P09 - Architektura galerie", "lecturers": ["L3"], "room": "R1", "limit": 1, "resources": ["lecturer"]},
    "P10": {"name": "P10 - Materiálová laboratoř", "lecturers": ["L3", "L4"], "room": "R1", "limit": 2, "resources": ["lecturer", "room"]},
    "P11": {"name": "P11 - Tvořivá laboratoř", "lecturers": ["L4", "L5"], "room": "R2", "limit": 1, "resources": ["lecturer"]},
    "P12": {"name": "P12 - Speciální workshop", "lecturers": ["L5"], "room": "R3", "limit": 1, "resources": ["lecturer"]},
}


@dataclass
class ScenarioResult:
    id: str
    name: str
    expected: str
    actual: str
    passed: bool
    expected_reason: Optional[str] = None
    actual_reason: Optional[str] = None
    raw_message: Optional[str] = None
    diagnostic: Optional[str] = None


async def find_target_institution(conn) -> tuple[str, Optional[str]]:
    row = await conn.fetchrow(
        """
        SELECT i.id::text AS institution_id,
               COALESCE(
                 (SELECT u.id::text FROM users u
                  WHERE u.institution_id = i.id AND u.email = $1
                  LIMIT 1),
                 (SELECT u.id::text FROM users u
                  WHERE u.institution_id = i.id
                    AND u.role IN ('admin', 'spravce')
                  ORDER BY u.created_at NULLS LAST
                  LIMIT 1)
               ) AS admin_id
        FROM institutions i
        WHERE i.name = $2
           OR EXISTS (
             SELECT 1 FROM users u WHERE u.institution_id = i.id AND u.email = $1
           )
        LIMIT 1
        """,
        TARGET_ADMIN_EMAIL,
        TARGET_INSTITUTION_NAME,
    )
    if not row:
        raise RuntimeError(
            f"Target test institution not found: {TARGET_INSTITUTION_NAME!r} / {TARGET_ADMIN_EMAIL!r}"
        )
    return row["institution_id"], row["admin_id"]


def lecturer_id(code: str) -> str:
    return stable_id(f"lecturer:{code}")


def room_id(code: str) -> str:
    return stable_id(f"room:{code}")


def program_id(code: str) -> str:
    return stable_id(f"program:{code}")


def reservation_id(key: str) -> str:
    return stable_id(f"reservation:{key}")


def exception_id(key: str) -> str:
    return stable_id(f"exception:{key}")


async def cleanup(conn) -> None:
    """Remove only fixtures owned by this regression suite."""
    await conn.execute(
        """
        DELETE FROM availability_exceptions
        WHERE id = ANY($1::uuid[]) OR reason LIKE $2
        """,
        [exception_id("program-p05")],
        f"{PREFIX}%",
    )
    await conn.execute(
        """
        DELETE FROM reservations
        WHERE id = ANY($1::uuid[])
           OR school_name LIKE $2
           OR contact_email LIKE 'kolize-test-%@example.test'
        """,
        [reservation_id(f"res-{idx}") for idx in range(1, 80)],
        f"{PREFIX}%",
    )
    await conn.execute(
        "DELETE FROM programs WHERE id = ANY($1::uuid[]) OR name_cs LIKE $2",
        [program_id(code) for code in PROGRAMS],
        f"{PREFIX}%",
    )
    await conn.execute(
        "DELETE FROM rooms WHERE id = ANY($1::uuid[]) OR name LIKE $2",
        [room_id(code) for code in ROOMS],
        f"{PREFIX}%",
    )
    await conn.execute(
        """
        DELETE FROM users
        WHERE id = ANY($1::uuid[]) OR email LIKE 'kolize-test-%@example.test'
        """,
        [lecturer_id(code) for code in LECTURERS],
    )


async def seed_fixtures(conn, institution_id: str, admin_id: Optional[str]) -> None:
    now = datetime.now(timezone.utc)
    password_hash = hash_seed_password(PASSWORD)

    program_ids_by_code = {code: program_id(code) for code in PROGRAMS}

    for code, lecturer in LECTURERS.items():
        await insert_row(
            conn,
            "users",
            {
                "id": lecturer_id(code),
                "institution_id": institution_id,
                "email": lecturer["email"],
                "password_hash": password_hash,
                "name": f"{PREFIX} {lecturer['name']}",
                "role": "lektor",
                "lecturer_mode": "main",
                "supported_program_ids": json.dumps([program_ids_by_code[p] for p in lecturer["programs"]]),
                "learning_program_ids": json.dumps([]),
                "status": "active",
                "gdpr_consent": True,
                "gdpr_consent_date": now,
                "terms_accepted": True,
                "created_at": now,
                "updated_at": now,
            },
            {"id": "uuid", "institution_id": "uuid", "supported_program_ids": "jsonb", "learning_program_ids": "jsonb"},
        )

    for code, name in ROOMS.items():
        await insert_row(
            conn,
            "rooms",
            {
                "id": room_id(code),
                "institution_id": institution_id,
                "name": f"{PREFIX} {name}",
                "capacity": 30,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {"id": "uuid", "institution_id": "uuid"},
        )

    for code, program in PROGRAMS.items():
        lecturer_ids = [lecturer_id(lc) for lc in program["lecturers"]]
        await insert_row(
            conn,
            "programs",
            {
                "id": program_id(code),
                "institution_id": institution_id,
                "name_cs": f"{PREFIX} {program['name']}",
                "name_en": f"{PREFIX} {program['name']}",
                "description_cs": f"{PREFIX} collision regression fixture",
                "duration": 60,
                "age_group": "zs1_7_12",
                "min_capacity": 5,
                "max_capacity": 30,
                "required_lecturers": 1,
                "target_group": "schools",
                "target_groups": json.dumps(["zs1_7_12"]),
                "status": "active",
                "is_published": True,
                "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "time_blocks": json.dumps(["09:00-10:00", "09:59-11:00", "10:00-11:00", "10:30-11:30", "11:00-12:00"]),
                "allow_parallel": True,
                "max_concurrent_bookings": program["limit"],
                "collision_resources": json.dumps(program["resources"]),
                "collision_lecturer_ids": json.dumps(lecturer_ids),
                "blocked_program_ids": json.dumps([]),
                "assigned_lecturer_id": lecturer_ids[0],
                "room_id": room_id(program["room"]),
                "created_by": admin_id,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "uuid",
                "institution_id": "uuid",
                "target_groups": "json",
                "time_blocks": "json",
                "collision_resources": "json",
                "collision_lecturer_ids": "json",
                "blocked_program_ids": "json",
                "assigned_lecturer_id": "uuid",
                "room_id": "uuid",
                "created_by": "uuid",
            },
        )


async def delete_scenario_reservations(conn) -> None:
    await conn.execute(
        """
        DELETE FROM reservations
        WHERE school_name LIKE $1 OR contact_email LIKE 'kolize-test-%@example.test'
        """,
        f"{PREFIX}%",
    )


async def add_reservation(
    conn,
    key: str,
    institution_id: str,
    program_code: str,
    lecturer_code: Optional[str],
    time_block: str = MAIN_TIME,
    date: str = SCENARIO_DATE,
) -> str:
    now = datetime.now(timezone.utc)
    lecturer_uuid = lecturer_id(lecturer_code) if lecturer_code else None
    lecturer_ids = [lecturer_uuid] if lecturer_uuid else []
    rid = reservation_id(key)
    await insert_row(
        conn,
        "reservations",
        {
            "id": rid,
            "institution_id": institution_id,
            "program_id": program_id(program_code),
            "date": date,
            "time_block": time_block,
            "school_name": f"{PREFIX} škola",
            "group_type": "zs1_7_12",
            "age_or_class": "4.A",
            "num_students": 20,
            "num_teachers": 2,
            "contact_name": f"{PREFIX} pedagog",
            "contact_email": f"kolize-test-{key}@example.test",
            "contact_phone": "+420 600 000 000",
            "status": "confirmed",
            "assigned_lecturer_id": lecturer_uuid,
            "assigned_lecturer_name": LECTURERS[lecturer_code]["name"] if lecturer_code else None,
            "assigned_lecturer_at": now if lecturer_code else None,
            "assigned_lecturer_ids": json.dumps(lecturer_ids),
            "assignment_source": "manual_admin" if lecturer_code else "unassigned",
            "gdpr_consent": True,
            "gdpr_consent_date": now,
            "terms_accepted": True,
            "terms_accepted_at": now,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "uuid",
            "institution_id": "uuid",
            "program_id": "uuid",
            "assigned_lecturer_id": "uuid",
            "assigned_lecturer_ids": "jsonb",
        },
    )
    return rid


async def add_exception(conn, institution_id: str, admin_id: Optional[str]) -> None:
    await insert_row(
        conn,
        "availability_exceptions",
        {
            "id": exception_id("program-p05"),
            "institution_id": institution_id,
            "scope_type": "program",
            "scope_id": program_id("P05"),
            "date": EXCEPTION_DATE,
            "start_time": "10:00",
            "end_time": "11:00",
            "reason": f"{PREFIX} programová výjimka",
            "created_by": admin_id,
            "created_at": datetime.now(timezone.utc),
        },
        {"id": "uuid", "institution_id": "uuid", "scope_id": "uuid", "created_by": "uuid"},
    )


def classify_message(message: Optional[str]) -> str:
    if not message:
        return "allow"
    lowered = message.lower()
    if "souběžn" in lowered or "kapacita" in lowered:
        return "max_concurrent"
    if "kolize lektora" in lowered:
        return "lecturer_collision"
    if "kolize místnosti" in lowered:
        return "room_collision"
    if "jednorázově" in lowered or "výjimka" in lowered or "uzavřen" in lowered:
        return "availability_exception"
    if "nedostatek lektor" in lowered or "žádný vybraný lektor" in lowered:
        return "qualified_lecturer_unavailable"
    if "paralelní" in lowered:
        return "parallel_blocked"
    if "blokace" in lowered:
        return "blocked_program"
    return "other_block"


def diagnostic_for(expected: str, expected_reason: Optional[str], actual: str, actual_reason: str) -> Optional[str]:
    if expected == "allow" and actual == "blocked":
        return "A_FALSE_POSITIVE"
    if expected == "blocked" and actual == "allow":
        if expected_reason == "unsupported_lecturer":
            return "D_LECTURER_QUALIFICATION_NOT_ENFORCED"
        return "B_FALSE_NEGATIVE"
    if expected == "blocked" and expected_reason and expected_reason != actual_reason:
        if expected_reason == "max_concurrent":
            return "E_WRONG_CAPACITY_REASON"
        if expected_reason == "room_collision":
            return "C_WRONG_COLLISION_REASON_ROOM"
        if expected_reason == "lecturer_collision":
            return "C_WRONG_COLLISION_REASON_LECTURER"
        if expected_reason == "availability_exception":
            return "G_AVAILABILITY_EXCEPTION_REASON_MISMATCH"
        return "C_WRONG_COLLISION_REASON"
    return None


async def booking_check(institution_id: str, program_code: str, lecturer_code: Optional[str], time_block: str = MAIN_TIME, date: str = SCENARIO_DATE) -> tuple[str, str, Optional[str]]:
    async with AsyncSessionLocal() as db:
        message = await check_booking_collision(
            db,
            institution_id,
            program_id(program_code),
            date,
            time_block,
            lecturer_id=lecturer_id(lecturer_code) if lecturer_code else None,
        )
        await db.rollback()
    actual = "allow" if message is None else "blocked"
    return actual, classify_message(message), message


async def run_booking_scenario(
    conn,
    institution_id: str,
    scenario_id: str,
    name: str,
    setup: Iterable[tuple[str, str, Optional[str], str]],
    program_code: str,
    lecturer_code: Optional[str],
    expected: str,
    expected_reason: Optional[str] = None,
    time_block: str = MAIN_TIME,
) -> ScenarioResult:
    await delete_scenario_reservations(conn)
    for reservation_key, setup_program, setup_lecturer, setup_time in setup:
        await add_reservation(conn, reservation_key, institution_id, setup_program, setup_lecturer, setup_time)
    actual, actual_reason, message = await booking_check(institution_id, program_code, lecturer_code, time_block)
    passed = actual == expected and (expected == "allow" or expected_reason == actual_reason)
    return ScenarioResult(
        scenario_id,
        name,
        expected,
        actual,
        passed,
        expected_reason,
        actual_reason,
        message,
        diagnostic_for(expected, expected_reason, actual, actual_reason),
    )


async def run_pick_scenario(
    conn,
    institution_id: str,
    scenario_id: str,
    name: str,
    setup: Iterable[tuple[str, str, Optional[str], str]],
    program_code: str,
    expected_lecturer_code: Optional[str],
) -> ScenarioResult:
    await delete_scenario_reservations(conn)
    for reservation_key, setup_program, setup_lecturer, setup_time in setup:
        await add_reservation(conn, reservation_key, institution_id, setup_program, setup_lecturer, setup_time)
    async with AsyncSessionLocal() as db:
        row = await db.execute(select(Program).where(Program.id == uuid.UUID(program_id(program_code))))
        program = row.scalar_one()
        pick = await pick_main_lecturer(db, institution_id, program, SCENARIO_DATE, MAIN_TIME)
        await db.rollback()
    expected = "blocked" if expected_lecturer_code is None else "allow"
    actual = "blocked" if pick is None else "allow"
    actual_reason = "qualified_lecturer_unavailable" if pick is None else "auto_lecturer_available"
    expected_reason = "qualified_lecturer_unavailable" if expected_lecturer_code is None else "auto_lecturer_available"
    chosen_id = pick.get("lecturer_id") if pick else None
    passed = actual == expected and (
        expected_lecturer_code is None or chosen_id == lecturer_id(expected_lecturer_code)
    )
    message = None if pick is None else pick.get("reason")
    return ScenarioResult(
        scenario_id,
        name,
        expected,
        actual,
        passed,
        expected_reason,
        actual_reason,
        message,
        diagnostic_for(expected, expected_reason, actual, actual_reason),
    )


async def run_assignment_collision_scenario(conn, institution_id: str) -> ScenarioResult:
    await delete_scenario_reservations(conn)
    await add_reservation(conn, "res-50", institution_id, "P01", "L1", MAIN_TIME)
    target_id = await add_reservation(conn, "res-51", institution_id, "P03", "L1", MAIN_TIME)
    async with AsyncSessionLocal() as db:
        message = await check_lecturer_collision_for_assignment(
            db,
            lecturer_id("L1"),
            institution_id,
            target_id,
        )
        await db.rollback()
    actual = "allow" if message is None else "blocked"
    actual_reason = classify_message(message)
    expected_reason = "lecturer_collision"
    return ScenarioResult(
        "T05b",
        "Assignment service blocks assigning an already occupied lecturer",
        "blocked",
        actual,
        actual == "blocked" and actual_reason == expected_reason,
        expected_reason,
        actual_reason,
        message,
        diagnostic_for("blocked", expected_reason, actual, actual_reason),
    )


async def run_availability_exception_scenario(conn, institution_id: str, admin_id: Optional[str]) -> list[ScenarioResult]:
    await delete_scenario_reservations(conn)
    await conn.execute("DELETE FROM availability_exceptions WHERE id = $1::uuid", exception_id("program-p05"))
    await add_exception(conn, institution_id, admin_id)

    actual, actual_reason, message = await booking_check(
        institution_id,
        "P05",
        "L2",
        MAIN_TIME,
        EXCEPTION_DATE,
    )
    direct = ScenarioResult(
        "T19",
        "Program AvailabilityException blocks booking collision check",
        "blocked",
        actual,
        actual == "blocked" and actual_reason == "availability_exception",
        "availability_exception",
        actual_reason,
        message,
        diagnostic_for("blocked", "availability_exception", actual, actual_reason),
    )

    async with AsyncSessionLocal() as db:
        slots = await evaluate_program_slots(db, institution_id, program_id("P05"), EXCEPTION_DATE)
        await db.rollback()
    target_slot = next((slot for slot in slots if slot.get("time") == MAIN_TIME), None)
    slots_ok = bool(target_slot and target_slot.get("status") == STATUS_BLOCKED_EXCEPTION)
    availability = ScenarioResult(
        "T20",
        "Availability view marks exception slot unavailable",
        "blocked",
        "blocked" if slots_ok else "allow",
        slots_ok,
        "availability_exception",
        "availability_exception" if slots_ok else "allow",
        json.dumps(target_slot, ensure_ascii=False) if target_slot else "slot not returned",
        None if slots_ok else "G_AVAILABILITY_EXCEPTION_NOT_VISIBLE",
    )
    return [direct, availability]


async def run_order_independence_stress(conn, institution_id: str) -> ScenarioResult:
    expected = [
        ("P01", "L1", "allow"),
        ("P04", "L2", "allow"),
        ("P03", "L1", "blocked"),
        ("P05", "L4", "blocked"),
        ("P01", "L5", "allow"),
        ("P01", "L2", "blocked"),
    ]
    await delete_scenario_reservations(conn)
    actual_steps = []
    for idx, (program_code, lecturer_code, expected_actual) in enumerate(expected, start=1):
        actual, reason, message = await booking_check(institution_id, program_code, lecturer_code)
        actual_steps.append({"step": idx, "program": program_code, "lecturer": lecturer_code, "expected": expected_actual, "actual": actual, "reason": reason, "message": message})
        if actual == "allow":
            await add_reservation(conn, f"res-60-{idx}", institution_id, program_code, lecturer_code, MAIN_TIME)
    passed = all(step["expected"] == step["actual"] for step in actual_steps)
    return ScenarioResult(
        "S01",
        "Mixed order-independent stress path: allow, lecturer, room and max-capacity decisions stay stable",
        "mixed",
        "mixed",
        passed,
        "mixed",
        "mixed",
        json.dumps(actual_steps, ensure_ascii=False),
        None if passed else "H_STRESS_ORDER_INDEPENDENCE_FAILED",
    )


async def collect_report() -> dict:
    db_url = require_test_database_url(SCRIPT_NAME)
    configure_sqlalchemy_test_database(SCRIPT_NAME)
    import asyncpg

    conn = await asyncpg.connect(asyncpg_url(db_url), statement_cache_size=0)
    try:
        institution_id, admin_id = await find_target_institution(conn)
        await cleanup(conn)
        await seed_fixtures(conn, institution_id, admin_id)

        scenarios: list[ScenarioResult] = []
        scenarios.extend([
            await run_booking_scenario(conn, institution_id, "T01", "P01 + Anna at 10-11 is allowed", [], "P01", "L1", "allow"),
            await run_booking_scenario(conn, institution_id, "T02", "Second parallel P01 with different lecturer is allowed", [("res-1", "P01", "L1", MAIN_TIME)], "P01", "L2", "allow"),
            await run_booking_scenario(conn, institution_id, "T03", "Third parallel P01 is blocked by max_concurrent_bookings=2", [("res-2", "P01", "L1", MAIN_TIME), ("res-3", "P01", "L2", MAIN_TIME)], "P01", "L5", "blocked", "max_concurrent"),
            await run_booking_scenario(conn, institution_id, "T04", "Second P02 is blocked by max_concurrent_bookings=1", [("res-4", "P02", "L1", MAIN_TIME)], "P02", "L3", "blocked", "max_concurrent"),
            await run_booking_scenario(conn, institution_id, "T05", "Same lecturer cannot lead P01 and P03 at the same time", [("res-5", "P01", "L1", MAIN_TIME)], "P03", "L1", "blocked", "lecturer_collision"),
            await run_booking_scenario(conn, institution_id, "T06", "Different program and different lecturer can run in parallel", [("res-6", "P01", "L1", MAIN_TIME)], "P04", "L2", "allow"),
            await run_booking_scenario(conn, institution_id, "T07", "Same room blocks even with different lecturer", [("res-7", "P01", "L1", MAIN_TIME)], "P05", "L2", "blocked", "room_collision"),
            await run_booking_scenario(conn, institution_id, "T08", "Program allowing 2x still respects room collision", [("res-8", "P10", "L3", MAIN_TIME)], "P10", "L4", "blocked", "room_collision"),
            await run_booking_scenario(conn, institution_id, "T09", "Two P06 instances with the same lecturer are blocked", [("res-9", "P06", "L3", MAIN_TIME)], "P06", "L3", "blocked", "lecturer_collision"),
            await run_booking_scenario(conn, institution_id, "T10", "Second P06 with another qualified free lecturer is allowed", [("res-10", "P06", "L3", MAIN_TIME)], "P06", "L4", "allow"),
            await run_booking_scenario(conn, institution_id, "T11", "Unsupported lecturer Anna must not lead P09", [], "P09", "L1", "blocked", "unsupported_lecturer"),
            await run_pick_scenario(conn, institution_id, "T12", "P08 only has Petr; when Petr is busy no qualified lecturer is available", [("res-12", "P01", "L2", MAIN_TIME)], "P08", None),
            await run_booking_scenario(conn, institution_id, "T16", "Adjacent blocks with same lecturer do not overlap", [("res-16", "P01", "L1", "09:00-10:00")], "P03", "L1", "allow", time_block="10:00-11:00"),
            await run_booking_scenario(conn, institution_id, "T17", "One-minute overlap with same lecturer is blocked", [("res-17", "P01", "L1", "09:00-10:00")], "P03", "L1", "blocked", "lecturer_collision", time_block="09:59-11:00"),
            await run_booking_scenario(conn, institution_id, "T18", "Partial overlap with same lecturer is blocked", [("res-18", "P01", "L1", "09:00-10:30")], "P03", "L1", "blocked", "lecturer_collision", time_block="10:00-11:00"),
        ])

        await delete_scenario_reservations(conn)
        for idx, program_code, lecturer_code in [(1, "P01", "L1"), (2, "P04", "L2"), (3, "P11", "L4"), (4, "P12", "L5")]:
            actual, reason, message = await booking_check(institution_id, program_code, lecturer_code)
            if actual == "allow":
                await add_reservation(conn, f"res-13-{idx}", institution_id, program_code, lecturer_code)
            scenarios.append(
                ScenarioResult(
                    f"T13.{idx}",
                    f"Parallel distinct program {program_code} with distinct lecturer {lecturer_code}",
                    "allow",
                    actual,
                    actual == "allow",
                    None,
                    reason,
                    message,
                    diagnostic_for("allow", None, actual, reason),
                )
            )

        scenarios.append(
            await run_pick_scenario(
                conn,
                institution_id,
                "T14",
                "When Anna is busy, P07 remains bookable through free qualified Eliška",
                [("res-14", "P01", "L1", MAIN_TIME)],
                "P07",
                "L5",
            )
        )
        scenarios.append(
            await run_booking_scenario(
                conn,
                institution_id,
                "T15",
                "Klára cannot lead P10 and P09 at the same time",
                [("res-15", "P10", "L3", MAIN_TIME)],
                "P09",
                "L3",
                "blocked",
                "lecturer_collision",
            )
        )
        scenarios.append(await run_assignment_collision_scenario(conn, institution_id))
        scenarios.extend(await run_availability_exception_scenario(conn, institution_id, admin_id))
        scenarios.append(await run_order_independence_stress(conn, institution_id))

        failed = [item for item in scenarios if not item.passed]
        status = "ok" if not failed else "attention_required"
        await delete_scenario_reservations(conn)

        return {
            "status": status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "institution": {
                "id": institution_id,
                "expected_name": TARGET_INSTITUTION_NAME,
                "expected_admin_email": TARGET_ADMIN_EMAIL,
            },
            "seed": {
                "prefix": PREFIX,
                "lecturers": len(LECTURERS),
                "rooms": len(ROOMS),
                "programs": len(PROGRAMS),
                "scenario_date": SCENARIO_DATE,
            },
            "checks": {
                "uses_real_collision_service": True,
                "uses_real_assignment_service": True,
                "uses_real_availability_service": True,
                "scenarios_total": len(scenarios),
                "scenarios_passed": len([item for item in scenarios if item.passed]),
                "scenarios_failed": len(failed),
            },
            "failures": [item.__dict__ for item in failed],
            "scenarios": [item.__dict__ for item in scenarios],
        }
    finally:
        await conn.close()


def print_human_summary(report: dict) -> None:
    failed = report["failures"]
    print("\n=== Lecturer/program capacity regression summary ===", file=sys.stderr)
    print(
        f"Status: {report['status']} | passed {report['checks']['scenarios_passed']}/"
        f"{report['checks']['scenarios_total']}",
        file=sys.stderr,
    )
    if failed:
        print("Failures:", file=sys.stderr)
        for item in failed:
            print(
                f"- {item['id']}: {item['name']} -> {item['diagnostic']} "
                f"(actual={item['actual']}, reason={item['actual_reason']})",
                file=sys.stderr,
            )
    else:
        print("All expected collision layers passed.", file=sys.stderr)


async def main() -> None:
    report = await collect_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print_human_summary(report)
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
