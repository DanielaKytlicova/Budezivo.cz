"""
Seed script for demo@budezivo.cz presentation account.
Creates realistic programs, schools, reservations, and feedback data.
"""
import asyncio
import uuid
import random
import secrets
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://postgres.dhuujqpxazadbbdlwago:myZwog-7sydhy-tubbec@aws-1-eu-west-1.pooler.supabase.com:6543/postgres"

INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"
USER_ID = "2868bc35-7d6e-4046-87fa-013ee5efdb60"

# Question IDs
Q_RATING = "dd37738f-dbd7-47c8-be15-241a09e47174"
Q_YESNO = "3ad49a66-f2da-4db6-a173-5a0a4af3d036"
Q_TEXT = "a7353917-14ee-460e-9132-b23d78f53ad6"

# Existing program IDs
PROG_HISTORICKA = "fa7c7513-813c-4c10-827c-30ff11a46caf"
PROG_MULTI = "5638d57c-b0e9-46a5-af47-ed6b61daf90c"

# ============ DATA ============

NEW_PROGRAMS = [
    {
        "name_cs": "Čteme obrazy",
        "name_en": "Reading Paintings",
        "description_cs": "Interaktivní program zaměřený na čtení a interpretaci výtvarných děl. Žáci se učí rozpoznávat symboly, příběhy a emoce ukryté v obrazech.",
        "description_en": "Interactive program focused on reading and interpreting artworks.",
        "age_group": "zs1_7_12",
        "duration": 60,
        "max_capacity": 25,
        "price": 80,
        "status": "active",
    },
    {
        "name_cs": "Dílna pro malé tvůrce",
        "name_en": "Workshop for Young Creators",
        "description_cs": "Kreativní workshop pro nejmenší. Děti si vyzkouší různé výtvarné techniky a vytvoří si vlastní dílo na odnesení.",
        "description_en": "Creative workshop for the youngest. Children try various art techniques.",
        "age_group": "ms_3_6",
        "duration": 45,
        "max_capacity": 20,
        "price": 60,
        "status": "active",
    },
    {
        "name_cs": "Architektura města",
        "name_en": "City Architecture",
        "description_cs": "Procházka po zajímavých budovách s výkladem o architektonických stylech a historii zástavby.",
        "description_en": "Walk through notable buildings with commentary on architectural styles.",
        "age_group": "ss_15_19",
        "duration": 90,
        "max_capacity": 30,
        "price": 100,
        "status": "active",
    },
    {
        "name_cs": "Přírodovědná laboratoř",
        "name_en": "Science Lab",
        "description_cs": "Praktické pokusy a experimenty pro žáky 2. stupně ZŠ. Fyzika, chemie a biologie v akci.",
        "description_en": "Hands-on experiments for upper primary students.",
        "age_group": "zs2_12_15",
        "duration": 75,
        "max_capacity": 20,
        "price": 90,
        "status": "active",
    },
]

SCHOOLS = [
    ("ZŠ Lesní", "Liberec", "Mgr. Jana Nováková", "novakova@zslesni.cz", "+420601234567"),
    ("ZŠ Husova", "Jablonec nad Nisou", "Ing. Petr Svoboda", "svoboda@zshusova.cz", "+420602345678"),
    ("MŠ Pastelka", "Liberec", "Bc. Lucie Dvořáková", "dvorakova@mspastelka.cz", "+420603456789"),
    ("MŠ Sluníčko Nové", "Turnov", "Eva Marková", "markova@msslun.cz", "+420604567890"),
    ("Gymnázium F. X. Šaldy", "Liberec", "PhDr. Martin Černý", "cerny@gfxs.cz", "+420605678901"),
    ("ZŠ Broumovská", "Liberec", "Mgr. Hana Procházková", "prochazkova@zsbroum.cz", "+420606789012"),
    ("ZŠ 5. května", "Liberec", "Mgr. Tomáš Veselý", "vesely@zs5kv.cz", "+420607890123"),
    ("Waldorfská škola", "Semily", "Ing. Klára Součková", "souckova@waldorf.cz", "+420608901234"),
    ("ZŠ Český Dub", "Český Dub", "Mgr. Pavel Kučera", "kucera@zscd.cz", "+420609012345"),
    ("SŠ Strojírenská", "Liberec", "Ing. Radek Horák", "horak@ssstrojir.cz", "+420610123456"),
    ("ZŠ Hodkovice", "Hodkovice nad Mohelkou", "Bc. Zdeňka Říhová", "rihova@zshodkovice.cz", "+420611234567"),
    ("MŠ Motýlek", "Liberec", "Alena Kratochvílová", "kratochvilova@msmotylek.cz", "+420612345678"),
]

TIME_BLOCKS = ["08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "13:00", "13:30", "14:00"]

FEEDBACK_COMMENTS_POSITIVE = [
    "Děti byly nadšené, program byl skvěle připravený.",
    "Výborný přístup lektora, děkujeme za zážitek!",
    "Velmi dobře organizované, přijdeme znovu.",
    "Líbil se nám interaktivní přístup k výuce.",
    "Perfektní program, děti se bavily a zároveň se učily.",
    "Oceňujeme profesionální přístup a vstřícnost.",
    "Program překonal naše očekávání, určitě doporučíme kolegům.",
    "Děti si odnesly skvělé zážitky, děkujeme!",
]

FEEDBACK_COMMENTS_MIXED = [
    "Program byl dobrý, jen trochu dlouhý pro mladší děti.",
    "Obsah výborný, prostory by mohly být lepší.",
    "Celkově spokojeni, jen časový harmonogram byl trochu nabitý.",
]

FEEDBACK_IMPROVEMENTS = [
    "Více praktických aktivit pro děti.",
    "Kratší teoretická část, více interakce.",
    "Možnost výběru obtížnosti dle věku.",
    "Přidejte prosím pracovní listy na odnesení.",
    "Bylo by fajn mít přestávku uprostřed programu.",
    "",
    "",
    "Vše bylo skvělé, nic bych neměnila.",
    "",
]


async def seed():
    engine = create_async_engine(
        DB_URL,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # 1. Create new programs
        program_ids = [PROG_HISTORICKA, PROG_MULTI]
        for prog in NEW_PROGRAMS:
            pid = str(uuid.uuid4())
            program_ids.append(pid)
            await db.execute(text("""
                INSERT INTO programs (id, institution_id, name_cs, name_en, description_cs, description_en,
                    age_group, duration, min_capacity, max_capacity, target_group, price, status, created_by, created_at, updated_at)
                VALUES (:id, :inst, :ncs, :nen, :dcs, :den, :ag, :dur, :minc, :cap, :tg, :price, :status, :uid,
                    :created, :updated)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": pid, "inst": INSTITUTION_ID, "ncs": prog["name_cs"],
                "nen": prog["name_en"], "dcs": prog["description_cs"],
                "den": prog["description_en"], "ag": prog["age_group"],
                "dur": prog["duration"], "minc": 10, "cap": prog["max_capacity"],
                "tg": prog["age_group"], "price": prog["price"], "status": prog["status"],
                "uid": USER_ID,
                "created": datetime.now(timezone.utc) - timedelta(days=random.randint(30, 90)),
                "updated": datetime.now(timezone.utc),
            })
        await db.commit()
        print(f"Created {len(NEW_PROGRAMS)} new programs")

        # 2. Create schools
        school_ids = []
        for name, city, contact, email, phone in SCHOOLS:
            sid = str(uuid.uuid4())
            school_ids.append(sid)
            await db.execute(text("""
                INSERT INTO schools (id, institution_id, name, city, contact_person,
                    email, phone, created_at, updated_at)
                VALUES (:id, :inst, :name, :city, :cn, :ce, :cp, :created, :updated)
                ON CONFLICT DO NOTHING
            """), {
                "id": sid, "inst": INSTITUTION_ID, "name": name, "city": city,
                "cn": contact, "ce": email, "cp": phone,
                "created": datetime.now(timezone.utc) - timedelta(days=random.randint(30, 120)),
                "updated": datetime.now(timezone.utc),
            })
        await db.commit()
        print(f"Created {len(SCHOOLS)} schools")

        # 3. Create reservations (past completed + upcoming confirmed + pending)
        reservation_ids = []
        today = datetime.now(timezone.utc).date()

        # Past completed reservations (last 3 months)
        for i in range(35):
            rid = str(uuid.uuid4())
            days_ago = random.randint(3, 90)
            res_date = (today - timedelta(days=days_ago)).isoformat()
            school_idx = random.randint(0, len(SCHOOLS) - 1)
            school = SCHOOLS[school_idx]
            prog_idx = random.randint(0, len(program_ids) - 1)
            
            num_students = random.randint(12, 30)
            num_teachers = random.choice([1, 2, 2, 3])
            
            await db.execute(text("""
                INSERT INTO reservations (id, institution_id, program_id, date, time_block,
                    school_name, group_type, num_students, num_teachers,
                    contact_name, contact_email, contact_phone,
                    status, confirmed_by, confirmed_at,
                    actual_students, actual_teachers,
                    gdpr_consent, terms_accepted, created_at, updated_at)
                VALUES (:id, :inst, :prog, :date, :time, :school, :group, :ns, :nt,
                    :cn, :ce, :cp, :status, :cb, :ca, :as_, :at_,
                    true, true, :created, :updated)
            """), {
                "id": rid, "inst": INSTITUTION_ID, "prog": program_ids[prog_idx],
                "date": res_date, "time": random.choice(TIME_BLOCKS),
                "school": school[0], "group": random.choice(["ms_3_6", "zs1_7_12", "zs2_12_15", "ss_15_19"]),
                "ns": num_students, "nt": num_teachers,
                "cn": school[2], "ce": school[3], "cp": school[4],
                "status": "completed",
                "cb": USER_ID, "ca": datetime.now(timezone.utc) - timedelta(days=days_ago + 1),
                "as_": num_students + random.randint(-3, 2),
                "at_": num_teachers,
                "created": datetime.now(timezone.utc) - timedelta(days=days_ago + 5),
                "updated": datetime.now(timezone.utc) - timedelta(days=days_ago),
            })
            reservation_ids.append((rid, program_ids[prog_idx], school_idx))

        # Upcoming confirmed (next 2 weeks)
        for i in range(8):
            rid = str(uuid.uuid4())
            days_ahead = random.randint(1, 14)
            res_date = (today + timedelta(days=days_ahead)).isoformat()
            school_idx = random.randint(0, len(SCHOOLS) - 1)
            school = SCHOOLS[school_idx]
            prog_idx = random.randint(0, len(program_ids) - 1)
            
            await db.execute(text("""
                INSERT INTO reservations (id, institution_id, program_id, date, time_block,
                    school_name, group_type, num_students, num_teachers,
                    contact_name, contact_email, contact_phone,
                    status, confirmed_by, confirmed_at,
                    gdpr_consent, terms_accepted, created_at, updated_at)
                VALUES (:id, :inst, :prog, :date, :time, :school, :group, :ns, :nt,
                    :cn, :ce, :cp, 'confirmed', :cb, :ca,
                    true, true, :created, :updated)
            """), {
                "id": rid, "inst": INSTITUTION_ID, "prog": program_ids[prog_idx],
                "date": res_date, "time": random.choice(TIME_BLOCKS),
                "school": school[0], "group": random.choice(["ms_3_6", "zs1_7_12", "zs2_12_15"]),
                "ns": random.randint(15, 28), "nt": random.choice([1, 2]),
                "cn": school[2], "ce": school[3], "cp": school[4],
                "cb": USER_ID, "ca": datetime.now(timezone.utc) - timedelta(days=random.randint(1, 7)),
                "created": datetime.now(timezone.utc) - timedelta(days=random.randint(3, 14)),
                "updated": datetime.now(timezone.utc),
            })

        # Pending reservations
        for i in range(4):
            rid = str(uuid.uuid4())
            days_ahead = random.randint(7, 21)
            res_date = (today + timedelta(days=days_ahead)).isoformat()
            school_idx = random.randint(0, len(SCHOOLS) - 1)
            school = SCHOOLS[school_idx]
            prog_idx = random.randint(0, len(program_ids) - 1)
            
            await db.execute(text("""
                INSERT INTO reservations (id, institution_id, program_id, date, time_block,
                    school_name, group_type, num_students, num_teachers,
                    contact_name, contact_email, contact_phone,
                    status, gdpr_consent, terms_accepted, created_at, updated_at)
                VALUES (:id, :inst, :prog, :date, :time, :school, :group, :ns, :nt,
                    :cn, :ce, :cp, 'pending', true, true, :created, :updated)
            """), {
                "id": rid, "inst": INSTITUTION_ID, "prog": program_ids[prog_idx],
                "date": res_date, "time": random.choice(TIME_BLOCKS),
                "school": school[0], "group": random.choice(["ms_3_6", "zs1_7_12"]),
                "ns": random.randint(12, 25), "nt": random.choice([1, 2]),
                "cn": school[2], "ce": school[3], "cp": school[4],
                "created": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 3)),
                "updated": datetime.now(timezone.utc),
            })

        await db.commit()
        print(f"Created {35 + 8 + 4} reservations (35 completed, 8 confirmed, 4 pending)")

        # 4. Create feedback for completed reservations
        feedback_count = 0
        for rid, prog_id, school_idx in reservation_ids:
            # ~75% response rate
            if random.random() > 0.75:
                continue

            token = secrets.token_urlsafe(32)
            rating = random.choices([3, 4, 4, 5, 5, 5], k=1)[0]  # skew positive
            recommend = rating >= 4 or random.random() > 0.3

            if rating >= 4:
                comment = random.choice(FEEDBACK_COMMENTS_POSITIVE)
            else:
                comment = random.choice(FEEDBACK_COMMENTS_MIXED)

            improvement = random.choice(FEEDBACK_IMPROVEMENTS)

            answers = {
                Q_RATING: rating,
                Q_YESNO: "yes" if recommend else "no",
                Q_TEXT: improvement,
            }

            submitted = datetime.now(timezone.utc) - timedelta(
                days=random.randint(2, 85),
                hours=random.randint(0, 12)
            )

            await db.execute(text("""
                INSERT INTO feedbacks (id, institution_id, reservation_id, program_id, token,
                    answers, overall_rating, would_recommend, additional_comments,
                    status, submitted_at, created_at, updated_at)
                VALUES (:id, :inst, :rid, :pid, :token, :answers, :rating, :rec, :comments,
                    'submitted', :sub, :created, :updated)
                ON CONFLICT (reservation_id) DO NOTHING
            """), {
                "id": str(uuid.uuid4()), "inst": INSTITUTION_ID,
                "rid": rid, "pid": prog_id, "token": token,
                "answers": str(answers).replace("'", '"'),
                "rating": rating, "rec": recommend,
                "comments": comment,
                "sub": submitted,
                "created": submitted - timedelta(days=1),
                "updated": submitted,
            })
            feedback_count += 1

        await db.commit()
        print(f"Created {feedback_count} feedback submissions")

        # 5. Mark onboarding as completed for demo
        await db.execute(text("""
            UPDATE institutions SET onboarding_completed = true
            WHERE id = :inst
        """), {"inst": INSTITUTION_ID})
        await db.commit()
        print("Marked onboarding as completed")

    await engine.dispose()
    print("\nDone! Demo account is fully seeded.")


asyncio.run(seed())
