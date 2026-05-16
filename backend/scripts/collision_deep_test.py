"""
Deep collision-logic test.
Creates controlled fixture programs in the gallery institution, runs scenarios,
reports real behavior vs expected.
"""
import asyncio, os, sys, uuid, random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, and_
from database.models import (
    Program, Room, User, Reservation, AvailabilityBlock, LecturerAvailability,
    Institution,
)

API = "https://school-crm-pilot.preview.emergentagent.com"
DB_URL = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+asyncpg://")
INST = "eefb9cbf-52bf-4e20-9418-5b2f659f8d23"  # Galerie U Zlatého kohouta

RESULTS = []


def log(name, actual, expected=None, detail=""):
    mark = "PASS" if (expected is None or actual == expected) else "FAIL"
    RESULTS.append({"name": name, "actual": actual, "expected": expected,
                    "result": mark, "detail": detail})


async def main():
    engine = create_async_engine(DB_URL, connect_args={"statement_cache_size": 0})
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # ─── Fetch fixtures from DB ───
    async with Session() as db:
        rooms = (await db.execute(select(Room).where(Room.institution_id == uuid.UUID(INST)))).scalars().all()
        R_MAIN = rooms[0].id
        R_ATE = rooms[1].id
        users = (await db.execute(
            select(User).where(and_(User.institution_id == uuid.UUID(INST), User.role == "lektor"))
        )).scalars().all()
        L1, L2 = users[0].id, users[1].id
        L1_name, L2_name = users[0].name, users[1].name

        # Create 4 controlled fixture programs (idempotent: delete old ones first)
        await db.execute(delete(Program).where(and_(
            Program.institution_id == uuid.UUID(INST),
            Program.name_cs.like("COL_TEST_%")
        )))
        await db.commit()

        programs = {
            "NONPAR_MAIN_L1": Program(
                id=uuid.uuid4(), institution_id=uuid.UUID(INST),
                name_cs="COL_TEST_NonParallel_Main_L1", name_en="x",
                description_cs="x", description_en="x",
                duration=60, age_group="zs1_7_12", target_groups=["zs1_7_12"],
                min_capacity=5, max_capacity=30, target_group="schools",
                status="active", is_published=True,
                available_days=["monday","tuesday","wednesday","thursday","friday","saturday","sunday"],
                time_blocks=["09:00-10:00"],
                min_days_before_booking=1, max_days_before_booking=365,
                preparation_time=0, cleanup_time=0,
                allow_parallel=False,
                collision_resources=["lecturer","room"],
                assigned_lecturer_id=L1, room_id=R_MAIN,
                feedback_enabled=False,
            ),
            "PAR_MAIN_L1": Program(
                id=uuid.uuid4(), institution_id=uuid.UUID(INST),
                name_cs="COL_TEST_Parallel_Main_L1", name_en="x",
                description_cs="x", description_en="x",
                duration=60, age_group="zs1_7_12", target_groups=["zs1_7_12"],
                min_capacity=5, max_capacity=30, target_group="schools",
                status="active", is_published=True,
                available_days=["monday","tuesday","wednesday","thursday","friday","saturday","sunday"],
                time_blocks=["09:00-10:00"],
                min_days_before_booking=1, max_days_before_booking=365,
                preparation_time=0, cleanup_time=0,
                allow_parallel=True,
                collision_resources=["lecturer","room"],
                assigned_lecturer_id=L1, room_id=R_MAIN,
                feedback_enabled=False,
            ),
            "PAR_ATE_L2": Program(
                id=uuid.uuid4(), institution_id=uuid.UUID(INST),
                name_cs="COL_TEST_Parallel_Atelier_L2", name_en="x",
                description_cs="x", description_en="x",
                duration=60, age_group="zs1_7_12", target_groups=["zs1_7_12"],
                min_capacity=5, max_capacity=30, target_group="schools",
                status="active", is_published=True,
                available_days=["monday","tuesday","wednesday","thursday","friday","saturday","sunday"],
                time_blocks=["09:00-10:00"],
                min_days_before_booking=1, max_days_before_booking=365,
                preparation_time=0, cleanup_time=0,
                allow_parallel=True,
                collision_resources=["lecturer","room"],
                assigned_lecturer_id=L2, room_id=R_ATE,
                feedback_enabled=False,
            ),
            "PAR_MAIN_L2": Program(
                id=uuid.uuid4(), institution_id=uuid.UUID(INST),
                name_cs="COL_TEST_Parallel_Main_L2", name_en="x",
                description_cs="x", description_en="x",
                duration=60, age_group="zs1_7_12", target_groups=["zs1_7_12"],
                min_capacity=5, max_capacity=30, target_group="schools",
                status="active", is_published=True,
                available_days=["monday","tuesday","wednesday","thursday","friday","saturday","sunday"],
                time_blocks=["09:00-10:00"],
                min_days_before_booking=1, max_days_before_booking=365,
                preparation_time=0, cleanup_time=0,
                allow_parallel=True,
                collision_resources=["lecturer","room"],
                assigned_lecturer_id=L2, room_id=R_MAIN,
                feedback_enabled=False,
            ),
        }
        for p in programs.values():
            db.add(p)
        await db.commit()
        pid = {k: str(v.id) for k, v in programs.items()}

    # ─── Helpers ───
    base_offset = 400 + random.randint(0, 40)
    def day(n):
        return (datetime.now() + timedelta(days=base_offset + n)).strftime("%Y-%m-%d")

    def payload(prog_id, d, tb, email="test@example.com", name="ZŠ Test"):
        return {
            "program_id": prog_id, "date": d, "time_block": tb,
            "school_name": name, "group_type": "zs1_7_12",
            "age_or_class": "5.A",
            "num_students": 10, "num_teachers": 1,
            "contact_name": "Test", "contact_email": email,
            "contact_phone": "+420 600 111 222",
            "gdpr_consent": True, "terms_accepted": True,
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        async def book(prog_key, d, tb, expect_status=200, scenario=""):
            r = await client.post(f"{API}/api/bookings/public/{INST}",
                                  json=payload(pid[prog_key], d, tb))
            detail = r.json().get("detail", r.text[:100]) if r.headers.get("content-type","").startswith("application/json") else r.text[:100]
            log(scenario, r.status_code, expect_status,
                f"{prog_key} {d} {tb} → {r.status_code}  msg={detail[:120]}")
            return r

        # ───────────────────────────────────────────────────────────────
        # SCENARIO 1: NON-PARALLEL BLOCKS EVERYTHING ON SAME TIME
        # ───────────────────────────────────────────────────────────────
        d1 = day(0)
        # Anchor: NonParallel program books 09:00-10:00
        await book("NONPAR_MAIN_L1", d1, "09:00-10:00", 200, "1.a-anchor-nonparallel-created")
        # 1.1 Same time, SAME space, SAME lecturer → expect 409
        await book("NONPAR_MAIN_L1", d1, "09:00-10:00", 409, "1.1-nonpar-same-time-same-space-same-lecturer")
        # 1.2 Same time, DIFFERENT space, DIFFERENT lecturer (parallel program) → expect 409 (non-par anchor blocks all)
        await book("PAR_ATE_L2", d1, "09:00-10:00", 409, "1.2-parprog-vs-nonpar-anchor-diff-room-lecturer")
        # 1.3 Same time, SAME space, DIFFERENT lecturer (parallel program L2 in MAIN) → expect 409
        await book("PAR_MAIN_L2", d1, "09:00-10:00", 409, "1.3-parprog-vs-nonpar-anchor-same-room-diff-lecturer")

        # ───────────────────────────────────────────────────────────────
        # SCENARIO 2: PARALLEL vs PARALLEL — resource checks decide
        # ───────────────────────────────────────────────────────────────
        d2 = day(5)
        await book("PAR_MAIN_L1", d2, "09:00-10:00", 200, "2.a-anchor-parallel-created")
        # 2.1 Same time, SAME space, different lecturer (anchor L1 Main vs PAR_MAIN_L2)
        #     → room collision expected
        await book("PAR_MAIN_L2", d2, "09:00-10:00", 409, "2.1-par-vs-par-same-room-diff-lecturer-expect-room-collision")
        # 2.2 Same time, DIFFERENT space, DIFFERENT lecturer → should succeed
        await book("PAR_ATE_L2", d2, "09:00-10:00", 200, "2.2-par-vs-par-diff-room-diff-lecturer-allowed")

        # ───────────────────────────────────────────────────────────────
        # SCENARIO 3: SAME-LECTURER COLLISION (both parallel, different rooms)
        # ───────────────────────────────────────────────────────────────
        # Create a 4th program: parallel, ATE room, lecturer L1 (same as PAR_MAIN_L1)
        async with Session() as db:
            p_ate_l1 = Program(
                id=uuid.uuid4(), institution_id=uuid.UUID(INST),
                name_cs="COL_TEST_Parallel_Atelier_L1", name_en="x",
                description_cs="x", description_en="x",
                duration=60, age_group="zs1_7_12", target_groups=["zs1_7_12"],
                min_capacity=5, max_capacity=30, target_group="schools",
                status="active", is_published=True,
                available_days=["monday","tuesday","wednesday","thursday","friday","saturday","sunday"],
                time_blocks=["09:00-10:00"],
                min_days_before_booking=1, max_days_before_booking=365,
                preparation_time=0, cleanup_time=0,
                allow_parallel=True,
                collision_resources=["lecturer","room"],
                assigned_lecturer_id=L1, room_id=R_ATE,
                feedback_enabled=False,
            )
            db.add(p_ate_l1)
            await db.commit()
            pid["PAR_ATE_L1"] = str(p_ate_l1.id)

        d3 = day(10)
        await book("PAR_MAIN_L1", d3, "09:00-10:00", 200, "3.a-anchor-par-main-l1")
        # 3.1 Parallel Atelier L1 (different room, same lecturer) → should be rejected (lecturer collision)
        await book("PAR_ATE_L1", d3, "09:00-10:00", 409, "3.1-par-diff-room-same-lecturer-expect-lecturer-collision")

        # ───────────────────────────────────────────────────────────────
        # SCENARIO 4: MANUAL AVAILABILITY BLOCK for lecturer (AvailabilityBlock table)
        # ───────────────────────────────────────────────────────────────
        d4 = day(15)
        async with Session() as db:
            year, month, d_day = map(int, d4.split("-"))
            blk = AvailabilityBlock(
                id=uuid.uuid4(), user_id=L1, institution_id=uuid.UUID(INST),
                start_time=datetime(year, month, d_day, 8, 0, tzinfo=timezone.utc),
                end_time=datetime(year, month, d_day, 12, 0, tzinfo=timezone.utc),
                source="manual", title="COL_TEST_manual_block",
                override=False,
            )
            db.add(blk)
            await db.commit()

        # 4.1 Public booking for program with blocked lecturer → NOT checked at booking time
        #     (collision_service check_booking_collision does NOT call check_availability_blocks!)
        r = await book("PAR_MAIN_L1", d4, "09:00-10:00", 200, "4.1-booking-ignores-lecturer-availability-block")

        # 4.2 Manual assign test — assign L1 to a fresh booking where L1 has block
        #     create fresh booking with no lecturer (program P doesn't have assigned lecturer - but our progs all do)
        #     We'll use the existing one and try to REassign same lecturer → should trigger assignment check
        book_id = r.json().get("id") if r.status_code == 200 else None
        if book_id:
            r2 = await client.post(
                f"{API}/api/bookings/{book_id}/assign-lecturer-admin",
                json={"lecturer_id": str(L1)},
                headers={"Authorization": f"Bearer {(await get_token(client))}"},
            )
            detail = r2.text[:200]
            log("4.2-manual-assign-detects-availability-block", r2.status_code, 409,
                f"assign L1 with manual block → {r2.status_code} {detail[:150]}")

        # ───────────────────────────────────────────────────────────────
        # SCENARIO 5: EDGE OVERLAPS (on non-parallel anchor)
        # ───────────────────────────────────────────────────────────────
        d5 = day(20)
        await book("NONPAR_MAIN_L1", d5, "09:00-10:00", 200, "5.a-anchor-nonpar")
        # 5.1 Booking touches boundary exactly (10:00-11:00) → should succeed (no overlap)
        await book("PAR_ATE_L2", d5, "10:00-11:00", 200, "5.1-exact-boundary-touch-allowed")
        # 5.2 1-min overlap (09:59-10:59 would overlap by 1 min) → should be rejected
        await book("PAR_ATE_L2", d5, "09:59-10:59", 409, "5.2-one-minute-overlap-rejected")
        # 5.3 5-min overlap
        d5b = day(22)
        await book("NONPAR_MAIN_L1", d5b, "09:00-10:00", 200, "5.3a-anchor-for-5min")
        await book("PAR_ATE_L2", d5b, "09:55-10:55", 409, "5.3b-five-minute-overlap-rejected")

        # ───────────────────────────────────────────────────────────────
        # SCENARIO 6: PENDING vs CONFIRMED collision (should both count)
        # ───────────────────────────────────────────────────────────────
        d6 = day(25)
        # First booking: pending (default)
        r6a = await book("NONPAR_MAIN_L1", d6, "09:00-10:00", 200, "6.a-first-pending-created")
        # Second booking: same time → should be rejected even though anchor is pending
        await book("NONPAR_MAIN_L1", d6, "09:00-10:00", 409, "6.b-pending-vs-pending-rejected")

        # ───────────────────────────────────────────────────────────────
        # SCENARIO 7: CANCELLED reservations MUST NOT block
        # ───────────────────────────────────────────────────────────────
        d7 = day(30)
        r7a = await book("NONPAR_MAIN_L1", d7, "09:00-10:00", 200, "7.a-anchor-to-cancel")
        # cancel it via direct DB
        if r7a.status_code == 200:
            async with Session() as db:
                await db.execute(
                    Reservation.__table__.update()
                    .where(Reservation.id == uuid.UUID(r7a.json()["id"]))
                    .values(status="cancelled", cancelled_at=datetime.now(timezone.utc))
                )
                await db.commit()
        # Now the same slot should be free
        await book("NONPAR_MAIN_L1", d7, "09:00-10:00", 200, "7.b-slot-freed-after-cancel")

    # ─── Cleanup ───
    async with Session() as db:
        await db.execute(delete(Reservation).where(and_(
            Reservation.institution_id == uuid.UUID(INST),
            Reservation.school_name.in_(["ZŠ Test"])
        )))
        await db.execute(delete(AvailabilityBlock).where(and_(
            AvailabilityBlock.institution_id == uuid.UUID(INST),
            AvailabilityBlock.title == "COL_TEST_manual_block"
        )))
        await db.execute(delete(Program).where(and_(
            Program.institution_id == uuid.UUID(INST),
            Program.name_cs.like("COL_TEST_%")
        )))
        await db.commit()

    # ─── REPORT ───
    passes = sum(1 for r in RESULTS if r["result"] == "PASS")
    fails = sum(1 for r in RESULTS if r["result"] == "FAIL")
    print(f"\n========== COLLISION-LOGIC DEEP TEST — {passes} PASS / {fails} FAIL ==========")
    for r in RESULTS:
        print(f"  [{r['result']}] {r['name']}: got={r['actual']} expect={r['expected']}  {r['detail']}")


async def get_token(client):
    r = await client.post(f"{API}/api/auth/login",
                          json={"email": "galerie@budezivo.cz", "password": "Galerie2026!"})
    return r.json().get("access_token") or r.json().get("token")


if __name__ == "__main__":
    asyncio.run(main())
