# KulturaBooking - Product Requirements Document

## Přehled projektu
Multi-tenant SaaS rezervační systém pro české kulturní instituce (muzea, galerie, knihovny).

## Základní požadavky
- **Cílová skupina:** České veřejné kulturní instituce
- **Jazyk:** Čeština (default) + Angličtina
- **Design:** Mobile-first, responsivní

## Architektura
- **Frontend:** React + TailwindCSS + Shadcn/UI
- **Backend:** FastAPI (Python)
- **Databáze:** MongoDB
- **Auth:** JWT tokens

---

## ✅ IMPLEMENTOVANÉ FUNKCE

### 1. Veřejná marketingová stránka (HomePage)
- Hero sekce s CTA
- Problem/Solution sekce
- Cenový přehled (Free, Basic, Standard, Premium)
- FAQ sekce
- "Domluvit online ukázku" dialog

### 2. Registrace instituce - 4-krokový wizard (NOVÉ - 17.2.2026)
**Krok 1 - Základní údaje:**
- Název instituce
- Typ instituce (Muzeum, Galerie, Knihovna, Botanická zahrada, Divadlo, Jiné)
- Země (ČR, SK)
- Admin email
- Heslo
- GDPR souhlas (povinný)

**Krok 2 - Informace o instituci:**
- Adresa instituce
- Město (výběr z českých měst)
- IČ/DIČ
- Logo instituce (URL)
- Hlavní barevnost (color picker)
- Sekundární barevnost (color picker)

**Krok 3 - Nabídka návštěvní doby:**
- Dny v týdnu (Po-Ne toggle buttons)
- Časové bloky (s možností přidat/odebrat)
- Termín (od-do datum)

**Krok 4 - Hlavní nastavení programů:**
- Výchozí popis pro pedagogy
- Výchozí délka (min)
- Výchozí kapacita
- Výchozí cílová skupina

### 3. Správa programů - 2 záložky (NOVÉ - 17.2.2026)
**Tab Detail:**
- Základní informace: Název, Popis, Cílová skupina
- Kapacita a trvání: Doba trvání, Max kapacita, Min účastníků
- Ceník: Tarif (Zdarma/Placený), Cena
- Další nastavení:
  - Vyžaduje schválení (switch)
  - Zveřejnit program (switch)
  - Odeslat upozornění mailem (switch)
- Status: Aktivní / Koncept / Archivovat (radio)

**Tab Nastavení:**
- Nabízené dny (Po-Ne buttons)
- Časové bloky (seznam s přepínači)
- Termín (Začátek/Konec programu)
- Parametry rezervace:
  - Min počet dnů před rezervací
  - Max počet dnů před rezervací
  - Potřebná doba na přípravu (min)
  - Potřebný čas na úklid (min)

**Seznam programů:**
- Karty s názvem, popisem, štítky (cílová skupina, status)
- Ikony: doba trvání, kapacita
- Akce: Duplikovat, Archivovat
- Plovoucí FAB tlačítko pro vytvoření nového

### 4. GDPR stránka pro ČR (NOVÉ - 17.2.2026)
9 sekcí podle českých právních požadavků:
1. Správce osobních údajů
2. Účely zpracování
3. Právní základ zpracování
4. Rozsah zpracovávaných údajů
5. Doba uchování údajů
6. Vaše práva
7. Kontakt a podání stížnosti (ÚOOÚ)
8. Zabezpečení údajů
9. Používání cookies

### 5. Admin Dashboard
- Dnešní rezervace
- Nadcházející skupiny
- Vytížení kapacity
- Limit rezervací
- Rychlé akce

### 6. Další admin stránky
- Rezervace (seznam, filtry, akce)
- Školy/Skupiny
- Statistiky (placeholder)
- Nastavení (téma, barvy, logo)
- Tarif (upgrade plány)

### 7. Veřejná rezervační stránka
- 4-krokový booking flow
- Výběr programu
- Výběr termínu (kalendář)
- Kontaktní údaje
- Potvrzení

---

## 🔜 NADCHÁZEJÍCÍ ÚKOLY (P1)

### Stripe integrace
- Test klíče dostupné
- Implementovat platební flow pro upgrade tarifu

### Role systém
- Admin, Staff, Viewer role
- Oprávnění v admin panelu

### Přepínač jazyků
- Funkční toggle CZ/EN v headeru
- i18n soubory připraveny (cs.json, en.json)

---

## 📋 BUDOUCÍ ÚKOLY (P2-P3)

### P2
- Statistiky a reporty (grafy)
- Hromadné akce pro rezervace

### P3
- Email notifikace (Resend/SendGrid integrace)
- GDPR export/smazání dat
- API přístup pro Premium

---

## Technické poznámky

### Backend modely (server.py)
- `UserCreate` - rozšířen o step 2-4 pole
- `ProgramBase` - rozšířen o nové atributy (requires_approval, time_blocks, booking params)
- `Institution` - rozšířen o default settings

### Frontend struktura
```
/app/frontend/src/
├── pages/
│   ├── public/
│   │   ├── HomePage.js
│   │   ├── LoginPage.js
│   │   ├── RegisterPage.js (4-krokový wizard)
│   │   ├── BookingPage.js
│   │   ├── GDPRPage.js (NOVÉ)
│   │   └── ForgotPasswordPage.js
│   └── admin/
│       ├── DashboardPage.js
│       ├── ProgramsPage.js (2 záložky)
│       ├── BookingsPage.js
│       ├── SchoolsPage.js
│       ├── StatisticsPage.js
│       ├── SettingsPage.js
│       └── PlanPage.js
```

### API Endpoints
- `POST /api/auth/register` - rozšířen o nová pole
- `POST /api/programs` - rozšířen o nové atributy
- `PUT /api/programs/{id}` - aktualizace s novými poli

### Testování
- Backend: 100% (21/21 testů)
- Frontend: 95% (drobné accessibility opravy provedeny)
- Test report: `/app/test_reports/iteration_2.json`

---

## Přihlašovací údaje pro testování
- Email: test@muzeum.cz
- Heslo: password123

---

Poslední aktualizace: 17. února 2026
