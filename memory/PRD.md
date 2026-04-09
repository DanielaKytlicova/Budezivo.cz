# Bude Živo - PRD (Product Requirements Document)

## Přehled projektu
Budeživo.cz je komplexní SaaS platforma pro správu vzdělávacích programů, rezervací a institucí v České republice.
Provozovatel: Daniela Kytlicová, IČO 07407971, Mlýnská 538 (není plátce DPH)

## Technologický stack
- **Frontend:** React 18, TailwindCSS, Shadcn/UI, Axios
- **Backend:** FastAPI, SQLAlchemy Async, Pydantic, slowapi, icalendar
- **Databáze:** Supabase (PostgreSQL) + pg_advisory_xact_lock
- **Emaily:** Resend API (s ICS přílohou)
- **Scheduler:** APScheduler (feedback, GDPR, auto-archivace)

---

## Implementované funkce

### Fáze 1-16 (předchozí)
- Core MVP, Feedback, Team Invitations, Legal & PRO Plan
- School Import + CRM, Booking & Team Improvements
- Kolize, Dostupnost lektora, Hromadné akce, GDPR
- VOP, Security Hardening, One-off bloky, Archive UI
- Onboarding Wizard, Email Theming, Pricing, Mobile fix
- Demo data seeding, Statistics fix

### Fáze 17 - Audit Log + Program Filtering (8.4.2026)
- [x] Audit Log: DB + API + admin stránka
- [x] Program filtering: BookingPage filtrační panel + URL params
- [x] Admin URL generátor s filtry

### Fáze 18A - Outlook ICS Export (8.4.2026)
- [x] ICS Feed: `/api/calendar/institution/{id}.ics`, `/program/{id}.ics`, `/reservation/{id}.ics`
- [x] Tlačítko "Přidat do Outlooku" v admin + veřejné success stránce
- [x] ICS příloha v potvrzovacím emailu

### Fáze 18B - Kolizní systém Hardening (9.4.2026)
- [x] **R1 — Kolize lektora při přiřazení**: `assign_lecturer` a `admin_assign_lecturer` nyní kontrolují časový překryv → 409 při konfliktu
- [x] **R2 — Oprava `check_booking_collision`**: Využívá `assigned_lecturer_id` z programu jako fallback
- [x] **R3 — Aktivace `check_lecturer_available_for_block`**: Kontrola recurring availability + time-off bloků
- [x] **R4 — Místnosti (rooms)**:
  - DB tabulka `rooms` (id, institution_id, name, capacity, equipment, is_active)
  - `room_id` FK na `programs`
  - CRUD API: `GET/POST /api/rooms`, `PATCH/DELETE /api/rooms/{id}`
  - Kolizní kontrola: Pokud `"room" in collision_resources` a dva programy sdílí `room_id`, překryv blokován
  - Frontend: Room management inline v záložce Kolize (dropdown + create/delete)
- [x] **R5 — Advisory Lock**: `pg_advisory_xact_lock(hash(institution_id, date))` v `check_booking_collision` brání race conditions

---

## Testovací přístupy
- **Demo účet:** demo@budezivo.cz / Demo2026!
- **Test reports:** iteration_21-26

---

## Backlog

### P0 - Outlook Integration Fáze B (čeká na Azure credentials)
- [ ] Microsoft OAuth připojení (Azure AD App Registration)
- [ ] DB tabulky: `user_calendar_integrations`, `availability_blocks`
- [ ] Synchronizace kalendáře (webhooks + polling fallback)
- [ ] Override logika (povolení/blokace Outlook bloků)
- [ ] UX: Zobrazení Outlook bloků v kalendáři dostupnosti

### P2 - Střední priorita
- [ ] i18n přepínač jazyků (CZ/EN)

### P3 - Backlog
- [ ] Social proof na landing page (loga, reference, čísla)

### P4 - Budoucnost
- [ ] Pokročilá analytika (heatmapa, trendy, finanční přehledy)
- [ ] Platební integrace (Stripe / Fakturoid)
- [ ] PWA, push notifikace
- [ ] 2FA, Alembic migrace

---

## Klíčové API endpointy
- `GET/POST /api/rooms` — CRUD místností
- `PATCH/DELETE /api/rooms/{id}`
- `POST /api/bookings/{id}/assign-lecturer-admin` — nyní s 409 kolizní kontrolou
- `GET /api/calendar/institution/{id}.ics` — ICS feed
- `GET /api/programs/public/{id}?age=MS,ZS1` — Filtrované programy

## DB Schema (nové)
```
rooms: id, institution_id, name, capacity, equipment, is_active
programs: + room_id (FK → rooms.id)
reservations: + composite index (institution_id, date, status)
```

*Poslední aktualizace: 9. dubna 2026*
