# Bude Živo - PRD (Product Requirements Document)

## Přehled projektu
Budeživo.cz je komplexní SaaS platforma pro správu vzdělávacích programů, rezervací a institucí v České republice.
Provozovatel: Daniela Kytlicová, IČO 07407971, Mlýnská 538 (není plátce DPH)

## Technologický stack
- **Frontend:** React 18, TailwindCSS, Shadcn/UI, Axios
- **Backend:** FastAPI, SQLAlchemy Async, Pydantic, slowapi (rate limiting)
- **Databáze:** Supabase (PostgreSQL)
- **Emaily:** Resend API
- **Scheduler:** APScheduler (feedback emaily, GDPR auto-cleanup, auto-archivace)

---

## Implementované funkce

### Fáze 1-9 (předchozí)
- Core MVP, Feedback System, Team Invitations, Legal & PRO Plan
- School Import + Multi-Contact CRM, Booking & Team Improvements
- Kolize a paralelní běh programů, Dostupnost lektora

### Fáze 10 - Hromadné akce a GDPR (26.3.2026)
- [x] Hromadná změna stavu rezervací (bulk-status)
- [x] GDPR export + anonymizace osobních údajů
- [x] Filtry stavu, checkboxy, vyhledávání v rezervacích

### Fáze 11 - VOP + GDPR Auto-cleanup (26.3.2026)
- [x] VOP 15 článků, public stránka /obchodni-podminky, admin sekce
- [x] Registrační checkbox souhlasu s VOP
- [x] GDPR auto-cleanup scheduler (denní, 3:00 UTC)

### Fáze 12 - Security Hardening + Pre-pilot (26.3.2026)
- [x] CORS, Rate limiting, Security headers, JWT 7-day expiry
- [x] Password strength validation, Email templates
- [x] OG meta tagy, robots.txt, sitemap.xml

### Fáze 13 - One-off bloky + Program Archive (27.3.2026)
- [x] One-off časové bloky pro lektory (jednorázová dostupnost)
- [x] Backend: Archive, Unarchive, Archive-report endpoints
- [x] Auto-archivace scheduler (APScheduler)

### Fáze 14 - Archive UI + Onboarding wizard (28.3.2026)
- [x] **Archive UI**: ArchivePage.js s /admin/archive routou
- [x] **Onboarding Wizard**: 4-krokový průvodce na Dashboard

### Fáze 15 - Email Template Theming (28.3.2026)
- [x] **Theme systém**: Branded hlavička, fallback, konzistence všech šablon
- [x] **Oprava dual-logo**: V hlavičce vždy jen JEDNO logo

### Fáze 16 - Pricing, Mobile fix, Demo data, Statistics fix (28.3.2026)
- [x] Pricing tiers update (Zdarma, Start, Pro, Pro+)
- [x] Mobile navigation fix pro přihlášené uživatele
- [x] Demo account seeding s programy, rezervacemi, feedbackem
- [x] Statistics page oprava (toFixed null reference bug)

### Fáze 17 - Audit Log + Program Filtering (8.4.2026)
- [x] **Audit Log**: DB tabulka `audit_logs`, backend `GET /api/audit-log` s paginací a filtrováním
- [x] **AuditLogPage.js**: Admin stránka s tabulkou, entity type filtrem, paginací
- [x] **Audit logging**: `log_action()` helper integrován do program CRUD a archivace
- [x] **Program filtering (backend)**: `GET /api/programs/public/{id}?age=MS,ZS1&duration=short&tag=..`
- [x] **Program filtering (frontend)**: BookingPage filtrační panel (věkové skupiny pilulky + délka select)
- [x] **URL param sync**: `useSearchParams` parsování ?age=MS,ZS1 s automatickým předvyplněním filtrů
- [x] **Client-side filtering**: `useMemo` s fallback na `target_groups` a `age_group`
- [x] **Admin URL generátor s filtry**: Rozšířený modal s checkboxy věkových kategorií → ?age=MS,ZS1 v URL
- [x] **Fallback matching**: `_matches_age()` kontroluje `age_categories` → `target_groups` → `age_group`

---

## Testovací přístupy
- **Demo účet:** demo@budezivo.cz / Demo2026!
- **Test reports:** iteration_21 (archive), iteration_22 (onboarding), iteration_23 (email theming), iteration_24 (filtering + audit)

---

## Backlog

### P2 - Střední priorita
- [ ] i18n přepínač jazyků (CZ/EN)

### P3 - Backlog
- [ ] Social proof na landing page (loga, reference, čísla)

### P4 - Budoucnost
- [ ] Pokročilá analytika (heatmapa, trendy, finanční přehledy)
- [ ] Platební integrace (Stripe pro PRO / Fakturoid)
- [ ] PWA, push notifikace
- [ ] 2FA pro admin účty
- [ ] Alembic migrace (nahrazení ručních SQL)

---

## Klíčové API endpointy
- `GET /api/programs/public/{id}?age=MS,ZS1&duration=short` - filtrovaný seznam programů
- `GET /api/audit-log?page=1&entity_type=program` - audit log s paginací
- `POST /api/programs/{id}/archive` - archivace
- `POST /api/programs/{id}/unarchive` - obnovení
- `GET /api/programs/{id}/archive-report` - report
- `GET /api/onboarding/status` - stav onboardingu

---

## Architektura
```
/app/backend/routes/audit.py          - Audit log endpoints + log_action helper
/app/backend/routes/programs.py       - Programs CRUD + filtering + archive
/app/frontend/src/pages/public/BookingPage.js   - Filter UI + URL param sync
/app/frontend/src/pages/admin/ProgramsPage.js   - URL generator s age filtry
/app/frontend/src/pages/admin/AuditLogPage.js   - Audit log tabulka
```

*Poslední aktualizace: 8. dubna 2026*
