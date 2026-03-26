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
- [x] **Filtrování škol** (zdroj, tag, neplatné kontakty)
- [x] **Vyhledávání** v názvech, emailech, městech
- [x] **IČO pole odstraněno** z UI i API

### Fáze 7 - Booking & Team Improvements (23. března 2026)
- [x] **Limity rezervací:** min 7, max 180 dní
- [x] **Automatické vytvoření kontaktu** při nové rezervaci
- [x] **Název programu** v přehledu rezervací a dashboardu
- [x] **Dropdown přiřazení lektora** v detailu rezervace
- [x] **Logo instituce** v potvrzovacích emailech + zkrácení patičky
- [x] **Editace jmen členů týmu** - `PATCH /api/team/{member_id}/name`
- [x] **Zobrazení jmen v dropdown lektora** místo emailů
- [x] **Fix: TeamMember schema** — chybělo `name` pole v Pydantic modelu
- [x] **Mobilní navigace** — přidána záložka Nastavení pro adminy do spodní lišty

### Fáze 8 - Kolize a paralelní běh (25. března 2026)
- [x] **Nové sloupce v tabulce `programs`:** `allow_parallel` (BOOLEAN), `collision_resources` (JSONB), `blocked_program_ids` (JSONB)
- [x] **Backend: Collision service** — parsování time bloků, detekce překryvů, kontrola zdrojů
- [x] **Backend: Validace při rezervaci** — 409 při kolizi
- [x] **Backend: Availability endpoint** — zohledňuje cross-program kolize
- [x] **Frontend: Záložka "Kolize"** v editaci programu

### Fáze 9 - Dostupnost lektora (25. března 2026)
- [x] **Nové DB tabulky:** `lecturer_availability` a `lecturer_time_off`
- [x] **Backend API:** CRUD pro pravidelnou dostupnost a blokace
- [x] **Frontend stránka:** `/admin/availability` s týdenním kalendářem
- [x] **Integrace do BookingPage** — "Lektor nedostupný" pro blokované časy

### Fáze 10 - Hromadné akce a GDPR (26. března 2026)
- [x] **Backend: `POST /api/bookings/bulk-status`** — hromadná změna stavu (potvrdit/zrušit/dokončit)
- [x] **Backend: `GET /api/gdpr/export`** — export osobních dat (GDPR čl. 20)
- [x] **Backend: `POST /api/gdpr/anonymize`** — anonymizace osobních údajů (GDPR čl. 17)
- [x] **Frontend: Checkboxy** u každé rezervace, "Vybrat vše"
- [x] **Frontend: Hromadný panel** (Potvrdit/Zrušit/Dokončit vybrané)
- [x] **Frontend: Filtry stavu** (Vše, Čekající, Potvrzené, Zrušené, Dokončené) s počty
- [x] **Frontend: Vyhledávání** v rezervacích (škola, kontakt, program)
- [x] **Frontend: GDPR sekce** v Nastavení — export dat (JSON stažení), anonymizace s potvrzovacím dialogem
- [x] **Právní článek 10** — odpovědnost za realizaci rezervací (platforma = prostředník, již existoval)

---

## Architektura

```
/app
├── backend/
│   ├── main.py
│   ├── scheduler.py
│   ├── core/security.py
│   ├── database/
│   │   ├── models.py
│   │   ├── supabase.py
│   │   └── supabase_repositories.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── bookings.py (+ bulk-status)
│   │   ├── gdpr.py (NEW)
│   │   ├── availability.py
│   │   ├── lecturer_availability.py
│   │   └── ...
│   ├── services/
│   │   ├── collision_service.py
│   │   └── email_service.py
│   ├── models/schemas.py
│   └── constants/legal_texts.py
├── frontend/
│   └── src/
│       ├── components/layout/AdminLayout.js
│       ├── pages/admin/
│       │   ├── BookingsPage.js (bulk actions, filters, search)
│       │   ├── SettingsPage.js (GDPR section)
│       │   └── ...
│       └── pages/public/
│           ├── GDPRPage.js
│           ├── TermsPage.js
│           └── ...
```

---

## Key API Endpoints

### Bulk Actions
| Metoda | Endpoint | Popis |
|--------|----------|-------|
| POST | /api/bookings/bulk-status | Hromadná změna stavu (confirmed/cancelled/completed) |

### GDPR
| Metoda | Endpoint | Popis |
|--------|----------|-------|
| GET | /api/gdpr/export | Export osobních dat (JSON) |
| POST | /api/gdpr/anonymize | Anonymizace osobních údajů (potvrzení: SMAZAT) |

### Team Management
| Metoda | Endpoint | Popis |
|--------|----------|-------|
| GET | /api/team | Seznam členů týmu |
| PATCH | /api/team/{id}/name | Aktualizace jména člena |

---

## Testovací přístupy
- **Demo účet:** demo@budezivo.cz / Demo2026!
- **Role:** admin
- **Instituce:** Test Muzeum

---

## Backlog

### P1 - Vysoká priorita
- [ ] Production deployment — uživatel musí pushnout na GitHub a spustit migrace

### P2 - Střední priorita
- [ ] Analýza zabezpečení webu (kyber bezpečnost, úniky dat)
- [ ] i18n přepínač jazyků (existující tlačítko, potřebuje napojení)

### P3 - Backlog
- [ ] Platební integrace (Fakturoid — zálohové faktury, aktivace PRO po připsání platby)

### P4 - Mobilní aplikace & Pokročilá analytika
- [ ] PWA, push notifikace, offline režim, QR check-in
- [ ] Heatmapa vytíženosti, trendy, finanční přehledy, exporty reportů

---

*Poslední aktualizace: 26. března 2026*
