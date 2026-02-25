# Budeživo.cz - Product Requirements Document

## Přehled projektu
Multi-tenant SaaS rezervační systém pro české kulturní instituce (muzea, galerie, knihovny).

**Brand:** Budeživo.cz  
**Logo:** Minimalistické logo - check mark ikona + název

## Architektura
- **Frontend:** React + TailwindCSS + Shadcn/UI
- **Backend:** FastAPI (Python)
- **Databáze:** MongoDB (plánován přechod na Supabase)
- **Auth:** JWT tokens

---

## ✅ IMPLEMENTOVANÉ FUNKCE (Únor 2026)

### 1. PRO funkce (Standard/Premium plán)

**Schools - CSV export + hromadná propagace:**
- Export CSV tlačítko - stahování seznamu škol
- Hromadný výběr škol checkboxy
- "Vybrat všechny školy" 
- Rozeslat propagaci programu vybraným školám
- Modal s výběrem programu

**Settings - PRO funkce sekce:**
- CSV export škol toggle
- Hromadná propagace programů toggle
- Email šablona propagace:
  - Předmět: {program_name}
  - Tělo: {program_name}, {program_description}, {reservation_url}, {institution_name}

**Programs - URL generátor:**
- "Generovat URL" v menu programu
- Modal s URL pro externí rezervace
- Kopírovat URL do schránky
- HTML embed kód pro vložení na web
- Náhled rezervační stránky

### 2. Detail rezervace - rozšířená oprávnění

**ADMIN/SPRÁVCE může upravit:**
- Datum rezervace
- Čas rezervace  
- Kontaktní jméno
- Kontaktní email
- Kontaktní telefon
- Skutečná účast (studenti/pedagogové)
- Poznámky

**PEDAGOG/EDUKATOR může upravit:**
- Datum rezervace
- Kontaktní údaje
- Skutečná účast

**POKLADNÍ může upravit:**
- Pouze skutečná účast

**LEKTOR může:**
- Přihlásit se k rezervaci (self-assign)

### 3. Časové bloky - ruční editace
- Textové pole s možností přímého psaní
- Auto-formátování (09 → 09:)
- Ikona hodin jako vizuální prvek
- Nápověda: "Zadejte čas ve formátu HH:MM"

### 4. Kompletní settings
- Správa instituce
- Uživatelé a role
- Notifikace
- Jazyk a místo
- PRO funkce [PRO badge]
- GDPR a reporting dat [PRO badge]

---

## Backend API Endpoints

### PRO Features
```
GET  /api/settings/pro          - PRO nastavení
PUT  /api/settings/pro          - Uložit PRO nastavení
GET  /api/schools/export-csv    - Export CSV (PRO only)
POST /api/schools/send-propagation - Odeslat propagaci (PRO only)
GET  /api/programs/{id}/external-url - URL pro externí rezervace
```

### Bookings (rozšířeno)
```
PUT  /api/bookings/{id}         - Update s date/time/contact
POST /api/bookings/{id}/assign-lecturer - Self-assign lektor
DELETE /api/bookings/{id}/unassign-lecturer - Odhlásit lektora
```

---

## Testovací účet
- **Email:** demo@budezivo.cz
- **Heslo:** demo123
- **Role:** admin
- **Plán:** standard (PRO enabled)

---

## 🔜 NADCHÁZEJÍCÍ ÚKOLY

### P1 - Statistiky a reporty
- Grafy návštěvnosti
- Export do CSV

### P2 - Email notifikace
- Integrace Resend/SendGrid (aktuálně MOCKED)

### P3 - Supabase migrace
- Připraveny SQL skripty v /app/supabase/

---

Poslední aktualizace: Únor 2026
