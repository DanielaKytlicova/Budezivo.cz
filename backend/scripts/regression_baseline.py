"""Generate a read-only baseline report for an isolated regression database.

The script intentionally uses the ad-hoc script safety guard. It will not accept
DATABASE_URL and refuses the known production Supabase project ref.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    from scripts.safety import asyncpg_url, require_test_database_url
except ModuleNotFoundError:
    from safety import asyncpg_url, require_test_database_url


BASELINE_TABLES = (
    "alembic_version",
    "institutions",
    "users",
    "programs",
    "reservations",
    "schools",
    "contacts",
    "mailing_campaigns",
    "events",
    "event_dates",
)

REQUIRED_COLUMNS = {
    "events": ("registration_deadline",),
    "event_dates": ("registration_deadline_override",),
}


def build_summary(
    *,
    alembic_versions: List[str],
    table_counts: Dict[str, Optional[int]],
    columns: Dict[str, Set[str]],
    write_probe: str,
) -> Dict:
    """Build a deterministic status report from collected database facts."""
    missing_tables = [table for table, count in table_counts.items() if count is None]
    missing_columns = {
        table: [column for column in expected if column not in columns.get(table, set())]
        for table, expected in REQUIRED_COLUMNS.items()
    }
    missing_columns = {table: cols for table, cols in missing_columns.items() if cols}

    checks = {
        "alembic_version_present": bool(alembic_versions),
        "required_tables_present": not missing_tables,
        "required_columns_present": not missing_columns,
        "write_probe_rolled_back": write_probe == "rolled_back",
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if all(checks.values()) else "attention_required",
        "checks": checks,
        "alembic_versions": alembic_versions,
        "table_counts": table_counts,
        "missing_tables": missing_tables,
        "missing_columns": missing_columns,
        "write_probe": write_probe,
    }


async def collect_report() -> dict:
    db_url = asyncpg_url(require_test_database_url("regression_baseline.py"))

    import asyncpg

    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    try:
        existing_tables = set(
            await conn.fetchval(
                """
                SELECT array_agg(table_name::text)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = ANY($1::text[])
                """,
                list(BASELINE_TABLES),
            )
            or []
        )

        table_counts: Dict[str, Optional[int]] = {}
        for table in BASELINE_TABLES:
            if table not in existing_tables:
                table_counts[table] = None
                continue
            table_counts[table] = await conn.fetchval(f'SELECT count(*) FROM "{table}"')

        alembic_versions = []
        if "alembic_version" in existing_tables:
            alembic_versions = [
                row["version_num"]
                for row in await conn.fetch("SELECT version_num FROM alembic_version ORDER BY version_num")
            ]

        column_rows = await conn.fetch(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = ANY($1::text[])
            """,
            list(REQUIRED_COLUMNS.keys()),
        )
        columns: Dict[str, Set[str]] = {}
        for row in column_rows:
            columns.setdefault(row["table_name"], set()).add(row["column_name"])

        tx = conn.transaction()
        await tx.start()
        try:
            await conn.execute("CREATE TEMP TABLE budezivo_regression_write_probe(id integer)")
            await conn.execute("INSERT INTO budezivo_regression_write_probe(id) VALUES (1)")
            inserted = await conn.fetchval("SELECT count(*) FROM budezivo_regression_write_probe")
            write_probe = "insert_failed" if inserted != 1 else "rolled_back"
        finally:
            await tx.rollback()

        return build_summary(
            alembic_versions=alembic_versions,
            table_counts=table_counts,
            columns=columns,
            write_probe=write_probe,
        )
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        help="Optional JSON output path. The report never includes database credentials.",
    )
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


if __name__ == "__main__":
    asyncio.run(main())
