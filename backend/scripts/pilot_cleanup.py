"""
Pilot-readiness cleanup — removes clearly-test data while preserving:
  - Test Muzeum (669e71b2…)   — canonical demo data
  - Galerie U Zlatého kohouta  — realistic showcase institution
  - Budeživo Platform          — superadmin institution
  - All real institutions (galerie@ogl.cz, lidice-memorial.cz, gask.cz…)

Deletes:
  - TEST_DeleteInst_*, TEST_FreePlan_*, Duplicate Test, Testovací Muzeum Supabase
  - Users test@budezivo.cz, test-kolega@example.com, invited_*@budezivo.cz (name="Test Invited User")
  - Reservations whose contact_email matches test patterns
  - Schools matching TEST_*, ZŠ Testovací, Load Test School #N
  - Duplicate event "Příměstský tábor Léto 2026" (kept "Příměstský tábor – Léto 2026")
"""
import asyncio
import os
import sys

import asyncpg

TEST_INSTITUTION_IDS = [
    "7ea0fc1a-19da-4c13-a8f9-a9700cf3a100",  # Testovací Muzeum Supabase
    "86b1837e-00e6-40a6-bc8b-74d50be94ee6",  # Testovací Muzeum Supabase (duplicate)
    "d9632e24-8c41-4d87-9f29-58ab27d9c5db",  # Duplicate Test
    "6f8fbf48-d7d3-4f09-8cde-2c0f8a5a0b3d",  # TEST_DeleteInst_26339f19
    "8a0c0c1f-b4f0-40bf-9aaa-d3a036fa61ba",  # TEST_FreePlan_ad6048a8
    "c486fbe4-6c07-436a-bdc6-de41c81ecbaa",  # TEST_FreePlan_check3
    "2c1b6ddb-cc3a-46ef-ac32-1c5e3d7b8a29",  # TEST_FreePlan_352b9c6f
]


async def main():
    db = os.environ.get("DATABASE_URL")
    if not db:
        for line in open("/app/backend/.env"):
            if line.startswith("DATABASE_URL="):
                db = line.split("=", 1)[1].strip().strip('"')
                break
    conn = await asyncpg.connect(db, statement_cache_size=0)

    # --- Resolve real test institution IDs by name (safer than hard-coding) ---
    rows = await conn.fetch("""
        SELECT id, name FROM institutions
        WHERE name ILIKE 'TEST\\_%' ESCAPE '\\'
           OR name ILIKE 'Testovací Muzeum Supabase'
           OR name = 'Duplicate Test'
    """)
    institution_ids = [r["id"] for r in rows]
    print(f"┌─ Will remove {len(institution_ids)} test institutions:")
    for r in rows: print(f"│   · {r['name']}  [{str(r['id'])[:8]}]")

    # --- Cascade delete via FK ON DELETE CASCADE (programs, reservations, users, settings…) ---
    if institution_ids:
        res = await conn.execute(
            "DELETE FROM institutions WHERE id = ANY($1::uuid[])",
            institution_ids,
        )
        print(f"│  ✓ {res}")

    # --- Test reservations on surviving institutions ---
    # Only reservations with CLEARLY test emails/names (TEST_* pattern)
    n = await conn.fetchval("""
        DELETE FROM reservations
        WHERE contact_email ILIKE 'TEST\\_%' ESCAPE '\\'
           OR contact_email ILIKE '%@example.com'
           OR contact_email ILIKE '%@example.cz'
           OR school_name ILIKE 'TEST\\_%' ESCAPE '\\'
           OR school_name ILIKE 'ZŠ Testovací%'
           OR school_name ILIKE 'Load Test School%'
           OR contact_name ILIKE 'TEST\\_%' ESCAPE '\\'
        RETURNING 1
    """) or 0
    # asyncpg fetchval returns only 1 row; use execute for row count
    res = await conn.execute("""
        DELETE FROM reservations
        WHERE contact_email ILIKE 'TEST\\_%' ESCAPE '\\'
           OR contact_email ILIKE '%@example.com'
           OR contact_email ILIKE '%@example.cz'
           OR school_name ILIKE 'TEST\\_%' ESCAPE '\\'
           OR school_name ILIKE 'ZŠ Testovací%'
           OR school_name ILIKE 'Load Test School%'
           OR contact_name ILIKE 'TEST\\_%' ESCAPE '\\'
    """)
    print(f"├─ Test reservations: {res}")

    # --- Test schools ---
    res = await conn.execute("""
        DELETE FROM schools
        WHERE name ILIKE 'TEST\\_%' ESCAPE '\\'
           OR name ILIKE 'ZŠ Testovací%'
           OR name ILIKE 'Load Test School%'
           OR email ILIKE '%@example.com'
           OR email ILIKE '%@example.cz'
    """)
    print(f"├─ Test schools: {res}")

    # --- Test users on surviving institutions ---
    # SOFT delete (set deleted_at) — avoids FK cascade hell (audit logs, email templates, etc.).
    # Our code already filters by deleted_at IS NULL so these users become invisible.
    res = await conn.execute("""
        UPDATE users
        SET deleted_at = NOW()
        WHERE (email IN ('test@budezivo.cz', 'test-kolega@example.com')
               OR email ILIKE 'invited\\_%@budezivo.cz' ESCAPE '\\')
          AND deleted_at IS NULL
    """)
    print(f"├─ Test users (soft delete): {res}")

    # --- Duplicate "Příměstský tábor Léto 2026" (without hyphen) ---
    dups = await conn.fetch("""
        SELECT id, name FROM events
        WHERE name = 'Příměstský tábor Léto 2026' AND is_archived = FALSE
    """)
    if dups:
        ids = [r["id"] for r in dups]
        # Dependencies: event_dates / event_applications (CASCADE)
        res = await conn.execute("DELETE FROM events WHERE id = ANY($1::uuid[])", ids)
        print(f"├─ Duplicate events removed: {res}")

    # --- Clean up teacher_login_attempts so no leftover lockouts ---
    await conn.execute("DELETE FROM teacher_login_attempts")
    print("├─ teacher_login_attempts cleared")

    # --- Show final counts ---
    cnt_inst = await conn.fetchval("SELECT count(*) FROM institutions WHERE deleted_at IS NULL")
    cnt_usr  = await conn.fetchval("SELECT count(*) FROM users WHERE deleted_at IS NULL")
    cnt_prog = await conn.fetchval("SELECT count(*) FROM programs WHERE deleted_at IS NULL")
    cnt_res  = await conn.fetchval("SELECT count(*) FROM reservations")
    cnt_sch  = await conn.fetchval("SELECT count(*) FROM schools")
    cnt_evt  = await conn.fetchval("SELECT count(*) FROM events WHERE is_archived=false")
    print("└─ Final counts:")
    print(f"     institutions:   {cnt_inst}")
    print(f"     users:          {cnt_usr}")
    print(f"     programs:       {cnt_prog}")
    print(f"     reservations:   {cnt_res}")
    print(f"     schools:        {cnt_sch}")
    print(f"     events:         {cnt_evt}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
