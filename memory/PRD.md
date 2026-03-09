# Budeživo.cz - Product Requirements Document

## Přehled projektu
Multi-tenant SaaS rezervační systém pro české kulturní instituce (muzea, galerie, knihovny).

**Brand:** Budeživo.cz  
**Logo:** Minimalistické logo - check mark ikona + název

## Architektura

### ✅ NOVÁ MODULÁRNÍ ARCHITEKTURA (Únor 2026)

```
/app/backend/
├── main.py              # Vstupní bod aplikace
├── server.py            # Zpětná kompatibilita
├── core/
│   ├── config.py        # Konfigurace z .env
│   └── security.py      # JWT, hashování hesel
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
│   └── email_templates.py # /api/programs/{id}/email-template/* (NEW)
├── database/
│   ├── supabase.py              # PostgreSQL connection
│   ├── supabase_repositories.py # Repository pattern
│   ├── models.py                # SQLAlchemy models
│   ├── mongodb.py               # [DEPRECATED] MongoDB client
│   └── repositories.py          # [DEPRECATED] MongoDB repos
├── services/
│   └── email_service.py         # Email sending (Resend) + Template rendering (NEW)
└── alembic/                     # Databázové migrace
```

### Technologie
- **Frontend:** React + TailwindCSS + Shadcn/UI + TipTap (rich text editor)
- **Backend:** FastAPI (Python)
- **Databáze:** ~~MongoDB~~ → **Supabase (PostgreSQL)**
- **Auth:** JWT tokens
- **ORM:** SQLAlchemy (async)
- **Migrace:** Alembic
- **Email:** Resend (připraveno k aktivaci)

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

### 5. ✅ Email šablony per program (Březen 2026) - NEW
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

### 6. ✅ Opravy UI a Stability (Březen 2026) - NEW
- [x] **Tlačítko pro zobrazení hesla** v přihlašovacím formuláři
- [x] **Oprava `.map()` chyb** - přidány Array.isArray() kontroly napříč aplikací
  - BookingsPage.js
  - ProgramsPage.js
  - SchoolsPage.js
  - TeamPage.js
  - BookingPage.js (public)
  - PlanPage.js
  - RegisterPage.js
  - toaster.jsx
- [x] **Prevence bílé stránky** - bezpečné zpracování API odpovědí

---

## Databázové schéma (Supabase)

### Tabulky
- `institutions` - organizace/instituce
- `users` - uživatelé s rolemi
- `programs` - vzdělávací programy
- `reservations` - rezervace/bookingy
- `schools` - CRM škol
- `theme_settings` - brandingové nastavení
- `payments` - platební transakce
- `contact_messages` - kontaktní formulář
- `program_email_templates` - email šablony per program (NEW)
- `email_logs` - logy odeslaných emailů (NEW)

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

### Email Templates (NEW)
```
GET    /api/programs/email-config/status             # Status email služby
GET    /api/programs/{id}/email-template             # Získat šablonu
PUT    /api/programs/{id}/email-template             # Uložit šablonu
POST   /api/programs/{id}/email-template/preview     # Náhled s vzorovými daty
POST   /api/programs/{id}/email-template/test        # Odeslat testovací email
GET    /api/programs/{id}/email-logs                 # Logy odeslaných emailů
```

### Template proměnné
```
{{school_name}}          - Název školy/skupiny
{{contact_person}}       - Jméno kontaktní osoby
{{email}}                - E-mail kontaktní osoby
{{phone}}                - Telefon
{{reservation_date}}     - Datum rezervace
{{reservation_time}}     - Čas rezervace
{{number_of_students}}   - Počet žáků
{{number_of_teachers}}   - Počet pedagogů
{{program_name}}         - Název programu
{{program_duration}}     - Délka programu (min)
{{institution_name}}     - Název instituce
{{special_requirements}} - Speciální požadavky
```

### Bookings
```
GET    /api/bookings                        # Seznam rezervací
POST   /api/bookings                        # Vytvořit rezervaci
GET    /api/bookings/{id}                   # Detail
PUT    /api/bookings/{id}                   # Upravit
PATCH  /api/bookings/{id}/status            # Změnit status
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

---

## Testovací účet
- **Email:** test@budezivo.cz
- **Heslo:** test123
- **Role:** admin
- **Instituce:** Test Muzeum

---

## ⚠️ K AKTIVACI

### Email služba (Resend)
Email šablony jsou implementovány, ale odesílání není aktivní.

**Pro aktivaci přidejte do `/app/backend/.env`:**
```
RESEND_API_KEY=re_your_api_key_here
SENDER_EMAIL=noreply@budezivo.cz
```

**Získání API klíče:**
1. Registrace na https://resend.com
2. Dashboard → API Keys → Create API Key
3. Ověření odesílací domény (nebo použít testovací onboarding@resend.dev)

---

## 🔜 NADCHÁZEJÍCÍ ÚKOLY

### P1 - Statistiky a reporty
- [ ] Implementace grafů návštěvnosti
- [ ] Export statistik do CSV

### P2 - Další vylepšení
- [ ] Jazykový přepínač (i18n)
- [ ] Hromadné akce pro rezervace
- [ ] GDPR správa dat

### P3 - Refaktoring
- [ ] BookingPage.js - rozdělit na menší komponenty

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

Poslední aktualizace: 3. března 2026
