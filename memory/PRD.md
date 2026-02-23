# Budeživo.cz - Product Requirements Document

## Přehled projektu
Multi-tenant SaaS rezervační systém pro české kulturní instituce (muzea, galerie, knihovny).

**Brand:** Budeživo.cz  
**Logo:** Minimalistické logo - check mark ikona + název

## Architektura
- **Frontend:** React + TailwindCSS + Shadcn/UI
- **Backend:** FastAPI (Python)
- **Databáze:** Supabase (PostgreSQL) s RLS
- **Auth:** Supabase Auth + JWT tokens

---

## 🆕 SUPABASE PRODUCTION CONFIG (Prosinec 2025)

### Vytvořené soubory:
```
/app/supabase/
├── .env.example                    # Šablona environment proměnných
├── DEPLOYMENT_CHECKLIST.md         # Checklist pro nasazení
├── docs/
│   ├── PRODUCTION_CONFIG.md        # Kompletní produkční dokumentace
│   └── ROLE_PERMISSIONS.md         # Matice oprávnění rolí
├── migrations/
│   ├── 001_schema.sql              # Databázové schéma
│   └── FULL_MIGRATION.sql          # Kompletní migrační skript
├── policies/
│   ├── 002_rls_policies.sql        # RLS politiky
│   └── 003_rls_cashier_restriction.sql  # Omezení pro pokladní
└── scripts/
    ├── 004_audit_triggers.sql      # Audit logging
    ├── 005_backup_recovery.sql     # Backup & GDPR
    └── 006_performance_optimization.sql  # Indexy & optimalizace
```

### RLS (Row Level Security):
- ✅ Povoleno na všech tabulkách
- ✅ Multi-tenant izolace (institution_id)
- ✅ Role-based přístup (admin, edukator, lektor, pokladni, viewer)
- ✅ Veřejný přístup pro booking (anon role)

### Bezpečnostní opatření:
- Service role key pouze na serveru
- Anon key bezpečný pro klienta
- Audit logging všech změn
- GDPR export a anonymizace

---

## ✅ IMPLEMENTOVANÉ FUNKCE

### 1. Nastavení - kompletně přepracované (AKTUALIZOVÁNO 18.2.2026)

**Hlavní menu nastavení:**
- Správa instituce
- Uživatelé a role (odkaz na TeamPage)
- Notifikace
- Jazyk a místo
- GDPR a reporting dat [PRO]
- Odhlásit se

**Správa instituce:**
- Základní informace: Název, Typ, IČ/DIČ
- Fakturační údaje: Adresa, Město, PSČ, Země
- Kontaktní informace: Mobil, Email, Webovky
- Logo a vizuál: Logo upload, Hlavní/Sekundární barevnost

**Notifikace a upozornění:**
- Mailová upozornění: Nová rezervace, Potvrzení, Zrušení
- SMS upozornění [PRO]

**Jazyk a místo:**
- Jazykové rozhraní (CS/EN)
- Časové pásmo
- Datový formát (DD.MM.RRRR atd.)
- Časový formát (24h/12h)

**GDPR a export dat:**
- Banner "Vylepši svůj plán"
- Export dat a report
- Ukládání dat (smaž po uplynutí)
- Nastavení soukromí

### 2. Role systém
**4 role podle wireframu:**
- Správce - plný přístup
- Uživatel/Edukator - programy a rezervace
- Uživatel/Externí lektor - zapisování k rezervacím
- Uživatel/Pokladní - doplňování údajů

### 3. UI/UX
- Pozadí login/register: světlé (#F8FAFC)
- Mobilní navigace optimalizována

### 4. Stránky
- Homepage, Login, Register, GDPR, Kontakt
- Admin: Dashboard, Programy, Rezervace, Školy, Statistiky, Tým, Nastavení

---

## 🔜 NADCHÁZEJÍCÍ ÚKOLY (P1-P2)

### P1 - Statistiky a reporty
- Grafy návštěvnosti
- Export do CSV

### P2 - Email notifikace
- Integrace Resend/SendGrid

---

## Backend API - Settings

```
GET /api/institution/settings - získání nastavení instituce
PUT /api/institution/settings - aktualizace nastavení
PUT /api/settings/notifications - notifikace
PUT /api/settings/locale - jazyk a místo
PUT /api/settings/gdpr - GDPR nastavení
```

---

## Přihlašovací údaje
- Správce: test@muzeum.cz / password123

---

## 🔜 NADCHÁZEJÍCÍ ÚKOLY

### P0 - Supabase Nasazení
1. Vytvořit Supabase projekt (production)
2. Spustit `FULL_MIGRATION.sql`
3. Nastavit environment proměnné
4. Upravit backend pro Supabase klienta

### P1 - Statistiky a reporty
- Grafy návštěvnosti
- Export do CSV

### P2 - Email notifikace
- Integrace Resend/SendGrid

---

Poslední aktualizace: Prosinec 2025
