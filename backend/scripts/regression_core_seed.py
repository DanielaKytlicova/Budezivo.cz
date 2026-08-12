"""Seed and verify minimal core-flow data in an isolated regression database.

This script is intentionally guarded by scripts.safety:
- APP_ENV must be test
- TEST_DATABASE_URL must be present
- DATABASE_URL is not accepted
- the known production Supabase project is refused

It creates deterministic test records and prints a generated one-time admin
password for the isolated test database only. No committed demo password exists.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from scripts.safety import asyncpg_url, require_test_database_url
except ModuleNotFoundError:
    from safety import asyncpg_url, require_test_database_url


IDS = {
    "institution": "11111111-1111-4111-8111-111111111111",
    "admin": "22222222-2222-4222-8222-222222222222",
    "cashier": "22222222-2222-4222-8222-222222222223",
    "program": "33333333-3333-4333-8333-333333333333",
    "school": "44444444-4444-4444-8444-444444444444",
    "school_contact": "55555555-5555-4555-8555-555555555555",
    "contact": "66666666-6666-4666-8666-666666666666",
    "reservation": "77777777-7777-4777-8777-777777777777",
    "event": "88888888-8888-4888-8888-888888888888",
    "event_date": "99999999-9999-4999-8999-999999999999",
    "mailing_campaign": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "mailing_campaign_program": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    "mailing_recipient": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    "mailing_recipient_program": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
    "payment_settings": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
}

ADMIN_EMAIL = "regression-admin@example.test"
CASHIER_EMAIL = "regression-cashier@example.test"
SCHOOL_EMAIL = "regression.teacher@example.test"

CORE_TABLES = (
    "institutions",
    "users",
    "programs",
    "schools",
    "school_contacts",
    "contacts",
    "reservations",
    "events",
    "event_dates",
    "mailing_campaigns",
    "mailing_campaign_programs",
    "mailing_campaign_recipients",
    "mailing_recipient_programs",
    "institution_payment_settings",
)


def generated_admin_password() -> str:
    return "Rg-" + secrets.token_urlsafe(18) + "9a"


def expected_seed_counts() -> Dict[str, int]:
    counts = {table: 1 for table in CORE_TABLES}
    counts["users"] = 2
    return counts


async def table_counts(conn) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    institution_scoped = {
        "users",
        "programs",
        "schools",
        "school_contacts",
        "contacts",
        "reservations",
        "events",
        "mailing_campaigns",
        "institution_payment_settings",
    }
    for table in institution_scoped:
        counts[table] = await conn.fetchval(
            f'SELECT count(*) FROM "{table}" WHERE institution_id = $1::uuid',
            IDS["institution"],
        )
    counts["institutions"] = await conn.fetchval(
        'SELECT count(*) FROM institutions WHERE id = $1::uuid',
        IDS["institution"],
    )
    counts["event_dates"] = await conn.fetchval(
        'SELECT count(*) FROM event_dates WHERE event_id = $1::uuid',
        IDS["event"],
    )
    counts["mailing_campaign_programs"] = await conn.fetchval(
        'SELECT count(*) FROM mailing_campaign_programs WHERE campaign_id = $1::uuid',
        IDS["mailing_campaign"],
    )
    counts["mailing_campaign_recipients"] = await conn.fetchval(
        'SELECT count(*) FROM mailing_campaign_recipients WHERE campaign_id = $1::uuid',
        IDS["mailing_campaign"],
    )
    counts["mailing_recipient_programs"] = await conn.fetchval(
        'SELECT count(*) FROM mailing_recipient_programs WHERE recipient_id = $1::uuid',
        IDS["mailing_recipient"],
    )
    return counts


async def cleanup(conn) -> None:
    await conn.execute("DELETE FROM institutions WHERE id = $1::uuid", IDS["institution"])
    await conn.execute("DELETE FROM users WHERE email = ANY($1::text[])", [ADMIN_EMAIL, CASHIER_EMAIL])


def hash_seed_password(password: str) -> str:
    import bcrypt

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def table_columns(conn, table_name: str) -> set[str]:
    rows = await conn.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = $1
        """,
        table_name,
    )
    return {row["column_name"] for row in rows}


async def insert_row(conn, table_name: str, values: Dict[str, object], casts: Dict[str, str] | None = None) -> None:
    existing_columns = await table_columns(conn, table_name)
    filtered = {column: value for column, value in values.items() if column in existing_columns}
    if not filtered:
        raise RuntimeError(f"No matching columns available for {table_name}")

    casts = casts or {}
    columns = list(filtered)
    placeholders = [
        f"${index}{casts.get(column, '')}"
        for index, column in enumerate(columns, start=1)
    ]
    query = (
        f'INSERT INTO "{table_name}" ('
        + ", ".join(f'"{column}"' for column in columns)
        + ") VALUES ("
        + ", ".join(placeholders)
        + ")"
    )
    await conn.execute(query, *[filtered[column] for column in columns])


async def seed(conn, admin_password: str) -> Dict[str, object]:
    password_hash = hash_seed_password(admin_password)

    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).date().isoformat()
    event_start = now + timedelta(days=14)
    event_end = event_start + timedelta(hours=2)
    deadline = event_start - timedelta(days=2)

    await cleanup(conn)

    tx = conn.transaction()
    await tx.start()
    try:
        await insert_row(
            conn,
            "institutions",
            {
                "id": IDS["institution"],
                "name": "Regression Test Institution",
                "type": "museum",
                "country": "CZ",
                "city": "Test City",
                "email": "regression-institution@example.test",
                "plan": "pro",
                "plan_status": "active",
                "programs_limit": 25,
                "bookings_monthly_limit": 500,
                "default_available_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "default_time_blocks": json.dumps([{"start": "09:00", "end": "10:30"}]),
                "notification_settings": json.dumps({"customer": {}, "admin": {"new_reservation": True, "recipient_user_ids": []}}),
                "locale_settings": json.dumps({"language": "cs", "timezone": "Europe/Prague", "date_format": "dd.mm.yyyy", "time_format": "24h"}),
                "gdpr_settings": json.dumps({"data_retention": "never", "anonymize": False}),
                "pro_settings": json.dumps({}),
                "onboarding_completed": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "::uuid",
                "default_available_days": "::text[]",
                "default_time_blocks": "::json",
                "notification_settings": "::json",
                "locale_settings": "::json",
                "gdpr_settings": "::json",
                "pro_settings": "::json",
            },
        )

        for user_id, email, role, name in (
            (IDS["admin"], ADMIN_EMAIL, "admin", "Regression Admin"),
            (IDS["cashier"], CASHIER_EMAIL, "pokladni", "Regression Cashier"),
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
                    "role": role,
                    "lecturer_mode": "main",
                    "status": "active",
                    "gdpr_consent": True,
                    "terms_accepted": True,
                    "created_at": now,
                    "updated_at": now,
                },
                {"id": "::uuid", "institution_id": "::uuid"},
            )

        await insert_row(
            conn,
            "institution_payment_settings",
            {
                "id": IDS["payment_settings"],
                "institution_id": IDS["institution"],
                "payment_mode": "qr",
                "allowed_methods": json.dumps(["qr", "cash"]),
                "provider": None,
                "account_number": "123456789",
                "bank_code": "0100",
                "account_name": "Regression Test Institution",
                "created_at": now,
                "updated_at": now,
            },
            {"id": "::uuid", "institution_id": "::uuid", "allowed_methods": "::json"},
        )

        await insert_row(
            conn,
            "programs",
            {
                "id": IDS["program"],
                "institution_id": IDS["institution"],
                "name_cs": "Regression Program",
                "description_cs": "Program for isolated regression testing.",
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
                "send_email_notification": True,
                "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "time_blocks": json.dumps(["09:00-10:30", "10:45-12:15"]),
                "start_date": None,
                "end_date": now + timedelta(days=365),
                "min_days_before_booking": 1,
                "max_days_before_booking": 180,
                "preparation_time": 0,
                "cleanup_time": 0,
                "collision_resources": json.dumps([]),
                "collision_lecturer_ids": json.dumps([]),
                "blocked_program_ids": json.dumps([]),
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
                "created_by": "::uuid",
                "feedback_questions": "::json",
            },
        )

        await insert_row(
            conn,
            "schools",
            {
                "id": IDS["school"],
                "institution_id": IDS["institution"],
                "name": "Regression School",
                "address": "Test Street 1",
                "city": "Test City",
                "contact_person": "Test Teacher",
                "email": SCHOOL_EMAIL,
                "phone": "+420000000000",
                "booking_count": 1,
                "tags": json.dumps(["regression"]),
                "source": "manual",
                "notes": "Seeded by regression_core_seed.py",
                "created_at": now,
                "updated_at": now,
            },
            {"id": "::uuid", "institution_id": "::uuid", "tags": "::json"},
        )
        await insert_row(
            conn,
            "school_contacts",
            {
                "id": IDS["school_contact"],
                "school_id": IDS["school"],
                "institution_id": IDS["institution"],
                "email": SCHOOL_EMAIL,
                "name": "Test Teacher",
                "phone": "+420000000000",
                "status": "active",
                "email_validated": True,
                "deliverability_status": "unknown",
                "is_primary": True,
                "notes": "Seeded by regression_core_seed.py",
                "created_at": now,
                "updated_at": now,
            },
            {"id": "::uuid", "school_id": "::uuid", "institution_id": "::uuid"},
        )
        await insert_row(
            conn,
            "contacts",
            {
                "id": IDS["contact"],
                "institution_id": IDS["institution"],
                "first_name": "Test",
                "last_name": "Teacher",
                "email": SCHOOL_EMAIL,
                "phone": "+420000000000",
                "type": "pedagog",
                "primary_source": "seed",
                "school_name": "Regression School",
                "school_type": "ZS",
                "marketing_consent": True,
                "marketing_consent_at": now,
                "deliverability_status": "unknown",
                "note": "Seeded by regression_core_seed.py",
                "created_at": now,
                "updated_at": now,
                "last_activity_at": now,
            },
            {"id": "::uuid", "institution_id": "::uuid"},
        )
        await insert_row(
            conn,
            "reservations",
            {
                "id": IDS["reservation"],
                "institution_id": IDS["institution"],
                "program_id": IDS["program"],
                "date": tomorrow,
                "time_block": "09:00-10:30",
                "school_name": "Regression School",
                "school_id": IDS["school"],
                "group_type": "zs1_7_12",
                "age_or_class": "3.A",
                "num_students": 20,
                "num_teachers": 2,
                "contact_name": "Test Teacher",
                "contact_email": SCHOOL_EMAIL,
                "contact_phone": "+420000000000",
                "status": "confirmed",
                "gdpr_consent": True,
                "gdpr_consent_date": now,
                "terms_accepted": True,
                "terms_accepted_at": now,
                "terms_accepted_text_version": "v1",
                "marketing_consent": True,
                "created_at": now,
                "updated_at": now,
            },
            {"id": "::uuid", "institution_id": "::uuid", "program_id": "::uuid", "school_id": "::uuid"},
        )

        await insert_row(
            conn,
            "events",
            {
                "id": IDS["event"],
                "institution_id": IDS["institution"],
                "name": "Regression Event",
                "type": "event",
                "description": "Event for isolated regression testing.",
                "capacity": 30,
                "price": 0,
                "currency": "CZK",
                "is_active": True,
                "is_archived": False,
                "form_fields": json.dumps([{"id": "name", "type": "text", "label": "Name", "required": True, "order": 1}]),
                "registration_deadline": deadline,
                "allowed_payment_methods": None,
                "created_at": now,
                "updated_at": now,
            },
            {"id": "::uuid", "institution_id": "::uuid", "form_fields": "::json", "allowed_payment_methods": "::json"},
        )
        await insert_row(
            conn,
            "event_dates",
            {
                "id": IDS["event_date"],
                "event_id": IDS["event"],
                "start_datetime": event_start,
                "end_datetime": event_end,
                "capacity_override": 25,
                "registration_deadline_override": deadline,
                "created_at": now,
            },
            {"id": "::uuid", "event_id": "::uuid"},
        )

        await insert_row(
            conn,
            "mailing_campaigns",
            {
                "id": IDS["mailing_campaign"],
                "institution_id": IDS["institution"],
                "created_by": IDS["admin"],
                "name": "Regression Mailing Draft",
                "type": "seasonal",
                "status": "draft",
                "recipient_mode": "manual",
                "subject": "Regression Campaign",
                "greeting": "Dobry den,",
                "intro_text": "Test intro",
                "closing_text": "Test closing",
                "signature": "Regression team",
                "content_snapshot": json.dumps({}),
                "selection_snapshot": json.dumps({"mode": "manual"}),
                "programs_snapshot": json.dumps([{"id": IDS["program"], "name_cs": "Regression Program"}]),
                "total_recipients": 1,
                "sent_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "::uuid",
                "institution_id": "::uuid",
                "created_by": "::uuid",
                "content_snapshot": "::json",
                "selection_snapshot": "::json",
                "programs_snapshot": "::json",
            },
        )
        await insert_row(
            conn,
            "mailing_campaign_programs",
            {
                "id": IDS["mailing_campaign_program"],
                "campaign_id": IDS["mailing_campaign"],
                "program_id": IDS["program"],
                "display_order": 1,
            },
            {"id": "::uuid", "campaign_id": "::uuid", "program_id": "::uuid"},
        )
        await insert_row(
            conn,
            "mailing_campaign_recipients",
            {
                "id": IDS["mailing_recipient"],
                "campaign_id": IDS["mailing_campaign"],
                "school_id": IDS["school"],
                "contact_id": IDS["school_contact"],
                "email": SCHOOL_EMAIL,
                "school_name": "Regression School",
                "contact_name": "Test Teacher",
                "status": "pending",
                "matching_reason": json.dumps({"selection_mode": "manual", "manual_override": True}),
                "delivery_status": "unknown",
                "created_at": now,
            },
            {
                "id": "::uuid",
                "campaign_id": "::uuid",
                "school_id": "::uuid",
                "contact_id": "::uuid",
                "matching_reason": "::json",
            },
        )
        await insert_row(
            conn,
            "mailing_recipient_programs",
            {
                "id": IDS["mailing_recipient_program"],
                "recipient_id": IDS["mailing_recipient"],
                "program_id": IDS["program"],
                "program_name": "Regression Program",
                "program_target_groups": json.dumps(["zs1_7_12"]),
            },
            {"id": "::uuid", "recipient_id": "::uuid", "program_id": "::uuid", "program_target_groups": "::json"},
        )

        counts = await table_counts(conn)
        expected = expected_seed_counts()
        missing = {table: expected[table] - counts.get(table, 0) for table in expected if counts.get(table, 0) < expected[table]}
        if missing:
            raise RuntimeError(f"Seed verification failed: {missing}")

        await tx.commit()
    except Exception:
        await tx.rollback()
        raise

    return {
        "status": "ok",
        "institution_id": IDS["institution"],
        "admin_email": ADMIN_EMAIL,
        "admin_password": admin_password,
        "cashier_email": CASHIER_EMAIL,
        "cashier_password": admin_password,
        "program_id": IDS["program"],
        "reservation_id": IDS["reservation"],
        "event_id": IDS["event"],
        "event_date_id": IDS["event_date"],
        "mailing_campaign_id": IDS["mailing_campaign"],
        "booking_path": f"/booking/{IDS['institution']}",
        "seeded_counts": counts,
    }

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cleanup-only", action="store_true", help="Remove the deterministic regression seed records and exit.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    db_url = asyncpg_url(require_test_database_url("regression_core_seed.py"))

    import asyncpg

    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    try:
        if args.cleanup_only:
            await cleanup(conn)
            print(json.dumps({"status": "ok", "cleanup": "done", "institution_id": IDS["institution"]}, indent=2, sort_keys=True))
            return

        report = await seed(conn, generated_admin_password())
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
