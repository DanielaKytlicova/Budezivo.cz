# Budeživo.cz - Product Requirements Document

## Přehled projektu
Multi-tenant SaaS rezervační systém pro české kulturní instituce (muzea, galerie, knihovny).

**Brand:** Budeživo.cz  
**Logo:** Minimalistické logo - check mark ikona + název

## Architektura

### ✅ AKTUÁLNÍ MODULÁRNÍ ARCHITEKTURA (Březen 2026)

```
/app/backend/
├── main.py              # Vstupní bod aplikace
├── server.py            # Zpětná kompatibilita
├── core/
│   ├── config.py        # Konfigurace z .env
│   └── security.py      # JWT, hashování hesel
├── config/
│   └── email_config.py  # Email konfigurace, sender adresy (NEW)
├── models/
│   └── schemas.py       # Pydantic modely
├── routes/
│   ├── auth.py          # /api/auth/*
│   ├── programs.py      # /api/programs/*
│   ├── bookings.py      # /api/bookings/*
│   ├── schools.py       # /api/schools/*
│   ├── settings.py      # /api/settings/*
│   ├── team.py          # /api/team/*
│   ├── dashboard.py     # /api/dashboard/*
│   ├── payments.py      # /api/payments/*
│   ├── availability.py  # /api/availability/*
│   ├── statistics.py    # /api/statistics/*
│   ├── email_templates.py # /api/programs/{id}/email-template/*
│   ├── emails.py        # /api/emails/* (NEW)
│   ├── account.py       # /api/account/* (NEW)
│   └── public.py        # /api/public/*
├── database/
│   ├── supabase.py              # PostgreSQL connection
│   ├── supabase_repositories.py # Repository pattern
│   ├── models.py                # SQLAlchemy models
│   ├── mongodb.py               # [DEPRECATED] MongoDB client
│   └── repositories.py          # [DEPRECATED] MongoDB repos
├── services/
│   └── email_service.py         # Kompletní email service s triggery (UPDATED)
├── templates/
│   └── emails/
│       ├── __init__.py          # Export šablon (NEW)
│       └── templates.py         # 13 HTML email šablon (NEW)
├── docs/
│   └── email-system.md          # Dokumentace email systému (NEW)
└── alembic/                     # Databázové migrace
```

### Technologie
- **Frontend:** React + TailwindCSS + Shadcn/UI + TipTap (rich text editor)
- **Backend:** FastAPI (Python)
- **Databáze:** ~~MongoDB~~ → **Supabase (PostgreSQL)**
- **Auth:** JWT tokens
- **ORM:** SQLAlchemy (async)
- **Migrace:** Alembic
- **Email:** Resend ✅ AKTIVNÍ

---

## ✅ DOKONČENÉ ÚKOLY (Únor-Březen 2026)

### 1. Backend Refaktoring
- [x] Rozdělit monolitický `server.py` do modulární struktury
- [x] Vytvořit `core/` - konfigurace, security
- [x] Vytvořit `models/` - Pydantic schemas
- [x] Vytvořit `routes/` - všechny API endpointy
- [x] Vytvořit `database/` - repository pattern

### 2. Migrace na Supabase (PostgreSQL)
- [x] Připojení k Supabase Transaction Pooler
- [x] SQLAlchemy async modely
- [x] Alembic migrace (001_initial_schema)
- [x] Repository pattern pro všechny entity
- [x] Odstranění MongoDB závislostí z routes
- [x] **100% testů prošlo**

### 3. PRO funkce (Standard/Premium plán)
- [x] CSV export škol
- [x] Hromadná propagace programů
- [x] Email šablony
- [x] URL generátor pro externí rezervace

### 4. Detail rezervace - rozšířená oprávnění
- [x] ADMIN/SPRÁVCE - plný přístup
- [x] EDUKATOR - datum, kontakt, účast
- [x] POKLADNÍ - pouze skutečná účast
- [x] LEKTOR - self-assign k rezervaci

### 5. ✅ Email šablony per program (Březen 2026)
- [x] **Backend:**
  - [x] Email service s Resend API (`services/email_service.py`)
  - [x] Template rendering engine s proměnnými ({{variable}})
  - [x] API endpoints pro CRUD šablon (`routes/email_templates.py`)
  - [x] DB tabulky: `program_email_templates`, `email_logs`
  - [x] Trigger odeslání emailu po vytvoření rezervace
- [x] **Frontend:**
  - [x] Nový tab "Mailing" v editaci programu
  - [x] TipTap rich text editor pro tělo emailu
  - [x] Panel dostupných proměnných s kopírováním
  - [x] Náhled šablony s vzorovými daty
  - [x] Testovací odeslání emailu
- [x] **Testováno:** 100% backend + frontend testy prošly

### 6. ✅ Opravy UI a Stability (Březen 2026)
- [x] **Tlačítko pro zobrazení hesla** v přihlašovacím formuláři
- [x] **Oprava `.map()` chyb** - přidány Array.isArray() kontroly
- [x] **Prevence bílé stránky** - bezpečné zpracování API odpovědí

### 7. ✅ Rozšíření HomePage a ARES integrace (Březen 2026)
- [x] **Nové marketingové sekce na HomePage**
- [x] **Dynamické statistiky na login stránce**
- [x] **ARES integrace pro ověření IČ při registraci**

### 8. ✅ KOMPLETNÍ TRANSAKČNÍ EMAIL SYSTÉM (14. března 2026) - NEW
- [x] **Backend email infrastruktura:**
  - [x] `/config/email_config.py` - Centralizovaná konfigurace
  - [x] `/services/email_service.py` - Rozšířený email service
  - [x] `/templates/emails/templates.py` - 13 HTML šablon
  - [x] `/routes/emails.py` - Test a správa emailů
  - [x] `/routes/account.py` - Správa účtu a smazání
  - [x] `/docs/email-system.md` - Kompletní dokumentace
- [x] **13 typů transakčních emailů:**
  - Account: user_registration_confirmation, account_activation, password_reset, password_changed
  - Reservations: reservation_created_teacher, reservation_created_institution, reservation_confirmed, reservation_rejected, reservation_updated, reservation_cancelled
  - Reminders: reservation_reminder_teacher, reservation_reminder_institution
  - Admin: new_institution_registration
- [x] **Sender adresy:**
  - no-reply@budezivo.cz
  - reservations@budezivo.cz
  - accounts@budezivo.cz
- [x] **Email triggery:**
  - Po vytvoření rezervace → email učiteli + instituci
  - Po potvrzení rezervace → email učiteli
  - Po zrušení rezervace → email učiteli
- [x] **API endpointy:**
  - GET /api/emails/config
  - GET /api/emails/templates
  - GET /api/emails/templates/{name}
  - GET /api/emails/variables
  - POST /api/emails/test
  - GET /api/emails/logs
- [x] **Development mode** - přesměrování emailů na dev@budezivo.cz
- [x] **Email logging** - všechny odeslané emaily v databázi
- [x] **Testováno:** 100% (14/14 backend testů prošlo)

### 9. ✅ SMAZÁNÍ ÚČTU V NASTAVENÍ (14. března 2026) - NEW
- [x] **Backend:**
  - [x] GET /api/account/status - stav účtu a can_delete flag
  - [x] DELETE /api/account/delete - soft delete (deaktivace)
  - [x] Validace: admin nemůže smazat účet pokud je jediný admin
- [x] **Frontend:**
  - [x] "Smazat účet" odkaz v dolní části menu Nastavení (nevýrazný)
  - [x] Sekce smazání účtu s varováním
  - [x] Potvrzovací input (musí napsat "DELETE")
  - [x] Tlačítko disabled dokud není zadáno DELETE
  - [x] Informace o trvalém vymazání dat
- [x] **Testováno:** 100% (UI + API funkční)

### 10. ✅ STATISTIKY PAGE S VIZUALIZACEMI (15. března 2026)
- [x] **Backend:**
  - [x] GET /api/statistics - kompletní statistiky z DB
  - [x] Filtry: měsíc, školní rok (září-červen), pololetí, kalendářní rok, vlastní období
  - [x] GET /api/statistics/export/csv - CSV export (3 typy: reservations, summary, programs)
  - [x] PRO kontrola + csv_export_exception pro admin výjimky
- [x] **Frontend:**
  - [x] Přehledové karty (rezervace, žáci, pedagogové, návštěvníci)
  - [x] Status karty (potvrzené, čekající, dokončené, zrušené)
  - [x] Line chart - trend rezervací
  - [x] Bar chart - nejpopulárnější programy
  - [x] Pie chart - rozložení podle statusu
  - [x] Bar chart - věkové skupiny
  - [x] Export tlačítka (pouze PRO)
  - [x] Filtry období s podporou školního roku
- [x] **Testováno:** 100%

### 11. ✅ VÍCE CÍLOVÝCH SKUPIN PRO PROGRAM (15. března 2026)
- [x] **Backend:**
  - [x] Nový sloupec `target_groups` (JSONB array) v tabulce programs
  - [x] Zpětná kompatibilita s `target_group` (single value)
  - [x] Schema aktualizace
- [x] **Frontend:**
  - [x] Multi-select checkboxy místo single select
  - [x] 7 věkových skupin: MŠ, ZŠ I., ZŠ II., SŠ, Gymnázium, Dospělí, Všechny
  - [x] Validace - alespoň jedna skupina musí být vybrána
  - [x] Zobrazení v seznamu: "MŠ, ZŠ I. +1" pro více skupin
  - [x] Zpětná kompatibilita pro starší programy
- [x] **Testováno:** Funkční

---

## Databázové schéma (Supabase)

### Tabulky
- `institutions` - organizace/instituce
- `users` - uživatelé s rolemi (+ deleted_at pro soft delete)
- `programs` - vzdělávací programy
- `reservations` - rezervace/bookingy
- `schools` - CRM škol
- `theme_settings` - brandingové nastavení
- `payments` - platební transakce
- `contact_messages` - kontaktní formulář
- `program_email_templates` - email šablony per program
- `email_logs` - logy odeslaných emailů

### Role uživatelů
- `admin` - plný přístup
- `spravce` - správa instituce
- `edukator` - správa programů a rezervací
- `lektor` - externí lektor
- `pokladni` - evidence účasti
- `viewer` - pouze čtení

---

## API Endpoints

### Auth
```
POST /api/auth/register     # Registrace
POST /api/auth/login        # Přihlášení
GET  /api/auth/verify       # Ověření tokenu
GET  /api/auth/me           # Aktuální uživatel
POST /api/auth/forgot-password
```

### Programs
```
GET    /api/programs                        # Seznam programů
POST   /api/programs                        # Vytvořit program
GET    /api/programs/{id}                   # Detail programu
PUT    /api/programs/{id}                   # Upravit program
DELETE /api/programs/{id}                   # Smazat program
GET    /api/programs/public/{institution_id} # Veřejné programy
GET    /api/programs/{id}/external-url      # URL pro web
```

### Email Templates (per program)
```
GET    /api/programs/email-config/status             # Status email služby
GET    /api/programs/{id}/email-template             # Získat šablonu
PUT    /api/programs/{id}/email-template             # Uložit šablonu
POST   /api/programs/{id}/email-template/preview     # Náhled s vzorovými daty
POST   /api/programs/{id}/email-template/test        # Odeslat testovací email
GET    /api/programs/{id}/email-logs                 # Logy odeslaných emailů
```

### Emails (NEW - transakční systém)
```
GET    /api/emails/config                   # Konfigurace email služby
GET    /api/emails/templates                # Seznam všech 13 šablon
GET    /api/emails/templates/{name}         # Náhled šablony
GET    /api/emails/variables                # Dostupné proměnné (25)
POST   /api/emails/test                     # Odeslat testovací email
GET    /api/emails/logs                     # Historie odeslaných emailů
```

### Account (NEW)
```
GET    /api/account/status                  # Stav účtu, can_delete flag
DELETE /api/account/delete                  # Soft delete účtu
```

### Bookings
```
GET    /api/bookings                        # Seznam rezervací
POST   /api/bookings                        # Vytvořit rezervaci
GET    /api/bookings/{id}                   # Detail
PUT    /api/bookings/{id}                   # Upravit
PATCH  /api/bookings/{id}/status            # Změnit status (+ email trigger)
POST   /api/bookings/{id}/assign-lecturer   # Přiřadit lektora
DELETE /api/bookings/{id}/unassign-lecturer # Odhlásit lektora
POST   /api/bookings/public/{institution_id} # Veřejná rezervace (+ email trigger)
```

### Settings
```
GET /api/settings/theme                     # Theme nastavení
PUT /api/settings/theme                     # Upravit theme
GET /api/settings/theme/public/{id}         # Veřejný theme
GET /api/settings/pro                       # PRO nastavení
PUT /api/settings/pro                       # Upravit PRO
```

### Public
```
GET /api/public/stats                       # Veřejné statistiky
GET /api/public/ares/{ico}                  # ARES validace IČ
```

---

## Email proměnné (25 dostupných)

```
{{institution_name}}     - Název instituce
{{institution_email}}    - Email instituce
{{institution_phone}}    - Telefon instituce
{{institution_address}}  - Adresa instituce
{{program_name}}         - Název programu
{{program_description}}  - Popis programu
{{program_duration}}     - Délka programu (min)
{{reservation_date}}     - Datum rezervace
{{reservation_time}}     - Čas rezervace
{{reservation_id}}       - ID rezervace
{{teacher_name}}         - Jméno učitele/kontaktu
{{teacher_email}}        - Email učitele
{{teacher_phone}}        - Telefon učitele
{{school_name}}          - Název školy
{{children_count}}       - Počet dětí/žáků
{{teachers_count}}       - Počet pedagogů
{{special_requirements}} - Speciální požadavky
{{user_name}}            - Jméno uživatele
{{user_email}}           - Email uživatele
{{reset_link}}           - Odkaz pro reset hesla
{{activation_link}}      - Aktivační odkaz
{{cancellation_reason}}  - Důvod zrušení
{{rejection_reason}}     - Důvod odmítnutí
{{booking_url}}          - URL rezervačního systému
{{dashboard_url}}        - URL administrace
```

---

## Testovací účet
- **Email:** demo@budezivo.cz
- **Heslo:** Demo2026!
- **Role:** admin
- **Instituce:** Test Muzeum

---

## ✅ EMAIL SLUŽBA (Resend) - AKTIVNÍ

Email systém je plně funkční a konfigurovaný:

```env
RESEND_API_KEY=re_RBiLJpAK_FXh42ngaBPYWyLUdjriA5YX2
SENDER_EMAIL=onboarding@resend.dev
```

**Sender adresy (po ověření domény):**
- no-reply@budezivo.cz
- reservations@budezivo.cz
- accounts@budezivo.cz

**Dokumentace:** `/app/docs/email-system.md`

---

## 🔜 NADCHÁZEJÍCÍ ÚKOLY

### P1 - Statistiky a reporty
- [ ] Implementace grafů návštěvnosti
- [ ] Export statistik do CSV

### P2 - Další vylepšení
- [ ] Jazykový přepínač (i18n)
- [ ] Hromadné akce pro rezervace
- [ ] GDPR správa dat (export, anonymizace)

### P3 - Refaktoring
- [ ] BookingPage.js - rozdělit na menší komponenty

### P3 - Email rozšíření
- [ ] Reminder cron job (automatické připomínky)
- [ ] Webhook pro status updates z Resend
- [ ] A/B testování šablon

---

## Deployment

### Vercel (Frontend)
- URL: budezivo.cz
- Environment: `REACT_APP_BACKEND_URL=https://api.budezivo.cz`

### Railway (Backend)
- URL: api.budezivo.cz
- Dockerfile: `/app/backend/Dockerfile`
- Environment: DATABASE_URL, JWT_SECRET, RESEND_API_KEY, SENDER_EMAIL

### Supabase (Database)
- Dashboard: https://dhuujqpxazadbbdlwago.supabase.co
- Connection string in Railway env vars

---

Poslední aktualizace: 14. března 2026
