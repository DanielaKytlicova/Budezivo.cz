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
│   └── statistics.py    # /api/statistics/*
├── database/
│   ├── supabase.py              # PostgreSQL connection
│   ├── supabase_repositories.py # Repository pattern
│   ├── models.py                # SQLAlchemy models
│   ├── mongodb.py               # [DEPRECATED] MongoDB client
│   └── repositories.py          # [DEPRECATED] MongoDB repos
├── services/                    # Business logika (připraveno)
└── alembic/                     # Databázové migrace
```

### Technologie
- **Frontend:** React + TailwindCSS + Shadcn/UI
- **Backend:** FastAPI (Python)
- **Databáze:** ~~MongoDB~~ → **Supabase (PostgreSQL)**
- **Auth:** JWT tokens
- **ORM:** SQLAlchemy (async)
- **Migrace:** Alembic

---

## ✅ DOKONČENÉ ÚKOLY (Únor 2026)

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

### Bookings
```
GET    /api/bookings                        # Seznam rezervací
POST   /api/bookings                        # Vytvořit rezervaci
GET    /api/bookings/{id}                   # Detail
PUT    /api/bookings/{id}                   # Upravit
PATCH  /api/bookings/{id}/status            # Změnit status
POST   /api/bookings/{id}/assign-lecturer   # Přiřadit lektora
DELETE /api/bookings/{id}/unassign-lecturer # Odhlásit lektora
POST   /api/bookings/public/{institution_id} # Veřejná rezervace
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

## 🔜 NADCHÁZEJÍCÍ ÚKOLY

### P1 - Statistiky a reporty
- [ ] Implementace grafů návštěvnosti
- [ ] Export statistik do CSV

### P2 - Email notifikace
- [ ] Integrace Resend/SendGrid (aktuálně MOCKED)

### P3 - Další vylepšení
- [ ] Jazykový přepínač (i18n)
- [ ] Hromadné akce pro rezervace
- [ ] GDPR správa dat

---

## Supabase konfigurace

**Connection:**
```
postgresql://postgres.dhuujqpxazadbbdlwago:[PASSWORD]@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
```

**Dashboard:** https://dhuujqpxazadbbdlwago.supabase.co

---

Poslední aktualizace: 25. února 2026
