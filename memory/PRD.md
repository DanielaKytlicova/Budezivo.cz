# Bude Živo - PRD (Product Requirements Document)

## Přehled projektu
Budeživo.cz je komplexní SaaS platforma pro správu vzdělávacích programů, rezervací a institucí v České republice.

## Technologický stack
- **Frontend:** React 18, TailwindCSS, Shadcn/UI, Axios
- **Backend:** FastAPI, SQLAlchemy Async, Pydantic, slowapi, icalendar, msal, httpx
- **Databáze:** Supabase (PostgreSQL) + pg_advisory_xact_lock
- **Emaily:** Resend API (s ICS přílohou)
- **Integrace:** Microsoft Graph API (Outlook calendar sync)
- **Scheduler:** APScheduler (feedback, GDPR, auto-archivace, Outlook sync 5min)

---

## Implementované funkce

### Fáze 1-16 (předchozí)
- Core MVP, Feedback, Team, Legal, CRM, Booking, Kolize, GDPR
- VOP, Security, One-off bloky, Archive, Onboarding, Email Theming
- Pricing, Mobile fix, Demo data, Statistics fix

### Fáze 17 - Audit Log + Program Filtering (8.4.2026)
- [x] Audit Log: DB + API + admin stránka
- [x] Program filtering: BookingPage filtrační panel + URL params
- [x] Admin URL generátor s filtry

### Fáze 18A - ICS Export (8.4.2026)
- [x] ICS Feed: `/api/calendar/institution/{id}.ics`, `/program/{id}.ics`, `/reservation/{id}.ics`
- [x] Tlačítko "Přidat do Outlooku" (admin + veřejná success stránka)
- [x] ICS příloha v potvrzovacím emailu

### Fáze 18B - Kolizní systém Hardening (9.4.2026)
- [x] Kolize lektora při přiřazení (409 při konfliktu)
- [x] Místnosti: CRUD API + room_id na programech + kolizní kontrola
- [x] Advisory Lock: pg_advisory_xact_lock brání race conditions

### Fáze 18C - Microsoft Outlook Integration (9.4.2026)
- [x] **OAuth2 flow**: `GET /api/microsoft-calendar/connect` → MS login → callback → token storage
- [x] **Token management**: access_token + refresh_token s automatickým obnovením
- [x] **Calendar sync**: Stahuje 30 dní eventů z Outlook → `availability_blocks`
- [x] **Polling sync**: APScheduler job každých 5 minut pro automatickou synchronizaci
- [x] **Override logika**: `POST /blocks/{id}/override` — povolí/zablokuje rezervace v čase Outlook eventu
- [x] **Kolizní integrace**: `check_availability_blocks()` v collision_service kontroluje Outlook bloky
- [x] **Frontend UI**: Outlook karta na stránce Dostupnost — připojit/odpojit/sync/override
- [x] **Popup OAuth**: postMessage komunikace mezi popup oknem a rodičovským oknem

### DB Schema (nové tabulky)
```
user_calendar_integrations: id, user_id, institution_id, provider, access_token, 
    refresh_token, expires_at, microsoft_user_id, is_active, last_sync_at, sync_error
availability_blocks: id, user_id, institution_id, start_time, end_time, source, 
    external_event_id, title, override
rooms: id, institution_id, name, capacity, equipment, is_active
programs: + room_id (FK → rooms.id)
```

---

## Testovací přístupy
- **Demo účet:** demo@budezivo.cz / Demo2026!
- **Test reports:** iteration_21-27

---

## Klíčové API endpointy (nové)
- `GET /api/microsoft-calendar/connect` — zahájí OAuth flow
- `GET /api/microsoft-calendar/callback` — OAuth callback
- `GET /api/microsoft-calendar/status` — stav připojení
- `POST /api/microsoft-calendar/disconnect` — odpojení
- `POST /api/microsoft-calendar/sync` — manuální sync
- `GET /api/microsoft-calendar/blocks` — seznam bloků
- `POST /api/microsoft-calendar/blocks/{id}/override` — toggle override
- `GET/POST /api/rooms` + `PATCH/DELETE /api/rooms/{id}` — CRUD místností

---

## Backlog

### P2 - Střední priorita
- [ ] i18n přepínač jazyků (CZ/EN)

### P3 - Backlog
- [ ] Social proof na landing page
- [ ] Microsoft webhook subscription (real-time místo polling)

### P4 - Budoucnost
- [ ] Pokročilá analytika, Stripe/Fakturoid, PWA, 2FA, Alembic

---

## Důležitá poznámka k OAuth
Pro testování na preview prostředí je potřeba v Azure Portal přidat Redirect URI:
`https://booking-crm-3.preview.emergentagent.com/api/auth/microsoft/callback`

Aktuálně je nastaveno pouze: `https://budezivo.cz/api/auth/microsoft/callback`

### Fáze 19 - Aktualizace VOP (10.4.2026)
- [x] Bod 4 rozšířen: podrobný popis role platformy (4.1–4.4)
- [x] Nový bod 16: Ochrana systému a duševního vlastnictví (16.1–16.5)

*Poslední aktualizace: 10. dubna 2026*
