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
- [x] **Archive link**: Tlačítko "Archiv" v ProgramsPage
- [x] **Archivace z ProgramsPage**: Dedikovaný POST /archive endpoint
- [x] **Unarchive**: Obnovení programu z archivu
- [x] **Archive Report**: Dialog se statistikami + JSON export
- [x] **Oprava route ordering**: GET /archived před GET /{program_id}
- [x] **Oprava datetime**: archived_at jako datetime objekt (ne string)
- [x] **Onboarding Wizard**: 4-krokový průvodce na Dashboard
  - Welcome, Create Program, Set Availability, Done
  - Rozpoznání existujících programů (zelený banner)
  - Skip/dismiss funkce
  - Backend: GET/POST /api/onboarding (status + complete)
  - DB: institutions.onboarding_completed boolean

---

## Testovací přístupy
- **Demo účet:** demo@budezivo.cz / Demo2026!
- **Test reports:** iteration_21 (archive), iteration_22 (onboarding)

---

## Backlog

### P2 - Střední priorita
- [ ] i18n přepínač jazyků (CZ/EN)
- [ ] Smazat testovací data z DB

### P3 - Backlog
- [ ] Audit log (kdo, co, kdy změnil)
- [ ] Social proof na landing page (loga, reference, čísla)

### P4 - Budoucnost
- [ ] Pokročilá analytika (heatmapa, trendy, finanční přehledy)
- [ ] Platební integrace (Stripe pro PRO / Fakturoid)
- [ ] PWA, push notifikace
- [ ] 2FA pro admin účty
- [ ] Alembic migrace (nahrazení ručních SQL)

---

## Klíčové API endpointy
- `POST /api/programs/{id}/archive` - archivace
- `POST /api/programs/{id}/unarchive` - obnovení
- `GET /api/programs/{id}/archive-report` - report
- `GET /api/programs/archived` - seznam archivovaných
- `GET /api/onboarding/status` - stav onboardingu
- `POST /api/onboarding/complete` - dokončení onboardingu

---

## Architektura
```
/app/backend/routes/onboarding.py    - Onboarding endpoints
/app/backend/routes/programs.py      - Archive endpoints
/app/frontend/src/pages/admin/ArchivePage.js
/app/frontend/src/components/admin/OnboardingWizard.js
/app/frontend/src/pages/admin/DashboardPage.js  - Onboarding integration
```

*Poslední aktualizace: 28. března 2026*
