"""
Seed a realistic demo GALLERY institution with programs, lecturers, rooms,
availability, reservations, feedback and intentional conflicts.
Single-run bulk seed — minimal round-trips (one commit per table).
"""
import asyncio, os, sys, uuid, random
from datetime import datetime, timedelta, timezone, date
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import delete, select

from database.models import (
    Institution, User, Room, Program, Reservation, Feedback,
    LecturerAvailability, AvailabilityBlock, ThemeSetting,
)
from core.security import hash_password

DB_URL = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+asyncpg://")
RNG = random.Random(42)

GALLERY_EMAIL = "galerie@budezivo.cz"
GALLERY_PASSWORD = "Galerie2026!"


async def main():
    engine = create_async_engine(DB_URL, connect_args={"statement_cache_size": 0})
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # ---- Clean-up old demo gallery (idempotent) ----
        existing = await db.execute(select(Institution).where(Institution.name == "Galerie U Zlatého kohouta"))
        prev = existing.scalar_one_or_none()
        if prev:
            await db.execute(delete(Institution).where(Institution.id == prev.id))
            await db.commit()

        # ---- Institution ----
        inst = Institution(
            id=uuid.uuid4(),
            name="Galerie U Zlatého kohouta",
            type="gallery",
            country="CZ",
            city="Brno",
            address="Masarykova 14",
            psc="60200",
            ico_dic="28474829",
            phone="+420 515 919 270",
            email=GALLERY_EMAIL,
            website="https://galerie-zlatykohout.cz",
            primary_color="#4A3F7A",
            secondary_color="#D4A574",
            plan="pro",
            plan_status="active",
            plan_activated_by="admin",
            plan_activated_at=datetime.now(timezone.utc),
            plan_expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            programs_limit=30,
            bookings_monthly_limit=500,
            onboarding_completed=True,
        )
        db.add(inst)
        await db.flush()
        inst_id = inst.id

        # ---- Users: admin + 3 lecturers ----
        admin = User(
            id=uuid.uuid4(), institution_id=inst_id, email=GALLERY_EMAIL,
            password_hash=hash_password(GALLERY_PASSWORD),
            name="Jana Procházková", role="admin", status="active",
            gdpr_consent=True, gdpr_consent_date=datetime.now(timezone.utc),
            terms_accepted=True,
        )
        lecturers = [
            User(id=uuid.uuid4(), institution_id=inst_id,
                 email="anna.dvorakova@budezivo.cz", password_hash=hash_password("Lektor2026!"),
                 name="Mgr. Anna Dvořáková", role="lektor", status="active"),
            User(id=uuid.uuid4(), institution_id=inst_id,
                 email="petr.kucera@budezivo.cz", password_hash=hash_password("Lektor2026!"),
                 name="MgA. Petr Kučera", role="lektor", status="active"),
            User(id=uuid.uuid4(), institution_id=inst_id,
                 email="klara.novakova@budezivo.cz", password_hash=hash_password("Lektor2026!"),
                 name="Bc. Klára Nováková", role="lektor", status="active"),
        ]
        db.add_all([admin] + lecturers)
        await db.flush()

        # Theme
        db.add(ThemeSetting(
            id=uuid.uuid4(), institution_id=inst_id,
            primary_color=inst.primary_color, secondary_color=inst.secondary_color,
            accent_color="#E9C46A",
        ))

        # ---- Rooms ----
        rooms = [
            Room(id=uuid.uuid4(), institution_id=inst_id, name="Hlavní výstavní sál",
                 capacity=40, equipment="projektor, plátno, mikrofon"),
            Room(id=uuid.uuid4(), institution_id=inst_id, name="Ateliér",
                 capacity=20, equipment="malířské stojany, stoly, dřezy"),
            Room(id=uuid.uuid4(), institution_id=inst_id, name="Přednáškový sál",
                 capacity=30, equipment="projektor, ozvučení"),
        ]
        db.add_all(rooms)
        await db.flush()
        R_MAIN, R_ATELIER, R_LECTURE = rooms[0].id, rooms[1].id, rooms[2].id
        L1, L2, L3 = lecturers[0].id, lecturers[1].id, lecturers[2].id

        # ---- Programs (8 — some parallel/non-parallel, varied durations) ----
        prog_specs = [
            # (name, age_code, duration, min/max, room, lecturer, parallel, blocks, pricing)
            ("Barvy kolem nás — MŠ", "ms_3_6", 45, 8, 15, R_ATELIER, L3, True,
             ["09:00-09:45", "10:00-10:45"], "Zdarma pro MŠ"),
            ("Barvy kolem nás — I. stupeň ZŠ", "zs1_7_12", 60, 10, 24, R_ATELIER, L3, False,
             ["09:00-10:00", "10:30-11:30"], "30 Kč/žák – pedagog zdarma"),
            ("Moderna v galerii — II. stupeň ZŠ", "zs2_12_15", 90, 12, 25, R_MAIN, L2, False,
             ["09:00-10:30", "11:00-12:30"], "40 Kč/žák"),
            ("Moderna v galerii — SŠ", "ss_14_18", 90, 12, 30, R_MAIN, L2, False,
             ["09:00-10:30", "11:00-12:30", "13:00-14:30"], "40 Kč/žák – pedagog zdarma"),
            ("Experimentální ateliér — II. stupeň ZŠ", "zs2_12_15", 60, 10, 20, R_ATELIER, L1, True,
             ["10:00-11:00", "12:00-13:00"], "50 Kč/žák (materiál v ceně)"),
            ("Experimentální ateliér — Gymnázium", "gym_14_18", 60, 10, 20, R_ATELIER, L1, True,
             ["10:00-11:00", "12:00-13:00"], "50 Kč/žák (materiál v ceně)"),
            ("Komentovaná prohlídka výstavy", "all", 45, 5, 30, R_LECTURE, L2, True,
             ["09:30-10:15", "10:30-11:15", "11:30-12:15", "13:00-13:45"], "20 Kč/osoba"),
            ("Tvůrčí dílna: grafika — I. stupeň ZŠ", "zs1_7_12", 90, 8, 16, R_ATELIER, L3, False,
             ["09:00-10:30", "11:00-12:30"], "60 Kč/žák (tisk v ceně)"),
        ]
        programs = []
        for name, age, dur, mn, mx, room_id, lect_id, par, blocks, pricing in prog_specs:
            tags = [age] if age != "all" else ["ms_3_6", "zs1_7_12", "zs2_12_15", "ss_14_18", "adults"]
            programs.append(Program(
                id=uuid.uuid4(), institution_id=inst_id,
                name_cs=name, name_en=name, description_cs=f"Doprovodný program {name.lower()}.",
                description_en=f"Educational programme: {name}",
                duration=dur, age_group=age, target_groups=tags,
                min_capacity=mn, max_capacity=mx, target_group="schools",
                price=0.0, pricing_info=pricing,
                status="active", is_published=True,
                available_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
                time_blocks=blocks,
                min_days_before_booking=3, max_days_before_booking=120,
                preparation_time=10, cleanup_time=15,
                allow_parallel=par,
                collision_resources=["lecturer", "room"],
                assigned_lecturer_id=lect_id, room_id=room_id,
                feedback_enabled=True,
            ))
        db.add_all(programs)
        await db.flush()

        # ---- Lecturer Availability (recurring + one-off blocks) ----
        recurring = []
        # Anna (L1): Po–Čt 8:00–16:00
        for d in range(0, 4):
            recurring.append(LecturerAvailability(
                id=uuid.uuid4(), lecturer_id=L1, institution_id=inst_id,
                day_of_week=d, start_time="08:00", end_time="16:00", is_recurring=True,
            ))
        # Petr (L2): Po–Pá 9:00–17:00
        for d in range(0, 5):
            recurring.append(LecturerAvailability(
                id=uuid.uuid4(), lecturer_id=L2, institution_id=inst_id,
                day_of_week=d, start_time="09:00", end_time="17:00", is_recurring=True,
            ))
        # Klára (L3): Út–Pá 9:00–15:00
        for d in range(1, 5):
            recurring.append(LecturerAvailability(
                id=uuid.uuid4(), lecturer_id=L3, institution_id=inst_id,
                day_of_week=d, start_time="09:00", end_time="15:00", is_recurring=True,
            ))
        db.add_all(recurring)

        # Manual one-off blocks (2)
        today = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
        blocks = [
            AvailabilityBlock(
                id=uuid.uuid4(), user_id=L1, institution_id=inst_id,
                start_time=today + timedelta(days=10),
                end_time=today + timedelta(days=10, hours=8),
                source="manual", title="Celodenní workshop mimo galerii",
            ),
            AvailabilityBlock(
                id=uuid.uuid4(), user_id=L2, institution_id=inst_id,
                start_time=today + timedelta(days=17, hours=5),
                end_time=today + timedelta(days=17, hours=8),
                source="manual", title="Porada vedení",
            ),
        ]
        db.add_all(blocks)

        # ---- Reservations (40 total) ----
        schools = [
            ("ZŠ Masarykova Brno", "reditel@zs-masarykova.cz", "+420 545 214 112"),
            ("Gymnázium Matyáše Lercha", "info@gml.cz", "+420 543 237 540"),
            ("MŠ Sluníčko Brno", "sekretariat@ms-slunicko.cz", "+420 545 223 909"),
            ("ZŠ Horácké náměstí", "kancelar@zshoracke.cz", "+420 549 212 110"),
            ("SOŠ grafická Brno", "info@sosbrno.cz", "+420 541 321 811"),
            ("ZŠ Sirotkova", "reditelstvi@zssirotkova.cz", "+420 549 272 004"),
            ("Gymnázium Vídeňská", "kancelar@gymnazium-vidno.cz", "+420 544 509 111"),
            ("MŠ Kamarád", "info@ms-kamarad.cz", "+420 545 571 140"),
            ("ZŠ Kotlářská", "reditelna@zs-kotlarska.cz", "+420 541 211 190"),
            ("Gymnázium Slovanské náměstí", "info@gsn-brno.cz", "+420 549 250 320"),
            ("ZŠ Úvoz", "reditel@zsuvoz.cz", "+420 541 513 900"),
            ("MŠ Veslařská", "info@ms-veslarska.cz", "+420 543 211 808"),
        ]
        teachers = [
            ("Mgr. Jana Nováková", "jana.novakova@"),
            ("Mgr. Petra Svobodová", "petra.svobodova@"),
            ("PaedDr. Karel Malý", "karel.maly@"),
            ("Mgr. Tereza Kolářová", "tereza.kolarova@"),
            ("Mgr. Martin Beneš", "martin.benes@"),
            ("Mgr. Eva Horáková", "eva.horakova@"),
            ("Mgr. Daniel Hruška", "daniel.hruska@"),
        ]

        def pick_school():
            sname, semail_domain, sphone = RNG.choice(schools)
            tname, temail_prefix = RNG.choice(teachers)
            return sname, tname, f"{temail_prefix}{semail_domain.split('@')[1]}", sphone

        reservations = []
        # Past: 25 completed
        for i in range(25):
            days_back = RNG.randint(3, 28)
            res_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).date()
            prog = RNG.choice(programs)
            tb = RNG.choice(prog.time_blocks)
            school, teacher, email, phone = pick_school()
            num_students = RNG.randint(prog.min_capacity, prog.max_capacity)
            reservations.append(Reservation(
                id=uuid.uuid4(), institution_id=inst_id, program_id=prog.id,
                date=res_date.isoformat(), time_block=tb,
                school_name=school, group_type=prog.age_group,
                age_or_class=RNG.choice(["3.A", "4.B", "5.A", "7.C", "2.třída", "kvarta", "sexta"]),
                num_students=num_students, num_teachers=RNG.randint(1, 3),
                contact_name=teacher, contact_email=email, contact_phone=phone,
                status="completed",
                confirmed_by=admin.id, confirmed_at=datetime.now(timezone.utc) - timedelta(days=days_back + 2),
                actual_students=num_students - RNG.randint(0, 3), actual_teachers=RNG.randint(1, 2),
                assigned_lecturer_id=prog.assigned_lecturer_id,
                assigned_lecturer_name=next((l.name for l in lecturers if l.id == prog.assigned_lecturer_id), ""),
                gdpr_consent=True, terms_accepted=True,
                created_at=datetime.now(timezone.utc) - timedelta(days=days_back + 5),
            ))

        # Future: 4 confirmed
        for i in range(4):
            days_fwd = RNG.randint(3, 25)
            res_date = (datetime.now(timezone.utc) + timedelta(days=days_fwd)).date()
            prog = RNG.choice(programs)
            tb = RNG.choice(prog.time_blocks)
            school, teacher, email, phone = pick_school()
            num_students = RNG.randint(prog.min_capacity, prog.max_capacity)
            reservations.append(Reservation(
                id=uuid.uuid4(), institution_id=inst_id, program_id=prog.id,
                date=res_date.isoformat(), time_block=tb,
                school_name=school, group_type=prog.age_group,
                num_students=num_students, num_teachers=RNG.randint(1, 2),
                contact_name=teacher, contact_email=email, contact_phone=phone,
                status="confirmed",
                confirmed_by=admin.id, confirmed_at=datetime.now(timezone.utc),
                assigned_lecturer_id=prog.assigned_lecturer_id,
                assigned_lecturer_name=next((l.name for l in lecturers if l.id == prog.assigned_lecturer_id), ""),
                gdpr_consent=True, terms_accepted=True,
            ))

        # Future: 5 pending
        for i in range(5):
            days_fwd = RNG.randint(5, 30)
            res_date = (datetime.now(timezone.utc) + timedelta(days=days_fwd)).date()
            prog = RNG.choice(programs)
            tb = RNG.choice(prog.time_blocks)
            school, teacher, email, phone = pick_school()
            num_students = RNG.randint(prog.min_capacity, prog.max_capacity)
            reservations.append(Reservation(
                id=uuid.uuid4(), institution_id=inst_id, program_id=prog.id,
                date=res_date.isoformat(), time_block=tb,
                school_name=school, group_type=prog.age_group,
                num_students=num_students, num_teachers=RNG.randint(1, 2),
                contact_name=teacher, contact_email=email, contact_phone=phone,
                status="pending",
                gdpr_consent=True, terms_accepted=True,
            ))

        # Cancelled: 6 (mix past/future)
        cancel_reasons = [
            "Nemocnost třídy", "Organizační důvody na straně školy",
            "Přeloženo na pozdější termín", "Zrušeno školou bez udání důvodu",
            "Karanténa", "Změna programu školy",
        ]
        for i in range(6):
            offset = RNG.randint(-15, 20)
            res_date = (datetime.now(timezone.utc) + timedelta(days=offset)).date()
            prog = RNG.choice(programs)
            tb = RNG.choice(prog.time_blocks)
            school, teacher, email, phone = pick_school()
            num_students = RNG.randint(prog.min_capacity, prog.max_capacity)
            reservations.append(Reservation(
                id=uuid.uuid4(), institution_id=inst_id, program_id=prog.id,
                date=res_date.isoformat(), time_block=tb,
                school_name=school, group_type=prog.age_group,
                num_students=num_students, num_teachers=1,
                contact_name=teacher, contact_email=email, contact_phone=phone,
                status="cancelled",
                cancelled_by=admin.id,
                cancelled_at=datetime.now(timezone.utc) - timedelta(days=max(1, -offset if offset < 0 else 1)),
                cancellation_reason=cancel_reasons[i],
                gdpr_consent=True, terms_accepted=True,
            ))

        # ---- INTENTIONAL CONFLICTS (4 extra records, direct insert bypasses collision) ----
        conflict_day = (datetime.now(timezone.utc) + timedelta(days=14)).date()
        # 1) Same lecturer L2 same room same time (Moderna ZŠ vs SŠ both at 11:00-12:30)
        p_zs = next(p for p in programs if p.name_cs == "Moderna v galerii — II. stupeň ZŠ")
        p_ss = next(p for p in programs if p.name_cs == "Moderna v galerii — SŠ")
        reservations.append(Reservation(
            id=uuid.uuid4(), institution_id=inst_id, program_id=p_zs.id,
            date=conflict_day.isoformat(), time_block="11:00-12:30",
            school_name="ZŠ Masarykova Brno", group_type="zs2_12_15",
            num_students=22, num_teachers=2,
            contact_name="Mgr. Jana Nováková", contact_email="jana.novakova@zs-masarykova.cz",
            contact_phone="+420 545 214 112", status="confirmed", confirmed_by=admin.id,
            confirmed_at=datetime.now(timezone.utc),
            assigned_lecturer_id=L2, assigned_lecturer_name="MgA. Petr Kučera",
            gdpr_consent=True, terms_accepted=True,
            notes="⚠️ Kolize: stejný lektor a prostor jako SŠ rezervace.",
        ))
        reservations.append(Reservation(
            id=uuid.uuid4(), institution_id=inst_id, program_id=p_ss.id,
            date=conflict_day.isoformat(), time_block="11:00-12:30",
            school_name="Gymnázium Matyáše Lercha", group_type="ss_14_18",
            num_students=26, num_teachers=2,
            contact_name="Mgr. Martin Beneš", contact_email="martin.benes@gml.cz",
            contact_phone="+420 543 237 540", status="pending",
            assigned_lecturer_id=L2, assigned_lecturer_name="MgA. Petr Kučera",
            gdpr_consent=True, terms_accepted=True,
        ))
        # 2) Edge overlap (5-10 min): Atelier L1 at 10:00-11:00 and another program ending 10:05
        p_exp_zs = next(p for p in programs if p.name_cs == "Experimentální ateliér — II. stupeň ZŠ")
        p_bar_zs = next(p for p in programs if p.name_cs == "Barvy kolem nás — I. stupeň ZŠ")
        edge_day = (datetime.now(timezone.utc) + timedelta(days=8)).date()
        reservations.append(Reservation(
            id=uuid.uuid4(), institution_id=inst_id, program_id=p_bar_zs.id,
            date=edge_day.isoformat(), time_block="09:05-10:05",
            school_name="ZŠ Kotlářská", group_type="zs1_7_12",
            num_students=18, num_teachers=1,
            contact_name="Mgr. Eva Horáková", contact_email="eva.horakova@zs-kotlarska.cz",
            contact_phone="+420 541 211 190", status="confirmed", confirmed_by=admin.id,
            confirmed_at=datetime.now(timezone.utc),
            assigned_lecturer_id=L3, assigned_lecturer_name="Bc. Klára Nováková",
            gdpr_consent=True, terms_accepted=True,
            notes="Edge overlap: končí 10:05, další rezervace začíná 10:00.",
        ))
        reservations.append(Reservation(
            id=uuid.uuid4(), institution_id=inst_id, program_id=p_exp_zs.id,
            date=edge_day.isoformat(), time_block="10:00-11:00",
            school_name="ZŠ Sirotkova", group_type="zs2_12_15",
            num_students=15, num_teachers=1,
            contact_name="Mgr. Tereza Kolářová", contact_email="tereza.kolarova@zssirotkova.cz",
            contact_phone="+420 549 272 004", status="confirmed", confirmed_by=admin.id,
            confirmed_at=datetime.now(timezone.utc),
            assigned_lecturer_id=L1, assigned_lecturer_name="Mgr. Anna Dvořáková",
            gdpr_consent=True, terms_accepted=True,
        ))

        db.add_all(reservations)
        await db.flush()

        # ---- Feedback: 24/25 completed = 96% ----
        comments_pool = [
            "Skvělý program, děti byly nadšené!",
            "Lektor byl výborný, zaujal i méně pozorné žáky.",
            "Pěkně připravené, děkujeme!",
            "Velmi vydařené, určitě se vrátíme.",
            "Zajímavé, jen prostor byl trochu chladný.",
            "Dobré, ale mohlo by být víc interaktivní.",
            "Moc krásný program, mile překvapeni.",
            "Paní lektorka byla skvělá, děkujeme!",
            "Program splnil naše očekávání.",
            "Trochu kratší, než jsme čekali.",
            "Děti si program užily, pochvala!",
            "Kvalitní výklad, škoda malého sálu.",
            "Výborné, děti odcházely spokojené.",
            "Zábavné i vzdělávací, perfektní kombinace.",
            "Bez problémů, rádi přijedeme znovu.",
        ]
        completed = [r for r in reservations if r.status == "completed"]
        # pick 24 out of 25 randomly
        with_fb = RNG.sample(completed, min(24, len(completed)))
        feedbacks = []
        for r in with_fb:
            # Realistic ratings: 15x5★, 6x4★, 3x3★ distribution
            rating = RNG.choices([5, 4, 3, 2], weights=[0.60, 0.28, 0.10, 0.02])[0]
            recommend = rating >= 4
            feedbacks.append(Feedback(
                id=uuid.uuid4(), institution_id=inst_id, reservation_id=r.id, program_id=r.program_id,
                token=uuid.uuid4().hex,
                answers={}, overall_rating=rating, would_recommend=recommend,
                additional_comments=RNG.choice(comments_pool) if RNG.random() > 0.15 else None,
                status="submitted",
                email_sent_at=datetime.now(timezone.utc) - timedelta(days=RNG.randint(1, 20)),
                submitted_at=datetime.now(timezone.utc) - timedelta(days=RNG.randint(0, 18)),
                submitted_by_email=r.contact_email,
            ))
        db.add_all(feedbacks)

        await db.commit()

        # ---- Summary ----
        print("=" * 60)
        print("Demo dataset created")
        print("=" * 60)
        print(f"Institution        : Galerie U Zlatého kohouta ({inst_id})")
        print(f"Admin login        : {GALLERY_EMAIL} / {GALLERY_PASSWORD}")
        print(f"Lecturers          : 3 (Anna, Petr, Klára)")
        print(f"Rooms              : 3")
        print(f"Programs           : {len(programs)}")
        print(f"Reservations       : {len(reservations)}  "
              f"(completed {sum(1 for r in reservations if r.status=='completed')}, "
              f"confirmed {sum(1 for r in reservations if r.status=='confirmed')}, "
              f"pending {sum(1 for r in reservations if r.status=='pending')}, "
              f"cancelled {sum(1 for r in reservations if r.status=='cancelled')})")
        print(f"Feedbacks          : {len(feedbacks)} / {len(completed)} completed "
              f"= {round(len(feedbacks)/len(completed)*100, 1)}%")
        print(f"Lecturer avail rows: {len(recurring)} recurring + {len(blocks)} one-off blocks")
        print(f"Intentional confl. : 4 (same-lecturer same-slot x2, edge 5-min overlap x2)")


if __name__ == "__main__":
    asyncio.run(main())
