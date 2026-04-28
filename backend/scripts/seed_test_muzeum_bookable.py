"""
Idempotent enhancement of Test Muzeum so booking flow is fully testable end-to-end.

Goals:
  • Each ACTIVE/PUBLISHED program has 4 time_blocks (morning + afternoon)
  • Each ACTIVE/PUBLISHED program has Mon-Fri available_days
  • Each ACTIVE/PUBLISHED program is bookable from min_days=1 day ahead, up to 180 days
  • All 3 active programs use NO lecturer collision (so they don't depend on lecturer schedules)
  • Programs span end_date well into the future
  • Print a "test booking URL" for the most permissive program

Run:  python /app/backend/scripts/seed_test_muzeum_bookable.py
"""
import asyncio
import os
import sys
from datetime import date, timedelta

import asyncpg

INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"

GOOD_TIME_BLOCKS = ["09:00-10:30", "10:45-12:15", "13:00-14:30", "14:45-16:15"]
GOOD_AVAILABLE_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]


async def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Fall back to backend/.env
        env_path = "/app/backend/.env"
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("DATABASE_URL="):
                    db_url = line.split("=", 1)[1].strip().strip('"')
                    break
    if not db_url:
        print("✗ DATABASE_URL is not set", file=sys.stderr)
        sys.exit(1)

    conn = await asyncpg.connect(db_url, statement_cache_size=0)

    progs = await conn.fetch(
        """SELECT id, name_cs, status, is_published FROM programs
           WHERE institution_id=$1 AND deleted_at IS NULL
           ORDER BY name_cs""",
        INSTITUTION_ID,
    )
    print(f"┌─ Test Muzeum — {len(progs)} programs found")

    end_date = date.today() + timedelta(days=365)
    updated_active = []
    for p in progs:
        if p["status"] != "active" or not p["is_published"]:
            print(f"│  · skip   {p['name_cs']}  (not active/published)")
            continue
        await conn.execute(
            """UPDATE programs SET
                  time_blocks = $1::jsonb,
                  available_days = $2,
                  min_days_before_booking = 1,
                  max_days_before_booking = 180,
                  start_date = NULL,
                  end_date = $3,
                  collision_resources = '[]'::jsonb,
                  collision_lecturer_ids = '[]'::jsonb,
                  assigned_lecturer_id = NULL,
                  updated_at = NOW()
               WHERE id = $4""",
            '["09:00-10:30","10:45-12:15","13:00-14:30","14:45-16:15"]',
            ["monday", "tuesday", "wednesday", "thursday", "friday"],
            end_date,
            p["id"],
        )
        print(f"│  ✓ update {p['name_cs']}  → 4 time_blocks · Mon-Fri · 1–180 d")
        updated_active.append(p)

    print(f"└─ {len(updated_active)} active programs are now fully bookable.\n")

    if updated_active:
        # Print a few test URLs for QA / docs
        print("Test URLs (open in browser to test booking flow):")
        for p in updated_active[:3]:
            print(f"  /booking/{INSTITUTION_ID}  -> pick '{p['name_cs']}' -> next month")

    # Show next 5 bookable weekdays for quick smoke test
    today = date.today()
    next_dates = []
    d = today + timedelta(days=1)
    while len(next_dates) < 5:
        if d.weekday() < 5:
            next_dates.append(d.isoformat())
        d += timedelta(days=1)
    print(f"\nNext 5 bookable weekdays: {', '.join(next_dates)}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
