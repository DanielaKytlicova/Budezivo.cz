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
        await conn.execute(
            """
            INSERT INTO institutions (
                id, name, type, country, city, email, plan, plan_status,
                programs_limit, bookings_monthly_limit, default_available_days,
                default_time_blocks, notification_settings, locale_settings,
                gdpr_settings, pro_settings, onboarding_completed, created_at, updated_at
            )
            VALUES (
                $1::uuid, 'Regression Test Institution', 'museum', 'CZ', 'Test City',
                'regression-institution@example.test', 'pro', 'active', 25, 500,
                $2::text[], $3::json, $4::json, $5::json, $6::json, $7::json,
                true, $8, $8
            )
            """,
            IDS["institution"],
            ["monday", "tuesday", "wednesday", "thursday", "friday"],
            json.dumps([{"start": "09:00", "end": "10:30"}]),
            json.dumps({"customer": {}, "admin": {"new_reservation": True, "recipient_user_ids": []}}),
            json.dumps({"language": "cs", "timezone": "Europe/Prague", "date_format": "dd.mm.yyyy", "time_format": "24h"}),
            json.dumps({"data_retention": "never", "anonymize": False}),
            json.dumps({}),
            now,
        )

        for user_id, email, role, name in (
            (IDS["admin"], ADMIN_EMAIL, "admin", "Regression Admin"),
            (IDS["cashier"], CASHIER_EMAIL, "pokladni", "Regression Cashier"),
        ):
            await conn.execute(
                """
                INSERT INTO users (
                    id, institution_id, email, password_hash, name, role, lecturer_mode,
                    status, gdpr_consent, terms_accepted, created_at, updated_at
                )
                VALUES (
                    $1::uuid, $2::uuid, $3, $4, $5, $6, 'main',
                    'active', true, true, $7, $7
                )
                """,
                user_id,
                IDS["institution"],
                email,
                password_hash,
                name,
                role,
                now,
            )

        await conn.execute(
            """
            INSERT INTO institution_payment_settings (
                id, institution_id, payment_mode, allowed_methods, provider,
                account_number, bank_code, account_name, created_at, updated_at
            )
            VALUES (
                $1::uuid, $2::uuid, 'qr', $3::json, NULL,
                '123456789', '0100', 'Regression Test Institution', $4, $4
            )
            """,
            IDS["payment_settings"],
            IDS["institution"],
            json.dumps(["qr", "cash"]),
            now,
        )

        await conn.execute(
            """
            INSERT INTO programs (
                id, institution_id, name_cs, description_cs, duration, age_group,
                min_capacity, max_capacity, required_lecturers, target_group,
                target_groups, price, status, is_published, requires_approval,
                send_email_notification, available_days, time_blocks, start_date,
                end_date, min_days_before_booking, max_days_before_booking,
                preparation_time, cleanup_time, collision_resources,
                collision_lecturer_ids, blocked_program_ids, created_by,
                feedback_enabled, feedback_questions, created_at, updated_at
            )
            VALUES (
                $1::uuid, $2::uuid, 'Regression Program', 'Program for isolated regression testing.',
                90, 'zs1_7_12', 5, 30, 1, 'schools', $3::json, 0,
                'active', true, false, true, $4::text[], $5::json, NULL,
                $6, 1, 180, 0, 0, $7::json, $7::json, $7::json,
                $8::uuid, true, $7::json, $9, $9
            )
            """,
            IDS["program"],
            IDS["institution"],
            json.dumps(["zs1_7_12"]),
            ["monday", "tuesday", "wednesday", "thursday", "friday"],
            json.dumps(["09:00-10:30", "10:45-12:15"]),
            now + timedelta(days=365),
            json.dumps([]),
            IDS["admin"],
            now,
        )

        await conn.execute(
            """
            INSERT INTO schools (
                id, institution_id, name, address, city, contact_person, email,
                phone, booking_count, tags, source, notes, created_at, updated_at
            )
            VALUES (
                $1::uuid, $2::uuid, 'Regression School', 'Test Street 1',
                'Test City', 'Test Teacher', $3, '+420000000000', 1,
                $4::json, 'manual', 'Seeded by regression_core_seed.py', $5, $5
            )
            """,
            IDS["school"],
            IDS["institution"],
            SCHOOL_EMAIL,
            json.dumps(["regression"]),
            now,
        )
        await conn.execute(
            """
            INSERT INTO school_contacts (
                id, school_id, institution_id, email, name, phone, status,
                email_validated, deliverability_status, is_primary, notes,
                created_at, updated_at
            )
            VALUES (
                $1::uuid, $2::uuid, $3::uuid, $4, 'Test Teacher',
                '+420000000000', 'active', true, 'unknown', true,
                'Seeded by regression_core_seed.py', $5, $5
            )
            """,
            IDS["school_contact"],
            IDS["school"],
            IDS["institution"],
            SCHOOL_EMAIL,
            now,
        )
        await conn.execute(
            """
            INSERT INTO contacts (
                id, institution_id, first_name, last_name, email, phone, type,
                primary_source, school_name, school_type, marketing_consent,
                marketing_consent_at, deliverability_status, note,
                created_at, updated_at, last_activity_at
            )
            VALUES (
                $1::uuid, $2::uuid, 'Test', 'Teacher', $3, '+420000000000',
                'pedagog', 'seed', 'Regression School', 'ZS', true, $4,
                'unknown', 'Seeded by regression_core_seed.py', $4, $4, $4
            )
            """,
            IDS["contact"],
            IDS["institution"],
            SCHOOL_EMAIL,
            now,
        )
        await conn.execute(
            """
            INSERT INTO reservations (
                id, institution_id, program_id, date, time_block, school_name,
                school_id, group_type, age_or_class, num_students, num_teachers,
                contact_name, contact_email, contact_phone, status, gdpr_consent,
                gdpr_consent_date, terms_accepted, terms_accepted_at,
                terms_accepted_text_version, marketing_consent, created_at, updated_at
            )
            VALUES (
                $1::uuid, $2::uuid, $3::uuid, $4, '09:00-10:30',
                'Regression School', $5::uuid, 'zs1_7_12', '3.A', 20, 2,
                'Test Teacher', $6, '+420000000000', 'confirmed', true,
                $7, true, $7, 'v1', true, $7, $7
            )
            """,
            IDS["reservation"],
            IDS["institution"],
            IDS["program"],
            tomorrow,
            IDS["school"],
            SCHOOL_EMAIL,
            now,
        )

        await conn.execute(
            """
            INSERT INTO events (
                id, institution_id, name, type, description, capacity, price,
                currency, is_active, is_archived, form_fields,
                registration_deadline, allowed_payment_methods, created_at, updated_at
            )
            VALUES (
                $1::uuid, $2::uuid, 'Regression Event', 'event',
                'Event for isolated regression testing.', 30, 0, 'CZK',
                true, false, $3::json, $4, NULL, $5, $5
            )
            """,
            IDS["event"],
            IDS["institution"],
            json.dumps([{"id": "name", "type": "text", "label": "Name", "required": True, "order": 1}]),
            deadline,
            now,
        )
        await conn.execute(
            """
            INSERT INTO event_dates (
                id, event_id, start_datetime, end_datetime,
                capacity_override, registration_deadline_override, created_at
            )
            VALUES ($1::uuid, $2::uuid, $3, $4, 25, $5, $6)
            """,
            IDS["event_date"],
            IDS["event"],
            event_start,
            event_end,
            deadline,
            now,
        )

        await conn.execute(
            """
            INSERT INTO mailing_campaigns (
                id, institution_id, created_by, name, type, status,
                recipient_mode, subject, greeting, intro_text, closing_text,
                signature, content_snapshot, selection_snapshot, programs_snapshot,
                total_recipients, sent_count, failed_count, skipped_count,
                created_at, updated_at
            )
            VALUES (
                $1::uuid, $2::uuid, $3::uuid, 'Regression Mailing Draft',
                'seasonal', 'draft', 'manual', 'Regression Campaign',
                'Dobry den,', 'Test intro', 'Test closing', 'Regression team',
                $4::json, $5::json, $6::json, 1, 0, 0, 0, $7, $7
            )
            """,
            IDS["mailing_campaign"],
            IDS["institution"],
            IDS["admin"],
            json.dumps({}),
            json.dumps({"mode": "manual"}),
            json.dumps([{"id": IDS["program"], "name_cs": "Regression Program"}]),
            now,
        )
        await conn.execute(
            """
            INSERT INTO mailing_campaign_programs (id, campaign_id, program_id, display_order)
            VALUES ($1::uuid, $2::uuid, $3::uuid, 1)
            """,
            IDS["mailing_campaign_program"],
            IDS["mailing_campaign"],
            IDS["program"],
        )
        await conn.execute(
            """
            INSERT INTO mailing_campaign_recipients (
                id, campaign_id, school_id, contact_id, email, school_name,
                contact_name, status, matching_reason, delivery_status, created_at
            )
            VALUES (
                $1::uuid, $2::uuid, $3::uuid, $4::uuid, $5,
                'Regression School', 'Test Teacher', 'pending',
                $6::json, 'unknown', $7
            )
            """,
            IDS["mailing_recipient"],
            IDS["mailing_campaign"],
            IDS["school"],
            IDS["school_contact"],
            SCHOOL_EMAIL,
            json.dumps({"selection_mode": "manual", "manual_override": True}),
            now,
        )
        await conn.execute(
            """
            INSERT INTO mailing_recipient_programs (
                id, recipient_id, program_id, program_name, program_target_groups
            )
            VALUES ($1::uuid, $2::uuid, $3::uuid, 'Regression Program', $4::json)
            """,
            IDS["mailing_recipient_program"],
            IDS["mailing_recipient"],
            IDS["program"],
            json.dumps(["zs1_7_12"]),
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
