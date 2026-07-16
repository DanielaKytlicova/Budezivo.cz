"""Ad-hoc test for the visit-reminder scheduler job (Phase 1)."""
import asyncio
from datetime import datetime, timezone, timedelta, date

from sqlalchemy import select, delete
from database.supabase import AsyncSessionLocal
from database.models import Reservation, Institution, Program, EmailLog
from scheduler import subtract_working_days, process_visit_reminders


def test_working_days():
    # Monday 2026-08-17 → 2 working days before → Thursday 2026-08-13
    assert subtract_working_days(date(2026, 8, 17), 2) == date(2026, 8, 13), subtract_working_days(date(2026, 8, 17), 2)
    # Tuesday 2026-08-18 → Friday 2026-08-14
    assert subtract_working_days(date(2026, 8, 18), 2) == date(2026, 8, 14), subtract_working_days(date(2026, 8, 18), 2)
    # Wednesday 2026-08-19 → Monday 2026-08-17
    assert subtract_working_days(date(2026, 8, 19), 2) == date(2026, 8, 17)
    print("OK working-day calc: Mon→Thu, Tue→Fri, Wed→Mon")


async def main():
    test_working_days()
    async with AsyncSessionLocal() as db:
        inst = (await db.execute(select(Institution).where(Institution.name.ilike('%Budeživo%')))).scalars().first()
        if not inst:
            inst = (await db.execute(select(Institution))).scalars().first()
        prog = (await db.execute(select(Program).where(Program.institution_id == inst.id))).scalars().first()
        print(f"Institution: {inst.name} | reminder setting: {(inst.notification_settings or {}).get('customer',{}).get('visit_reminder')}")

        # A visit date whose reminder day (2 working days before) is today.
        today = datetime.now(timezone.utc).date()
        # find a future date d such that subtract_working_days(d,2)==today
        visit = today
        for i in range(1, 12):
            cand = today + timedelta(days=i)
            if subtract_working_days(cand, 2) == today and cand.weekday() < 5:
                visit = cand
                break
        print(f"Test visit date (reminder due today): {visit}")

        r = Reservation(
            institution_id=inst.id, program_id=prog.id,
            date=visit.strftime('%Y-%m-%d'), time_block='10:00-11:00',
            school_name='TEST Reminder', group_type='zs1_7_12', num_students=20,
            contact_name='Test Kontakt', contact_email='reminder-test@example.com',
            contact_phone='+420111222333', status='confirmed',
        )
        db.add(r)
        await db.commit()
        rid = r.id
        print(f"Created reservation {rid}")

    # Run job (first pass)
    await process_visit_reminders()

    async with AsyncSessionLocal() as db:
        r = (await db.execute(select(Reservation).where(Reservation.id == rid))).scalars().first()
        logs = (await db.execute(select(EmailLog).where(EmailLog.reservation_id == rid))).scalars().all()
        print(f"After pass 1: sent_at={r.visit_reminder_sent_at} last_attempt={r.visit_reminder_last_attempt_at} error={r.visit_reminder_error!r} logs={len(logs)}")
        attempted = r.visit_reminder_last_attempt_at is not None
        print("PASS attempted+logged" if attempted and logs else "FAIL: not attempted")

    # Idempotency: force sent_at, run again → no new log
    async with AsyncSessionLocal() as db:
        r = (await db.execute(select(Reservation).where(Reservation.id == rid))).scalars().first()
        r.visit_reminder_sent_at = datetime.now(timezone.utc)
        await db.commit()
    await process_visit_reminders()
    async with AsyncSessionLocal() as db:
        logs2 = (await db.execute(select(EmailLog).where(EmailLog.reservation_id == rid))).scalars().all()
        print(f"After pass 2 (already sent): logs={len(logs2)} (should equal pass1 count → no duplicate)")

    # cleanup
    async with AsyncSessionLocal() as db:
        await db.execute(delete(EmailLog).where(EmailLog.reservation_id == rid))
        await db.execute(delete(Reservation).where(Reservation.id == rid))
        await db.commit()
        print("cleanup done")


if __name__ == '__main__':
    asyncio.run(main())
