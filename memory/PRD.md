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
- [x] **Backend: Collision service** (`/app/backend/services/collision_service.py`) — parsování time bloků (HH:MM i HH:MM-HH:MM), detekce překryvů, kontrola zdrojů (lektor/místnost) a ručně blokovaných programů
- [x] **Backend: Validace při rezervaci** — `POST /api/bookings/public/{id}` i admin `POST /api/bookings` vrací 409 při kolizi
- [x] **Backend: Availability endpoint** — zohledňuje cross-program kolize při zobrazení dostupných slotů
- [x] **Frontend: Záložka "Kolize"** v editaci programu s toggle, checkboxy zdrojů (Lektor/Místnost), multi-select blokovaných programů, tooltipy a summary kartou
- [x] **Edge cases:** plně paralelní program (bez omezení), oboustranná kontrola blokovaných programů

### Fáze 9 - Dostupnost lektora (25. března 2026)
- [x] **Nové DB tabulky:** `lecturer_availability` (pravidelná dostupnost) a `lecturer_time_off` (blokace/výjimky)
- [x] **Backend API:** Kompletní CRUD pro pravidelnou dostupnost a blokace, week-view endpoint, availability check endpoint
- [x] **Frontend stránka:** `/admin/availability` s týdenním kalendářem (Po-Ne, 7-18h)
- [x] **Kalendářové barvy:** zelená (dostupný), červená (blokace), šedá (nedostupný)
- [x] **Formuláře:** Přidání pravidelného času (multi-day), přidání blokace (datum, čas, důvod), editace, mazání
- [x] **Admin selector:** Dropdown pro výběr lektora (admin/správce vidí celý tým)
- [x] **Navigace:** Záložka "Dostupnost" v sidebaru pro role edukator, lektor, admin, spravce
- [x] **Logika validace:** Check endpoint pro ověření dostupnosti lektora při vytváření rezervací
- [x] **Edge cases:** Lektor bez nastavení = nedostupný, celodenní blokace, blokace mimo dostupnost

---

## Architektura

```
/app
├── backend/
│   ├── main.py
│   ├── scheduler.py
│   ├── core/security.py
│   ├── database/
│   │   ├── models.py (User, School, SchoolContact, ...)
│   │   ├── supabase.py
│   │   └── supabase_repositories.py
│   ├── routes/
│   │   ├── schools.py (Multi-contact CRM)
│   │   ├── bookings.py (Booking + lecturer assignment + collision check)
│   │   ├── availability.py (Availability + collision awareness)
│   │   ├── team.py (Team member mgmt + name editing)
│   │   ├── invitations.py (Team invitations)
│   │   ├── feedback.py
│   │   ├── plan.py
│   │   └── legal.py
│   ├── services/
│   │   └── collision_service.py (Collision detection & time block parsing)
│   ├── models/schemas.py (Pydantic schemas)
│   └── templates/emails/templates.py
├── frontend/
│   └── src/
│       ├── components/layout/AdminLayout.js (desktop sidebar + mobile bottom nav)
│       ├── pages/admin/
│       │   ├── BookingsPage.js (Lecturer dropdown with names)
│       │   ├── TeamPage.js (Name editing dialog)
│       │   ├── SchoolsPage.js (Multi-contact CRM UI)
│       │   ├── DashboardPage.js
│       │   ├── LecturerAvailabilityPage.js (Weekly calendar, CRUD)
│       │   ├── ProgramsPage.js (Collision tab)
│       │   └── SettingsPage.js
│       └── pages/public/
│           ├── TermsPage.js
│           └── AcceptInvitePage.js
```

---

## Key API Endpoints

### Team Management
| Metoda | Endpoint | Popis |
|--------|----------|-------|
| GET | /api/team | Seznam členů týmu (včetně name, status) |
| PATCH | /api/team/{id}/name | Aktualizace jména člena |
| PATCH | /api/team/{id}/role | Aktualizace role |
| DELETE | /api/team/{id} | Odebrání člena |

### Bookings
| Metoda | Endpoint | Popis |
|--------|----------|-------|
| POST | /api/bookings/{id}/assign-lecturer | Self-přiřazení lektora |
| POST | /api/bookings/{id}/assign-lecturer-admin | Admin přiřazení lektora |
| DELETE | /api/bookings/{id}/unassign-lecturer | Odhlášení lektora |

### Schools Multi-Contact CRM
| Metoda | Endpoint | Popis |
|--------|----------|-------|
| GET | /api/schools | Seznam škol s kontakty |
| POST | /api/schools/{id}/contacts | Přidání kontaktu |
| PUT | /api/schools/{id}/contacts/{id} | Úprava kontaktu |
| POST | /api/schools/setup-contacts-table | Vytvoření tabulky |
| POST | /api/schools/migrate-contacts | Migrace kontaktů |

---

## Testovací přístupy
- **Demo účet:** demo@budezivo.cz / Demo2026!
- **Role:** admin
- **Instituce:** Test Muzeum

---

## Backlog

### P1 - Vysoká priorita
- [ ] Propagace jména při přijetí pozvánky — kód je funkční (accept_invitation přenáší name), potřeba ověřit na produkci po deploymentu
- [ ] Production deployment — uživatel musí pushnout na GitHub a spustit migrace

### P2 - Střední priorita
- [ ] i18n přepínač jazyků (existující tlačítko, potřebuje napojení)
- [ ] Hromadné akce pro rezervace (Confirm/Cancel multiple)
- [ ] GDPR správa dat (Export/Delete personal data)

### P3 - Backlog
- [ ] Platební integrace (Stripe - aktuálně PRO je manuální)

### P4 - Mobilní aplikace & Pokročilá analytika
Podrobný rozsah:
- **Mobilní aplikace (PWA/React Native)**
  - Push notifikace pro nové rezervace a potvrzení
  - Offline režim pro prohlížení programů a rezervací
  - QR kód skenování pro check-in skupin
  - Fotogalerie z proběhlých programů
- **Pokročilá analytika**
  - Heatmapa vytíženosti (denní/týdenní/měsíční)
  - Trendy rezervací (rok-over-rok, měsíc-over-měsíc)
  - Konverzní poměry (návštěvy booking stránky vs. dokončené rezervace)
  - Finanční přehledy (příjmy, průměrná cena za žáka)
  - Exporty reportů (PDF, Excel)
  - Dashboard widgety přizpůsobitelné uživatelem
- **Mobilní admin navigace**
  - [x] Záložka Nastavení v mobilní spodní liště (pro adminy)
  - Swipe gesta pro rychlé akce (potvrdit/zrušit rezervaci)
  - Pull-to-refresh pro aktualizaci dat

---

*Poslední aktualizace: 23. března 2026*
