# Bude Živo - PRD (Product Requirements Document)

## Přehled projektu
Budeživo.cz je komplexní SaaS platforma pro správu vzdělávacích programů, rezervací a institucí v České republice.

## Technologický stack
- **Frontend:** React 18, TailwindCSS, Shadcn/UI, Axios
- **Backend:** FastAPI, SQLAlchemy Async, Pydantic
- **Databáze:** Supabase (PostgreSQL)
- **Emaily:** Resend API
- **Deployment:** Vercel (Frontend), Railway (Backend)
- **Scheduler:** APScheduler (integrován v backendu)

---

## Implementované funkce

### Fáze 1 - Core MVP
- [x] Registrace a přihlášení uživatelů (JWT)
- [x] Správa institucí a programů
- [x] Rezervační systém s kalendářem dostupnosti
- [x] Dynamická témata a loga institucí na booking stránkách
- [x] Dashboard s přehledem statistik
- [x] Transakční emaily (rezervace, potvrzení, reset hesla)

### Fáze 2 - Feedback System
- [x] Databáze `feedbacks` a `feedback_questions`
- [x] API pro správu otázek a zpětných vazeb
- [x] Admin UI `/admin/feedback`
- [x] Veřejný formulář `/feedback/{token}`
- [x] APScheduler pro automatické odesílání emailů

### Fáze 3 - Team Invitation System
- [x] Databáze `team_invitations`
- [x] API pro pozvánky (odesílání, ověření, přijetí)
- [x] Email šablona s personalizovaným obsahem
- [x] Frontend `/accept-invite?token=xxx`

### Fáze 4 - Legal & PRO Plan
- [x] Podmínky používání (`/terms`)
- [x] Booking form checkbox + Legal disclaimer
- [x] PRO Plan manual upgrade
- [x] Feature gating

### Fáze 5 - School Import System
- [x] Excel/CSV import škol
- [x] Vzorový soubor ke stažení
- [x] Validace a deduplikace

### Fáze 6 - Multi-Contact CRM System (21. března 2026)
- [x] **Nová tabulka `school_contacts`** - 1:N vazba na školy
- [x] **Deduplikace škol** podle kombinace Název + Město
- [x] **Více kontaktů pod jednou školou** (pedagogové, sekretariát, atd.)
- [x] **Status kontaktů:** aktivní, neplatný, čeká na ověření
- [x] **Automatická detekce překlepů v emailech** (gmail.cz -> gmail.com)
- [x] **Hlavní kontakt** (is_primary flag)
- [x] **Filtrování škol:**
  - Podle zdroje (import, rezervace, ručně přidané)
  - Podle tagu (MŠ, ZŠ, SŠ, Gymnázium, atd.)
  - Podle neplatných kontaktů
- [x] **Vyhledávání** v názvech, emailech, městech
- [x] **UI vylepšení:**
  - Rozbalovací seznam kontaktů u každé školy
  - Tlačítka pro přidání/úpravu/smazání kontaktu
  - Označení neplatných emailů červeně
  - Modal pro úpravu tagů
  - Modal pro import s multi-kontakt instrukcemi
- [x] **IČO pole odstraněno** z UI i API

---

## Architektura

```
/app
├── backend/
│   ├── main.py
│   ├── scheduler.py
│   ├── core/security.py
│   ├── database/
│   │   ├── models.py (School, SchoolContact, ...)
│   │   └── supabase.py
│   ├── routes/
│   │   ├── schools.py (Multi-contact CRM)
│   │   ├── feedback.py
│   │   ├── invitations.py
│   │   ├── plan.py
│   │   └── legal.py
│   └── templates/emails/templates.py
├── frontend/
│   └── src/
│       ├── pages/admin/
│       │   ├── SchoolsPage.js (Multi-contact UI)
│       │   ├── FeedbackAdminPage.js
│       │   └── SettingsPage.js
│       └── pages/public/
│           ├── TermsPage.js
│           └── AcceptInvitePage.js
```

---

## Key API Endpoints

### Schools Multi-Contact CRM
| Metoda | Endpoint | Popis |
|--------|----------|-------|
| GET | /api/schools | Seznam škol s kontakty (filtry: source, tag, has_invalid) |
| GET | /api/schools/{id} | Detail školy s kontakty |
| GET | /api/schools/tags | Všechny unikátní tagy |
| PUT | /api/schools/{id}/tags | Aktualizace tagů školy |
| POST | /api/schools/{id}/contacts | Přidání kontaktu |
| PUT | /api/schools/{id}/contacts/{id} | Úprava kontaktu (status, email, atd.) |
| DELETE | /api/schools/{id}/contacts/{id} | Smazání kontaktu |
| POST | /api/schools/{id}/contacts/{id}/fix-email | Automatická oprava překlepu |
| GET | /api/schools/import-template | Stažení vzorového Excel souboru |
| POST | /api/schools/import | Import škol a kontaktů |
| GET | /api/schools/export-csv | Export do CSV (PRO) |
| GET | /api/schools/campaign-contacts | Kontakty pro kampaně |
| POST | /api/schools/send-propagation | Rozeslání propagace (PRO) |

---

## DB Schema - school_contacts

```sql
CREATE TABLE school_contacts (
    id UUID PRIMARY KEY,
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    institution_id UUID REFERENCES institutions(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT,
    phone TEXT,
    status TEXT DEFAULT 'active', -- active, invalid, pending_verification
    email_validated BOOLEAN DEFAULT FALSE,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

---

## Testovací přístupy
- **Demo účet:** demo@budezivo.cz / Demo2026!
- **Role:** admin
- **Instituce:** Test Muzeum

---

## Backlog

### P0 - Kritické
- [ ] DNS nastavení domény budezivo.cz (čeká na uživatele - A záznam ve Wedos)

### P2 - Střední priorita
- [ ] i18n přepínač jazyků
- [ ] Hromadné akce pro rezervace (Confirm/Cancel multiple)
- [ ] GDPR správa dat (Export/Delete personal data)

### P3 - Backlog
- [ ] Platební integrace (Stripe)
- [ ] Mobilní aplikace
- [ ] Pokročilá analytika

---

*Poslední aktualizace: 21. března 2026*
