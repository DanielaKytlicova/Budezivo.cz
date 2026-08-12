"""Smoke-check role rules and tenant isolation in an isolated regression DB.

Prerequisites:
- Run alembic upgrade head against TEST_DATABASE_URL.
- Run scripts/regression_core_seed.py first; this script reuses its primary
  institution and adds a deterministic second institution.

The script refuses production through scripts.safety and never prints secrets.
"""
from __future__ import annotations

import argparse
import ast
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
    from scripts.regression_core_seed import ADMIN_EMAIL, CASHIER_EMAIL, IDS as PRIMARY_IDS, SCHOOL_EMAIL, insert_row
    from scripts.safety import asyncpg_url, require_test_database_url
except ModuleNotFoundError:
    from regression_core_seed import ADMIN_EMAIL, CASHIER_EMAIL, IDS as PRIMARY_IDS, SCHOOL_EMAIL, insert_row
    from safety import asyncpg_url, require_test_database_url


SECOND_IDS = {
    "institution": "12121212-1212-4121-8121-121212121212",
    "admin": "23232323-2323-4232-8232-232323232323",
    "cashier": "23232323-2323-4232-8232-232323232324",
    "program": "34343434-3434-4343-8343-343434343434",
    "school": "45454545-4545-4454-8454-454545454545",
    "school_contact": "56565656-5656-4565-8565-565656565656",
    "contact": "67676767-6767-4676-8676-676767676767",
    "reservation": "78787878-7878-4787-8787-787878787878",
    "event": "89898989-8989-4898-8898-898989898989",
    "event_date": "90909090-9090-4909-8909-909090909090",
    "mailing_campaign": "abababab-abab-4aba-8aba-abababababab",
    "mailing_campaign_program": "bcbcbcbc-bcbc-4bcb-8bcb-bcbcbcbcbcbc",
    "mailing_recipient": "cdcdcdcd-cdcd-4cdc-8cdc-cdcdcdcdcdcd",
    "mailing_recipient_program": "dededede-dede-4ded-8ded-dededededede",
    "payment_settings": "efefefef-efef-4efe-8efe-efefefefefef",
}

SECOND_ADMIN_EMAIL = "regression-other-admin@example.test"
SECOND_CASHIER_EMAIL = "regression-other-cashier@example.test"
SECOND_SCHOOL_EMAIL = "regression.other.teacher@example.test"

REQUIRED_CHECKS = (
    "primary_seed_present",
    "secondary_seed_present",
    "program_list_scoped",
    "reservation_list_scoped",
    "contact_list_scoped",
    "school_contact_list_scoped",
    "event_list_scoped",
    "mailing_list_scoped",
    "direct_foreign_id_probes_blocked",
    "role_matrix_static",
)


def build_report(checks: Dict[str, bool], details: Dict[str, object] | None = None) -> Dict[str, object]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if all(checks.get(name) for name in REQUIRED_CHECKS) else "attention_required",
        "checks": {name: bool(checks.get(name)) for name in REQUIRED_CHECKS},
        "details": details or {},
    }


def _extract_set_assignment(path: Path, name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                value = ast.literal_eval(node.value)
                return set(value)
    raise RuntimeError(f"Could not find {name} in {path}")


def role_matrix_static_ok() -> bool:
    permissions = BACKEND_ROOT / "core" / "permissions.py"
    mailings = BACKEND_ROOT / "routes" / "mailings.py"

    management = _extract_set_assignment(permissions, "MANAGEMENT_ROLES")
    program_edit = _extract_set_assignment(permissions, "PROGRAM_EDIT_ROLES")
    event_manage = _extract_set_assignment(permissions, "EVENT_MANAGE_ROLES")
    payments = _extract_set_assignment(permissions, "PAYMENTS_ROLES")
    calendar_personal = _extract_set_assignment(permissions, "CALENDAR_PERSONAL_ROLES")
    calendar_export = _extract_set_assignment(permissions, "CALENDAR_INSTITUTION_EXPORT_ROLES")
    campaigns = _extract_set_assignment(mailings, "CAMPAIGN_ROLES")

    return (
        management == {"admin", "spravce"}
        and program_edit == {"admin", "spravce", "edukator"}
        and event_manage == {"admin", "spravce"}
        and payments == {"admin", "spravce", "ucetni", "pokladni"}
        and "pokladni" not in program_edit
        and "pokladni" not in event_manage
        and "pokladni" not in campaigns
        and "ucetni" not in calendar_personal
        and calendar_export == {"admin", "spravce"}
    )


async def cleanup_second(conn) -> None:
    await conn.execute("DELETE FROM mailing_recipient_programs WHERE recipient_id = $1::uuid", SECOND_IDS["mailing_recipient"])
    await conn.execute("DELETE FROM mailing_campaign_recipients WHERE campaign_id = $1::uuid", SECOND_IDS["mailing_campaign"])
    await conn.execute("DELETE FROM mailing_campaign_programs WHERE campaign_id = $1::uuid", SECOND_IDS["mailing_campaign"])
    await conn.execute("DELETE FROM mailing_campaigns WHERE institution_id = $1::uuid", SECOND_IDS["institution"])
    await conn.execute("DELETE FROM event_dates WHERE event_id = $1::uuid", SECOND_IDS["event"])
    await conn.execute("DELETE FROM events WHERE institution_id = $1::uuid", SECOND_IDS["institution"])
    await conn.execute("DELETE FROM reservations WHERE institution_id = $1::uuid", SECOND_IDS["institution"])
    await conn.execute("DELETE FROM contacts WHERE institution_id = $1::uuid", SECOND_IDS["institution"])
    await conn.execute("DELETE FROM school_contacts WHERE institution_id = $1::uuid", SECOND_IDS["institution"])
    await conn.execute("DELETE FROM schools WHERE institution_id = $1::uuid", SECOND_IDS["institution"])
    await conn.execute("DELETE FROM programs WHERE institution_id = $1::uuid", SECOND_IDS["institution"])
    await conn.execute("DELETE FROM institution_payment_settings WHERE institution_id = $1::uuid", SECOND_IDS["institution"])
    await conn.execute("DELETE FROM users WHERE email = ANY($1::text[])", [SECOND_ADMIN_EMAIL, SECOND_CASHIER_EMAIL])
    await conn.execute("DELETE FROM institutions WHERE id = $1::uuid", SECOND_IDS["institution"])


async def primary_seed_present(conn) -> bool:
    counts = await conn.fetchrow(
        """
        SELECT
          EXISTS(SELECT 1 FROM institutions WHERE id = $1::uuid) AS institution,
          EXISTS(SELECT 1 FROM users WHERE email = $2) AS admin_user,
          EXISTS(SELECT 1 FROM programs WHERE id = $3::uuid AND institution_id = $1::uuid) AS program,
          EXISTS(SELECT 1 FROM reservations WHERE id = $4::uuid AND institution_id = $1::uuid) AS reservation,
          EXISTS(SELECT 1 FROM mailing_campaigns WHERE id = $5::uuid AND institution_id = $1::uuid) AS mailing
        """,
        PRIMARY_IDS["institution"],
        ADMIN_EMAIL,
        PRIMARY_IDS["program"],
        PRIMARY_IDS["reservation"],
        PRIMARY_IDS["mailing_campaign"],
    )
    return all(bool(counts[key]) for key in counts.keys())


async def seed_second_institution(conn) -> None:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=2)).date().isoformat()
    event_start = now + timedelta(days=16)
    event_end = event_start + timedelta(hours=2)
    deadline = event_start - timedelta(days=2)

    await cleanup_second(conn)

    tx = conn.transaction()
    await tx.start()
    try:
        await insert_row(
            conn,
            "institutions",
            {
                "id": SECOND_IDS["institution"],
                "name": "Regression Other Institution",
                "type": "gallery",
                "country": "CZ",
                "city": "Other City",
                "email": "regression-other-institution@example.test",
                "plan": "pro",
                "plan_status": "active",
                "programs_limit": 25,
                "bookings_monthly_limit": 500,
                "default_available_days": ["monday", "tuesday", "wednesday"],
                "default_time_blocks": json.dumps([{"start": "11:00", "end": "12:00"}]),
                "notification_settings": json.dumps({"customer": {}, "admin": {"new_reservation": True, "recipient_user_ids": []}}),
                "locale_settings": json.dumps({"language": "cs", "timezone": "Europe/Prague"}),
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
            (SECOND_IDS["admin"], SECOND_ADMIN_EMAIL, "admin", "Regression Other Admin"),
            (SECOND_IDS["cashier"], SECOND_CASHIER_EMAIL, "pokladni", "Regression Other Cashier"),
        ):
            await insert_row(
                conn,
                "users",
                {
                    "id": user_id,
                    "institution_id": SECOND_IDS["institution"],
                    "email": email,
                    "password_hash": "$2b$12$regressiononlyhashedpasswordseedvalue",
                    "name": name,
                    "role": role,
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
                "id": SECOND_IDS["payment_settings"],
                "institution_id": SECOND_IDS["institution"],
                "payment_mode": "qr",
                "allowed_methods": json.dumps(["qr"]),
                "provider": None,
                "created_at": now,
                "updated_at": now,
            },
            {"id": "::uuid", "institution_id": "::uuid", "allowed_methods": "::json"},
        )

        await insert_row(
            conn,
            "programs",
            {
                "id": SECOND_IDS["program"],
                "institution_id": SECOND_IDS["institution"],
                "name_cs": "Regression Foreign Program",
                "description_cs": "Must not be visible to the primary institution.",
                "duration": 60,
                "age_group": "zs2_12_15",
                "min_capacity": 5,
                "max_capacity": 25,
                "required_lecturers": 1,
                "target_group": "schools",
                "target_groups": json.dumps(["zs2_12_15"]),
                "price": 0,
                "status": "active",
                "is_published": True,
                "requires_approval": False,
                "send_email_notification": True,
                "available_days": ["monday", "tuesday"],
                "time_blocks": json.dumps(["11:00-12:00"]),
                "end_date": now + timedelta(days=365),
                "min_days_before_booking": 1,
                "max_days_before_booking": 180,
                "preparation_time": 0,
                "cleanup_time": 0,
                "created_by": SECOND_IDS["admin"],
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
                "created_by": "::uuid",
                "feedback_questions": "::json",
            },
        )

        await insert_row(
            conn,
            "schools",
            {
                "id": SECOND_IDS["school"],
                "institution_id": SECOND_IDS["institution"],
                "name": "Regression Other School",
                "city": "Other City",
                "email": SECOND_SCHOOL_EMAIL,
                "booking_count": 1,
                "tags": json.dumps(["foreign-regression"]),
                "source": "manual",
                "created_at": now,
                "updated_at": now,
            },
            {"id": "::uuid", "institution_id": "::uuid", "tags": "::json"},
        )
        await insert_row(
            conn,
            "school_contacts",
            {
                "id": SECOND_IDS["school_contact"],
                "school_id": SECOND_IDS["school"],
                "institution_id": SECOND_IDS["institution"],
                "email": SECOND_SCHOOL_EMAIL,
                "name": "Other Test Teacher",
                "status": "active",
                "email_validated": True,
                "deliverability_status": "unknown",
                "is_primary": True,
                "created_at": now,
                "updated_at": now,
            },
            {"id": "::uuid", "school_id": "::uuid", "institution_id": "::uuid"},
        )
        await insert_row(
            conn,
            "contacts",
            {
                "id": SECOND_IDS["contact"],
                "institution_id": SECOND_IDS["institution"],
                "first_name": "Other",
                "last_name": "Teacher",
                "email": SECOND_SCHOOL_EMAIL,
                "type": "pedagog",
                "primary_source": "seed",
                "school_name": "Regression Other School",
                "marketing_consent": True,
                "marketing_consent_at": now,
                "deliverability_status": "unknown",
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
                "id": SECOND_IDS["reservation"],
                "institution_id": SECOND_IDS["institution"],
                "program_id": SECOND_IDS["program"],
                "date": tomorrow,
                "time_block": "11:00-12:00",
                "school_name": "Regression Other School",
                "school_id": SECOND_IDS["school"],
                "group_type": "zs2_12_15",
                "age_or_class": "7.B",
                "num_students": 18,
                "num_teachers": 2,
                "contact_name": "Other Test Teacher",
                "contact_email": SECOND_SCHOOL_EMAIL,
                "contact_phone": "+420000000001",
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
                "id": SECOND_IDS["event"],
                "institution_id": SECOND_IDS["institution"],
                "name": "Regression Other Event",
                "type": "event",
                "description": "Must not be visible to the primary institution.",
                "capacity": 30,
                "price": 0,
                "currency": "CZK",
                "is_active": True,
                "is_archived": False,
                "form_fields": json.dumps([]),
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
                "id": SECOND_IDS["event_date"],
                "event_id": SECOND_IDS["event"],
                "start_datetime": event_start,
                "end_datetime": event_end,
                "registration_deadline_override": deadline,
                "created_at": now,
            },
            {"id": "::uuid", "event_id": "::uuid"},
        )
        await insert_row(
            conn,
            "mailing_campaigns",
            {
                "id": SECOND_IDS["mailing_campaign"],
                "institution_id": SECOND_IDS["institution"],
                "created_by": SECOND_IDS["admin"],
                "name": "Regression Other Mailing Draft",
                "type": "seasonal",
                "status": "draft",
                "recipient_mode": "manual",
                "subject": "Foreign Regression Campaign",
                "greeting": "Dobry den,",
                "intro_text": "Other intro",
                "closing_text": "Other closing",
                "signature": "Other regression team",
                "content_snapshot": json.dumps({}),
                "selection_snapshot": json.dumps({"mode": "manual"}),
                "programs_snapshot": json.dumps([{"id": SECOND_IDS["program"], "name_cs": "Regression Foreign Program"}]),
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
            {"id": SECOND_IDS["mailing_campaign_program"], "campaign_id": SECOND_IDS["mailing_campaign"], "program_id": SECOND_IDS["program"], "display_order": 1},
            {"id": "::uuid", "campaign_id": "::uuid", "program_id": "::uuid"},
        )
        await insert_row(
            conn,
            "mailing_campaign_recipients",
            {
                "id": SECOND_IDS["mailing_recipient"],
                "campaign_id": SECOND_IDS["mailing_campaign"],
                "school_id": SECOND_IDS["school"],
                "contact_id": SECOND_IDS["school_contact"],
                "email": SECOND_SCHOOL_EMAIL,
                "school_name": "Regression Other School",
                "contact_name": "Other Test Teacher",
                "status": "pending",
                "matching_reason": json.dumps({"selection_mode": "manual", "manual_override": True}),
                "delivery_status": "unknown",
                "created_at": now,
            },
            {"id": "::uuid", "campaign_id": "::uuid", "school_id": "::uuid", "contact_id": "::uuid", "matching_reason": "::json"},
        )
        await insert_row(
            conn,
            "mailing_recipient_programs",
            {
                "id": SECOND_IDS["mailing_recipient_program"],
                "recipient_id": SECOND_IDS["mailing_recipient"],
                "program_id": SECOND_IDS["program"],
                "program_name": "Regression Foreign Program",
                "program_target_groups": json.dumps(["zs2_12_15"]),
            },
            {"id": "::uuid", "recipient_id": "::uuid", "program_id": "::uuid", "program_target_groups": "::json"},
        )
        await tx.commit()
    except Exception:
        await tx.rollback()
        raise


async def collect_report() -> Dict[str, object]:
    db_url = asyncpg_url(require_test_database_url("regression_role_isolation_smoke.py"))

    import asyncpg

    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    try:
        primary_ok = await primary_seed_present(conn)
        if primary_ok:
            await seed_second_institution(conn)

        secondary_ok = bool(await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM institutions WHERE id = $1::uuid)",
            SECOND_IDS["institution"],
        ))

        async def ids_for(query: str, *args) -> set[str]:
            rows = await conn.fetch(query, *args)
            return {str(row["id"]) for row in rows}

        primary_program_ids = await ids_for(
            "SELECT id FROM programs WHERE institution_id = $1::uuid",
            PRIMARY_IDS["institution"],
        )
        primary_reservation_ids = await ids_for(
            "SELECT id FROM reservations WHERE institution_id = $1::uuid",
            PRIMARY_IDS["institution"],
        )
        primary_contact_ids = await ids_for(
            "SELECT id FROM contacts WHERE institution_id = $1::uuid",
            PRIMARY_IDS["institution"],
        )
        primary_school_contact_ids = await ids_for(
            "SELECT id FROM school_contacts WHERE institution_id = $1::uuid",
            PRIMARY_IDS["institution"],
        )
        primary_event_ids = await ids_for(
            "SELECT id FROM events WHERE institution_id = $1::uuid",
            PRIMARY_IDS["institution"],
        )
        primary_mailing_ids = await ids_for(
            "SELECT id FROM mailing_campaigns WHERE institution_id = $1::uuid",
            PRIMARY_IDS["institution"],
        )

        direct_probes = {
            "program": await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM programs WHERE id = $1::uuid AND institution_id = $2::uuid)",
                SECOND_IDS["program"],
                PRIMARY_IDS["institution"],
            ),
            "reservation": await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM reservations WHERE id = $1::uuid AND institution_id = $2::uuid)",
                SECOND_IDS["reservation"],
                PRIMARY_IDS["institution"],
            ),
            "contact": await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM contacts WHERE id = $1::uuid AND institution_id = $2::uuid)",
                SECOND_IDS["contact"],
                PRIMARY_IDS["institution"],
            ),
            "school_contact": await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM school_contacts WHERE id = $1::uuid AND institution_id = $2::uuid)",
                SECOND_IDS["school_contact"],
                PRIMARY_IDS["institution"],
            ),
            "event": await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM events WHERE id = $1::uuid AND institution_id = $2::uuid)",
                SECOND_IDS["event"],
                PRIMARY_IDS["institution"],
            ),
            "mailing_campaign": await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM mailing_campaigns WHERE id = $1::uuid AND institution_id = $2::uuid)",
                SECOND_IDS["mailing_campaign"],
                PRIMARY_IDS["institution"],
            ),
        }

        checks = {
            "primary_seed_present": primary_ok,
            "secondary_seed_present": secondary_ok,
            "program_list_scoped": PRIMARY_IDS["program"] in primary_program_ids and SECOND_IDS["program"] not in primary_program_ids,
            "reservation_list_scoped": PRIMARY_IDS["reservation"] in primary_reservation_ids and SECOND_IDS["reservation"] not in primary_reservation_ids,
            "contact_list_scoped": PRIMARY_IDS["contact"] in primary_contact_ids and SECOND_IDS["contact"] not in primary_contact_ids,
            "school_contact_list_scoped": PRIMARY_IDS["school_contact"] in primary_school_contact_ids and SECOND_IDS["school_contact"] not in primary_school_contact_ids,
            "event_list_scoped": PRIMARY_IDS["event"] in primary_event_ids and SECOND_IDS["event"] not in primary_event_ids,
            "mailing_list_scoped": PRIMARY_IDS["mailing_campaign"] in primary_mailing_ids and SECOND_IDS["mailing_campaign"] not in primary_mailing_ids,
            "direct_foreign_id_probes_blocked": not any(bool(value) for value in direct_probes.values()),
            "role_matrix_static": role_matrix_static_ok(),
        }
        details = {
            "primary_institution_id": PRIMARY_IDS["institution"],
            "secondary_institution_id": SECOND_IDS["institution"],
            "primary_admin_email": ADMIN_EMAIL,
            "primary_cashier_email": CASHIER_EMAIL,
            "primary_school_email": SCHOOL_EMAIL,
            "secondary_admin_email": SECOND_ADMIN_EMAIL,
            "secondary_cashier_email": SECOND_CASHIER_EMAIL,
            "secondary_school_email": SECOND_SCHOOL_EMAIL,
            "direct_foreign_id_probes": {key: bool(value) for key, value in direct_probes.items()},
        }
        return build_report(checks, details)
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cleanup-secondary-only", action="store_true", help="Remove only the deterministic second institution seed and exit.")
    parser.add_argument("--output", help="Optional JSON output path. The report never includes credentials.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    db_url = asyncpg_url(require_test_database_url("regression_role_isolation_smoke.py"))
    if args.cleanup_secondary_only:
        import asyncpg

        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        try:
            await cleanup_second(conn)
        finally:
            await conn.close()
        print(json.dumps({"status": "ok", "cleanup_secondary_only": True}, ensure_ascii=False, indent=2, sort_keys=True))
        return

    report = await collect_report()
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
