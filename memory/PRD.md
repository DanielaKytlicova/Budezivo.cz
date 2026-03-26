# Bude Živo - PRD (Product Requirements Document)

## Přehled projektu
Budeživo.cz je komplexní SaaS platforma pro správu vzdělávacích programů, rezervací a institucí v České republice.

## Technologický stack
- **Frontend:** React 18, TailwindCSS, Shadcn/UI, Axios
- **Backend:** FastAPI, SQLAlchemy Async, Pydantic
- **Databáze:** Supabase (PostgreSQL)
- **Emaily:** Resend API
- **Scheduler:** APScheduler (feedback emaily, GDPR auto-cleanup)

---

## Implementované funkce

### Fáze 1-9 (předchozí)
- Core MVP (registrace, přihlášení, programy, rezervace, dashboard, emaily)
- Feedback System s APScheduler
- Team Invitation System
- Legal & PRO Plan
- School Import + Multi-Contact CRM
- Booking & Team Improvements (limity, lektor dropdown, editace jmen)
- Kolize a paralelní běh programů
- Dostupnost lektora (kalendář + integrace do bookingu)

### Fáze 10 - Hromadné akce a GDPR (26. března 2026)
- [x] `POST /api/bookings/bulk-status` — hromadná změna stavu
- [x] `GET /api/gdpr/export` — export osobních dat (GDPR čl. 20)
- [x] `POST /api/gdpr/anonymize` — anonymizace (GDPR čl. 17)
- [x] Frontend: checkboxy, bulk panel, filtry stavu, vyhledávání
- [x] GDPR sekce v Nastavení (export, anonymizace, data retention)

### Fáze 11 - VOP + GDPR Auto-cleanup (26. března 2026)
- [x] **VOP (Všeobecné obchodní podmínky)** — 15 článků dle českého práva
- [x] **Public stránka `/obchodni-podminky`** — plný text VOP
- [x] **API `GET /api/legal/vop`** — strukturovaná VOP data
- [x] **Registrační checkbox** — "Souhlasím s obchodními podmínkami" + link na VOP
- [x] **Backend validace** — `terms_accepted` field v UserCreate + DB sloupec
- [x] **Admin Nastavení > VOP** — sekce pro opětovné přečtení podmínek
- [x] **GDPR auto-cleanup scheduler** — denní job (3:00 UTC), anonymizace starých rezervací dle data_retention nastavení instituce
- [x] **Automatická anonymizace** — toggle v GDPR nastavení s popisem

---

## Architektura

```
/app
├── backend/
│   ├── main.py
│   ├── scheduler.py (feedback + GDPR auto-cleanup)
│   ├── core/security.py
│   ├── database/
│   │   ├── models.py
│   │   ├── supabase.py
│   │   └── supabase_repositories.py
│   ├── routes/
│   │   ├── auth.py (register s terms_accepted)
│   │   ├── bookings.py (+ bulk-status)
│   │   ├── gdpr.py (export + anonymize)
│   │   ├── legal.py (terms + VOP)
│   │   ├── availability.py
│   │   ├── lecturer_availability.py
│   │   └── settings.py
│   ├── services/
│   │   ├── collision_service.py
│   │   └── email_service.py
│   ├── models/schemas.py
│   └── constants/legal_texts.py (VOP_SECTIONS)
├── frontend/
│   └── src/
│       ├── App.js (+ /obchodni-podminky route)
│       ├── pages/admin/
│       │   ├── BookingsPage.js (bulk actions)
│       │   ├── SettingsPage.js (GDPR + VOP sekce)
│       │   └── ...
│       └── pages/public/
│           ├── VopPage.js (NEW)
│           ├── RegisterPage.js (terms checkbox)
│           └── ...
```

---

## Testovací přístupy
- **Demo účet:** demo@budezivo.cz / Demo2026!
- **Test reports:** /app/test_reports/iteration_18.json (bulk+GDPR), iteration_19.json (VOP+scheduler)

---

## Backlog

### P1 - Vysoká priorita
- [ ] Production deployment — uživatel musí pushnout na GitHub

### P2 - Střední priorita
- [ ] Analýza zabezpečení webu (kyber bezpečnost, úniky dat)
- [ ] i18n přepínač jazyků

### P3 - Backlog
- [ ] Platební integrace Fakturoid (zálohové faktury, aktivace PRO po připsání platby)

### P4 - Budoucnost
- [ ] PWA, push notifikace, offline režim, QR check-in
- [ ] Heatmapa, trendy, finanční přehledy, exporty reportů

---

*Poslední aktualizace: 26. března 2026*
