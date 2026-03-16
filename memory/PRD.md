# Bude Živo - PRD (Product Requirements Document)

## Původní zadání
Rezervační systém pro kulturní instituce (muzea, galerie, knihovny) v České republice. Multi-tenant SaaS aplikace s podporou více institucí.

## Technický stack
- **Frontend:** React, TailwindCSS, Recharts
- **Backend:** FastAPI, SQLAlchemy
- **Databáze:** PostgreSQL (Supabase)
- **E-maily:** Resend API
- **Deployment:** Vercel (frontend), Railway (backend)

## Implementované funkce

### Core funkce
- [x] Registrace a přihlášení uživatelů
- [x] Multi-tenant architektura (více institucí)
- [x] Správa programů (CRUD)
- [x] Veřejná rezervační stránka
- [x] Kalendář dostupnosti
- [x] Správa rezervací (potvrzení/odmítnutí)
- [x] Správa škol (kontakty)

### Nové funkce (prosinec 2025)
- [x] **Transakční e-mailový systém** - Resend integrace, HTML šablony
- [x] **Smazání účtu** - GDPR compliance
- [x] **Stránka statistik** - Grafy, filtry, CSV export (PRO)
- [x] **Multi-select cílových skupin** - Více věkových skupin na program
- [x] **Datum platnosti programu** - start_date/end_date u programů
- [x] **Logo instituce na booking** - Vlastní logo v headeru rezervační stránky
- [x] **Theme na booking stránkách** - Barvy instituce aplikované na celou stránku

### Bug fixy (prosinec 2025)
- [x] Railway healthcheck endpoint (`/health`)
- [x] Registrační e-mail trigger
- [x] Hardcoded URL oprava pro produkci
- [x] Ukládání datumů platnosti programu (start_date/end_date)

## Blokované úkoly (vyžadují akci uživatele)

### P0 - Kritické
1. **DNS nastavení pro `budezivo.cz`**
   - Přidat A záznam u Wedos: `@ -> 76.76.21.21`
   
2. **Vercel env proměnná**
   - `REACT_APP_BACKEND_URL=https://api.budezivo.cz`

### P1 - Důležité
3. **Ověření domény v Resend**
   - Přidat DNS záznamy pro SPF/DKIM

## Backlog (prioritizovaný)

### P2 - Střední priorita
- [ ] Přepínač jazyků (i18n)
- [ ] Hromadné akce pro rezervace

### P3 - Nízká priorita
- [ ] Kompletní GDPR data management
- [ ] Refaktoring BookingPage.js

## Klíčové API endpointy
- `POST /api/auth/login` - Přihlášení
- `GET /api/programs` - Seznam programů
- `POST /api/programs` - Vytvoření programu
- `PUT /api/programs/{id}` - Úprava programu
- `GET /api/programs/public/{inst_id}` - Veřejné programy
- `POST /api/bookings/public/{inst_id}` - Vytvoření rezervace
- `GET /api/statistics` - Statistiky
- `POST /api/emails/test-email` - Test e-mailu
- `DELETE /api/users/me` - Smazání účtu
- `GET /health` - Health check

## Testovací přihlašovací údaje
- **Email:** demo@budezivo.cz
- **Heslo:** Demo2026!

## Architektura souborů
```
/app
├── backend/
│   ├── routes/           # API endpointy
│   ├── services/         # Business logika (email_service.py)
│   ├── database/         # SQLAlchemy modely a repozitáře
│   ├── templates/emails/ # HTML e-mailové šablony
│   └── main.py           # FastAPI aplikace
├── frontend/
│   └── src/
│       ├── pages/        # React stránky
│       └── components/   # UI komponenty
└── docs/
    └── email-system.md   # Dokumentace e-mailového systému
```

---
*Poslední aktualizace: 16. března 2026*
