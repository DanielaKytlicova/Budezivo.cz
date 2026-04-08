# Bude Živo - PRD (Product Requirements Document)

## Přehled projektu
Budeživo.cz je komplexní SaaS platforma pro správu vzdělávacích programů, rezervací a institucí v České republice.
Provozovatel: Daniela Kytlicová, IČO 07407971, Mlýnská 538 (není plátce DPH)

## Technologický stack
- **Frontend:** React 18, TailwindCSS, Shadcn/UI, Axios
- **Backend:** FastAPI, SQLAlchemy Async, Pydantic, slowapi, icalendar
- **Databáze:** Supabase (PostgreSQL)
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
- [x] Audit Log: DB + API + admin stránka s filtrováním
- [x] Program filtering: BookingPage filtrační panel + URL params
- [x] Admin URL generátor s filtry věkových kategorií
- [x] Backend fallback matching (_matches_age)

### Fáze 18 - Outlook Calendar Integration (Fáze A) (8.4.2026)
- [x] **ICS Feed Endpoints**: 3 endpointy pro export rezervací
  - `GET /api/calendar/institution/{id}.ics` — všechny rezervace instituce
  - `GET /api/calendar/program/{id}.ics` — rezervace konkrétního programu
  - `GET /api/calendar/reservation/{id}.ics` — jednotlivá rezervace
- [x] **Timezone**: Europe/Prague (TZID), správný VEVENT formát
- [x] **Status filter**: `?status=confirmed` query parameter
- [x] **Content-Type**: `text/calendar; charset=utf-8` + Content-Disposition attachment
- [x] **Admin BookingsPage**: Tlačítko "Outlook kalendář" v hlavičce (stáhne instituční ICS feed)
- [x] **Booking detail modal**: Tlačítko "Přidat do Outlooku (.ics)" pro jednotlivou rezervaci
- [x] **Veřejná success stránka**: Tlačítko "Přidat do Outlooku" po odeslání rezervace
- [x] **ICS příloha v emailu**: `_generate_ics_attachment()` v `send_booking_confirmation`
- [x] **ICS formát**: UID@budezivo.cz, SUMMARY, DTSTART/DTEND, DESCRIPTION (škola, počty, kontakt), LOCATION, STATUS

---

## Testovací přístupy
- **Demo účet:** demo@budezivo.cz / Demo2026!
- **Test reports:** iteration_21-25

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
- `GET /api/calendar/institution/{id}.ics?status=confirmed` — ICS feed
- `GET /api/calendar/program/{id}.ics` — ICS per program
- `GET /api/calendar/reservation/{id}.ics` — Single ICS download
- `GET /api/programs/public/{id}?age=MS,ZS1` — Filtrované programy
- `GET /api/audit-log` — Audit log

## Architektura
```
/app/backend/routes/calendar_export.py  - ICS feed endpoints (NEW)
/app/backend/services/email_service.py  - ICS attachment in emails (UPDATED)
/app/backend/main.py                    - calendar_export_router registered
```

*Poslední aktualizace: 8. dubna 2026*
