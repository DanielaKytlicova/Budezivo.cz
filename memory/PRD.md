# Budeživo.cz - Product Requirements Document

## Přehled projektu
Multi-tenant SaaS rezervační systém pro české kulturní instituce (muzea, galerie, knihovny).

**Brand:** Budeživo.cz  
**Logo:** Minimalistické logo - check mark ikona + název

## Základní požadavky
- **Cílová skupina:** České veřejné kulturní instituce
- **Jazyk:** Čeština (default)
- **Design:** Mobile-first, responsivní

## Architektura
- **Frontend:** React + TailwindCSS + Shadcn/UI
- **Backend:** FastAPI (Python)
- **Databáze:** MongoDB
- **Auth:** JWT tokens

---

## ✅ IMPLEMENTOVANÉ FUNKCE

### 1. Role systém (AKTUALIZOVÁNO 18.2.2026)
**4 role podle wireframu:**

| Role | Popis |
|------|-------|
| **Správce** | Má plný přístup k nastavení a správě dat |
| **Uživatel/Edukator** | Může vidět a spravovat doprovodné programy a rezervace |
| **Uživatel/Externí lektor** | Může se zapisovat k jednotlivým rezervacím |
| **Uživatel/Pokladní** | Může ke vzniklým rezervacím doplňovat údaje |

**Role-based navigace:**
- Správce: Přehled, Programy, Rezervace, Školy, Statistiky, Tým, Nastavení
- Edukator: Přehled, Programy, Rezervace, Školy, Statistiky
- Lektor: Přehled, Rezervace
- Pokladní: Přehled, Rezervace

### 2. UI/UX (AKTUALIZOVÁNO 18.2.2026)
- **Pozadí login/register:** světlé (#F8FAFC) místo béžové
- **Header:** 
  - Tlačítko "Přihlášení" viditelné i na mobilu
  - Tlačítka pouze na veřejných stránkách

### 3. Branding - Budeživo.cz
- Minimalistické logo: check mark ikona + název "Budeživo.cz"
- Barvy: #4A6FA5 (hlavní), #C4AB86 (akcent), #2B3E50 (tmavá)

### 4. Stránky
- **Homepage:** Hero, funkce, tarify, FAQ, kontakt
- **Login/Register:** 4-krokový wizard pro registraci
- **GDPR:** Ochrana osobních údajů pro ČR
- **Kontakt:** Kontaktní formulář a informace
- **Admin:** Dashboard, Programy, Rezervace, Školy, Statistiky, Tým, Nastavení

### 5. Správa programů - 2 záložky
- **Tab Detail:** základní info, kapacita/trvání, ceník, nastavení, status
- **Tab Nastavení:** nabízené dny, časové bloky, termín, parametry rezervace

### 6. Tarify (opraveno)
- Zdarma: 0 Kč navždy
- Basic: 990/9900 Kč měsíčně/ročně
- Standard: 1990/19900 Kč
- Premium: 3990/39900 Kč

---

## 🔜 NADCHÁZEJÍCÍ ÚKOLY (P1-P2)

### P1 - Statistiky a reporty
- Grafy návštěvnosti
- Export do CSV

### P2 - Email notifikace
- Integrace Resend/SendGrid
- Automatické připomínky

---

## 📋 BUDOUCÍ ÚKOLY (P3)

- Hromadné akce pro rezervace
- GDPR export/smazání dat
- API přístup pro Premium

---

## Technické poznámky

### Backend API - Role
Platné role: `spravce`, `edukator`, `lektor`, `pokladni` (+ legacy: `admin`, `staff`, `viewer`)

### Frontend - AdminLayout
Role-based navigace implementována v `/app/frontend/src/components/layout/AdminLayout.js`

---

## Přihlašovací údaje pro testování
- Správce: test@muzeum.cz / password123
- Edukator: kolega@muzeum.cz / f7471883

---

Poslední aktualizace: 18. února 2026
