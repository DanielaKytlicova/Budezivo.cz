# Bude Živo - PRD (Product Requirements Document)

## Přehled projektu
Budeživo.cz je komplexní SaaS platforma pro správu vzdělávacích programů, rezervací a institucí v České republice.
Provozovatel: Daniela Kytlicová, IČO 07407971, Mlýnská 538 (není plátce DPH)

## Technologický stack
- **Frontend:** React 18, TailwindCSS, Shadcn/UI, Axios
- **Backend:** FastAPI, SQLAlchemy Async, Pydantic, slowapi (rate limiting)
- **Databáze:** Supabase (PostgreSQL)
- **Emaily:** Resend API
- **Scheduler:** APScheduler (feedback emaily, GDPR auto-cleanup)

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
- [x] **CORS** omezeny na budezivo.cz domény (+ preview v dev)
- [x] **JWT expirace** snížena na 7 dní (z 30)
- [x] **JWT_SECRET** fail-fast (žádný fallback)
- [x] **Rate limiting**: 5/min registrace, 10/min login, 3/min reset hesla
- [x] **Validace hesla** na backendu: min 8 znaků, velké+malé+číslo
- [x] **Security headers**: X-Frame-Options=DENY, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy
- [x] **Reset hesla** dynamická URL z FRONTEND_URL env
- [x] **OG meta tagy** pro sociální sdílení + lang="cs"
- [x] **robots.txt** + **sitemap.xml**
- [x] **Indikátor síly hesla** v registraci (4 kritéria, barevné pruhy)
- [x] **VOP placeholder** vyplněn: Daniela Kytlicová, IČO 07407971, Mlýnská 538
- [x] **GDPR placeholder** vyplněn: datová schránka e2u63pp
- [x] **Email šablona** reservation_rescheduled (přesunutí termínu)

---

## Testovací přístupy
- **Demo účet:** demo@budezivo.cz / Demo2026!
- **Test reports:** iteration_18 (bulk), 19 (VOP), 20 (security)

---

## Backlog

### P2 - Střední priorita
- [ ] Analýza zabezpečení webu (penetrační testy, audit)
- [ ] i18n přepínač jazyků
- [ ] Smazat testovací data z DB (TEST_CSV_Škola atd.)

### P3 - Backlog
- [ ] Platební integrace Fakturoid (zálohové faktury → aktivace PRO)
- [ ] Onboarding wizard po registraci

### P4 - Budoucnost
- [ ] PWA, push notifikace, QR check-in
- [ ] Audit log (kdo, co, kdy změnil)
- [ ] Heatmapa, trendy, finanční přehledy
- [ ] 2FA pro admin účty
- [ ] Alembic migrace
- [ ] Social proof na landing page

---

*Poslední aktualizace: 26. března 2026*
