"""Smoke-check seeded core-flow data in an isolated regression database.

This script is read-only. It verifies the deterministic data created by
regression_core_seed.py and refuses production through scripts.safety.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from scripts.regression_core_seed import ADMIN_EMAIL, CASHIER_EMAIL, IDS, SCHOOL_EMAIL
    from scripts.safety import asyncpg_url, require_test_database_url
except ModuleNotFoundError:
    from regression_core_seed import ADMIN_EMAIL, CASHIER_EMAIL, IDS, SCHOOL_EMAIL
    from safety import asyncpg_url, require_test_database_url


REQUIRED_CHECKS = (
    "institution_present",
    "users_present",
    "program_present",
    "school_and_contact_present",
    "reservation_linked",
    "event_and_date_valid",
    "mailing_draft_linked",
)


def build_report(checks: Dict[str, bool], details: Dict[str, object] | None = None) -> Dict[str, object]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if all(checks.get(name) for name in REQUIRED_CHECKS) else "attention_required",
        "checks": {name: bool(checks.get(name)) for name in REQUIRED_CHECKS},
        "details": details or {},
    }


async def collect_report() -> Dict[str, object]:
    db_url = asyncpg_url(require_test_database_url("regression_core_smoke.py"))

    import asyncpg

    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    try:
        institution = await conn.fetchrow(
            "SELECT id, name FROM institutions WHERE id = $1::uuid",
            IDS["institution"],
        )
        user_rows = await conn.fetch(
            """
            SELECT email, role
            FROM users
            WHERE institution_id = $1::uuid
              AND email = ANY($2::text[])
            ORDER BY email
            """,
            IDS["institution"],
            [ADMIN_EMAIL, CASHIER_EMAIL],
        )
        users = {row["email"]: row["role"] for row in user_rows}

        program = await conn.fetchrow(
            """
            SELECT id, name_cs, status, is_published
            FROM programs
            WHERE id = $1::uuid AND institution_id = $2::uuid
            """,
            IDS["program"],
            IDS["institution"],
        )

        school_contact = await conn.fetchrow(
            """
            SELECT s.id AS school_id, sc.id AS contact_id, sc.email
            FROM schools s
            JOIN school_contacts sc ON sc.school_id = s.id
            WHERE s.id = $1::uuid
              AND s.institution_id = $2::uuid
              AND sc.email = $3
            """,
            IDS["school"],
            IDS["institution"],
            SCHOOL_EMAIL,
        )

        reservation = await conn.fetchrow(
            """
            SELECT r.id, r.program_id, r.school_id, r.status
            FROM reservations r
            WHERE r.id = $1::uuid
              AND r.institution_id = $2::uuid
              AND r.program_id = $3::uuid
            """,
            IDS["reservation"],
            IDS["institution"],
            IDS["program"],
        )

        event_date = await conn.fetchrow(
            """
            SELECT e.id AS event_id, ed.id AS date_id, e.registration_deadline,
                   ed.registration_deadline_override, ed.start_datetime, ed.end_datetime
            FROM events e
            JOIN event_dates ed ON ed.event_id = e.id
            WHERE e.id = $1::uuid
              AND e.institution_id = $2::uuid
              AND ed.id = $3::uuid
            """,
            IDS["event"],
            IDS["institution"],
            IDS["event_date"],
        )

        mailing = await conn.fetchrow(
            """
            SELECT mc.id AS campaign_id, mc.status,
                   count(DISTINCT mcp.id) AS program_links,
                   count(DISTINCT mcr.id) AS recipients,
                   count(DISTINCT mrp.id) AS recipient_program_links
            FROM mailing_campaigns mc
            LEFT JOIN mailing_campaign_programs mcp ON mcp.campaign_id = mc.id
            LEFT JOIN mailing_campaign_recipients mcr ON mcr.campaign_id = mc.id
            LEFT JOIN mailing_recipient_programs mrp ON mrp.recipient_id = mcr.id
            WHERE mc.id = $1::uuid
              AND mc.institution_id = $2::uuid
            GROUP BY mc.id, mc.status
            """,
            IDS["mailing_campaign"],
            IDS["institution"],
        )

        event_date_valid = False
        if event_date:
            event_date_valid = (
                event_date["end_datetime"] > event_date["start_datetime"]
                and event_date["registration_deadline_override"] < event_date["start_datetime"]
            )

        checks = {
            "institution_present": bool(institution),
            "users_present": users.get(ADMIN_EMAIL) == "admin" and users.get(CASHIER_EMAIL) == "pokladni",
            "program_present": bool(program and program["status"] == "active" and program["is_published"] is True),
            "school_and_contact_present": bool(school_contact),
            "reservation_linked": bool(reservation and str(reservation["school_id"]) == IDS["school"] and reservation["status"] == "confirmed"),
            "event_and_date_valid": event_date_valid,
            "mailing_draft_linked": bool(
                mailing
                and mailing["status"] == "draft"
                and mailing["program_links"] >= 1
                and mailing["recipients"] >= 1
                and mailing["recipient_program_links"] >= 1
            ),
        }
        details = {
            "institution_id": IDS["institution"],
            "admin_email": ADMIN_EMAIL,
            "cashier_email": CASHIER_EMAIL,
            "booking_path": f"/booking/{IDS['institution']}",
            "mailing_campaign_id": IDS["mailing_campaign"],
        }
        return build_report(checks, details)
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Optional JSON output path. The report never includes credentials.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
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
