# Bubeživo.cz - Product Requirements Document

## Přehled projektu
Multi-tenant SaaS rezervační systém pro české kulturní instituce (muzea, galerie, knihovny).

**Brand:** Bubeživo.cz  
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

### 1. Branding - Bubeživo.cz (NOVÉ - 17.2.2026)
- Minimalistické logo: check mark ikona + název "Bubeživo.cz"
- Barvy: #4A6FA5 (hlavní), #C4AB86 (akcent)
- Na mobilu při přihlášení/správě: pouze ikona loga
- Skryté tlačítko "Vyzkoušet zdarma" na mobilu v headeru

### 2. Role systém (NOVÉ - 17.2.2026)
**3 role s různými oprávněními:**

| Role | Oprávnění |
|------|-----------|
| **Administrátor** | Plný přístup - správa týmu, nastavení, všechny funkce |
| **Zaměstnanec** | Správa programů, rezervací, škol |
| **Návštěvník** | Pouze prohlížení dat |

**API Endpointy:**
- `GET /api/team` - seznam členů týmu
- `POST /api/team/invite` - pozvání nového člena
- `PATCH /api/team/{id}/role` - změna role
- `DELETE /api/team/{id}` - odebrání člena

**UI stránka:** `/admin/team` - Správa týmu

### 3. Veřejná marketingová stránka (HomePage)
- Hero sekce s CTA
- Problem/Solution sekce
- Cenový přehled (Free, Basic, Standard, Premium)
- FAQ sekce
- "Domluvit online ukázku" dialog

### 4. Registrace instituce - 4-krokový wizard
**Krok 1 - Základní údaje:**
- Název instituce
- Typ instituce (Muzeum, Galerie, Knihovna, Botanická zahrada, Divadlo, Jiné)
- Země (ČR, SK)
- Admin email, Heslo
- GDPR souhlas

**Krok 2 - Informace o instituci:**
- Adresa, Město, IČ/DIČ
- Logo instituce (URL)
- Hlavní/sekundární barevnost

**Krok 3 - Nabídka návštěvní doby:**
- Dny v týdnu (Po-Ne toggle)
- Časové bloky
- Termín (od-do)

**Krok 4 - Hlavní nastavení programů:**
- Výchozí popis, délka, kapacita, cílová skupina

### 5. Správa programů - 2 záložky
**Tab Detail:**
- Základní informace: Název, Popis, Cílová skupina
- Kapacita a trvání: Doba trvání, Max/Min kapacita
- Ceník: Tarif (Zdarma/Placený), Cena
- Další nastavení: Vyžaduje schválení, Zveřejnit, Email notifikace
- Status: Aktivní / Koncept / Archivovat

**Tab Nastavení:**
- Nabízené dny, Časové bloky
- Termín programu
- Parametry rezervace (min/max dní, příprava, úklid)

### 6. GDPR stránka pro ČR
9 sekcí podle českých právních požadavků

### 7. Admin Dashboard
- Přehled rezervací
- Rychlé akce
- Statistiky

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

### Frontend struktura
```
/app/frontend/src/
├── components/layout/
│   ├── Header.js (s BubezivoLogo komponentou)
│   ├── Footer.js
│   └── AdminLayout.js (role-based navigace)
├── pages/
│   ├── public/
│   │   ├── HomePage.js
│   │   ├── LoginPage.js (minimal header)
│   │   ├── RegisterPage.js
│   │   ├── BookingPage.js
│   │   └── GDPRPage.js
│   └── admin/
│       ├── DashboardPage.js
│       ├── ProgramsPage.js
│       ├── BookingsPage.js
│       ├── SchoolsPage.js
│       ├── StatisticsPage.js
│       ├── SettingsPage.js
│       ├── PlanPage.js
│       └── TeamPage.js (NOVÉ)
```

### Backend API - Team Management
- `GET /api/team` - TeamMember model
- `POST /api/team/invite` - TeamInvite model
- `PATCH /api/team/{id}/role` - RoleUpdate model
- `DELETE /api/team/{id}`

### Role-based Access Control
Navigace v AdminLayout filtrována podle role uživatele:
- Admin: všechny položky včetně Tým a Nastavení
- Staff: Přehled, Programy, Rezervace, Školy, Statistiky
- Viewer: Přehled, Programy, Rezervace

---

## Přihlašovací údaje pro testování
- Admin: test@muzeum.cz / password123
- Staff: kolega@muzeum.cz / f7471883

---

## Změny od minulé verze
- ~~KulturaBooking~~ → **Bubeživo.cz**
- Přidán role systém (Admin, Staff, Viewer)
- Skrytý přepínač jazyků
- Přeskočena Stripe integrace
- Mobile UI optimalizace (pouze ikona loga při přihlášení)

---

Poslední aktualizace: 17. února 2026
