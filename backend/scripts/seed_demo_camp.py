"""
Seed demo summer camp for Test Muzeum.

Idempotent — if the camp already exists by name + institution, it is updated in place.
Run via: python -m scripts.seed_demo_camp (from /app/backend) or python /app/backend/scripts/seed_demo_camp.py
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, '/app/backend')

from sqlalchemy import select, and_
from database.supabase import AsyncSessionLocal
from database.models import Event, EventDate, FeatureFlag, Institution, InstitutionPaymentSettings


# ── Configuration ──────────────────────────────────────────────────────────
TEST_MUZEUM_ID = uuid.UUID("669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5")
DEMO_CAMP_NAME = "Příměstský tábor – Léto 2026"

CAMP_DESCRIPTION = """Pětidenní kreativní příměstský tábor pro děti od 7 do 12 let v prostorách našeho muzea.

Co děti čeká:
• tvořivé výtvarné dílny (keramika, malba, koláž)
• komentované prohlídky výstav přizpůsobené dětem
• detektivní hra v depozitáři
• exkurze do restaurátorské dílny
• závěrečná vernisáž s rodiči

Cena zahrnuje: stravování (svačina + oběd + svačina), pitný režim, výtvarný materiál, vstupné, pojištění a tričko s logem tábora.

Termín: pondělí–pátek 1.–5. července 2026, 8:00–16:30
Místo konání: Test Muzeum, hlavní budova
"""

DEMO_CAMP_FORM_FIELDS = [
    {"id": "child_name",   "type": "text",     "label": "Jméno a příjmení dítěte",       "required": True,  "order": 1},
    {"id": "child_age",    "type": "number",   "label": "Věk dítěte (7–12 let)",          "required": True,  "order": 2},
    {"id": "child_school", "type": "text",     "label": "Škola, kterou dítě navštěvuje", "required": False, "order": 3},
    {"id": "parent_name",  "type": "text",     "label": "Jméno zákonného zástupce",       "required": True,  "order": 4},
    {"id": "parent_email", "type": "email",    "label": "E-mail zákonného zástupce",      "required": True,  "order": 5},
    {"id": "parent_phone", "type": "text",     "label": "Telefon zákonného zástupce",     "required": True,  "order": 6},
    {"id": "allergies",    "type": "textarea", "label": "Alergie, omezení stravy nebo zdravotní omezení", "required": False, "order": 7},
    {"id": "consent_photo","type": "checkbox", "label": "Souhlasím s pořizováním fotografií dítěte z aktivit tábora pro účely propagace.", "required": False, "order": 8},
]


async def ensure_feature_flag(session, flag_key: str, institution_id: uuid.UUID):
    res = await session.execute(select(FeatureFlag).where(FeatureFlag.key == flag_key))
    flag = res.scalar_one_or_none()
    if not flag:
        flag = FeatureFlag(
            key=flag_key,
            enabled=False,
            allowed_institution_ids=[str(institution_id)],
            description=f"Pilot {flag_key} module",
        )
        session.add(flag)
        await session.commit()
        print(f"  ✓ Created feature flag {flag_key}")
        return
    ids = list(flag.allowed_institution_ids or [])
    if str(institution_id) not in ids:
        ids.append(str(institution_id))
        flag.allowed_institution_ids = ids
        await session.commit()
        print(f"  ✓ Whitelisted {institution_id} in feature flag {flag_key}")
    else:
        print(f"  · Feature flag {flag_key} already covers {institution_id}")


async def ensure_payment_settings(session, institution_id: uuid.UUID):
    res = await session.execute(
        select(InstitutionPaymentSettings).where(InstitutionPaymentSettings.institution_id == institution_id)
    )
    ps = res.scalar_one_or_none()
    if ps is None:
        ps = InstitutionPaymentSettings(
            institution_id=institution_id,
            payment_mode="both",        # qr + gateway → user vidí obě varianty
            provider="comgate",
            account_number="295033917",
            bank_code="0300",
            account_name="Test Muzeum",
            iban="CZ6003000000000295033917",
            gateway_api_key="",          # MOCK mode → frontend zobrazí mock simulator
            gateway_secret="",
        )
        session.add(ps)
        await session.commit()
        print("  ✓ Created payment settings (Comgate MOCK + QR)")
    else:
        print("  · Payment settings already exist (skipping)")


async def upsert_demo_camp(session, institution_id: uuid.UUID):
    res = await session.execute(
        select(Event).where(and_(
            Event.institution_id == institution_id,
            Event.name == DEMO_CAMP_NAME,
        ))
    )
    event = res.scalar_one_or_none()
    if event is None:
        event = Event(
            institution_id=institution_id,
            name=DEMO_CAMP_NAME,
            type="camp",
            description=CAMP_DESCRIPTION,
            capacity=20,
            price=2500.0,
            currency="CZK",
            is_active=True,
            is_archived=False,
            form_fields=DEMO_CAMP_FORM_FIELDS,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        print(f"  ✓ Created event '{event.name}' ({event.id})")
    else:
        # Update content but keep the ID stable.
        event.description = CAMP_DESCRIPTION
        event.capacity = 20
        event.price = 2500.0
        event.currency = "CZK"
        event.is_active = True
        event.is_archived = False
        event.form_fields = DEMO_CAMP_FORM_FIELDS
        event.updated_at = datetime.now(timezone.utc)
        await session.commit()
        print(f"  · Updated existing event '{event.name}' ({event.id})")

    # Ensure a single date for July 1–5, 2026
    res2 = await session.execute(select(EventDate).where(EventDate.event_id == event.id))
    existing_dates = res2.scalars().all()
    if not existing_dates:
        ed = EventDate(
            event_id=event.id,
            start_datetime=datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc),
            end_datetime=datetime(2026, 7, 5, 16, 30, tzinfo=timezone.utc),
            capacity_override=None,
        )
        session.add(ed)
        await session.commit()
        print("  ✓ Added date 2026-07-01 → 2026-07-05")
    else:
        print(f"  · Event already has {len(existing_dates)} date(s) (skipping)")

    return event


async def main():
    print("┌─ Seed: Demo Summer Camp ──────────────────────────────")
    async with AsyncSessionLocal() as session:
        # Check institution exists
        inst = (await session.execute(
            select(Institution).where(Institution.id == TEST_MUZEUM_ID)
        )).scalar_one_or_none()
        if not inst:
            print(f"  ✗ Institution {TEST_MUZEUM_ID} not found, aborting")
            return
        print(f"  · Target institution: {inst.name} ({TEST_MUZEUM_ID})")

        await ensure_feature_flag(session, "events_module", TEST_MUZEUM_ID)
        await ensure_payment_settings(session, TEST_MUZEUM_ID)
        event = await upsert_demo_camp(session, TEST_MUZEUM_ID)

        print("└─ Done ────────────────────────────────────────────────")
        print(f"\nPublic URL:  /events/{TEST_MUZEUM_ID}")
        print(f"Admin URL:   /admin/events  (login as admin of {inst.name})")
        print(f"Event ID:    {event.id}")


if __name__ == "__main__":
    asyncio.run(main())
