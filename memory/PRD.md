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

### 1. Branding - Budeživo.cz (AKTUALIZOVÁNO 17.2.2026)
- Minimalistické logo: check mark ikona + název "Budeživo.cz"
- Barvy: #4A6FA5 (hlavní), #C4AB86 (akcent)
- Na mobilu při přihlášení/správě: pouze ikona loga
- Header logika:
  - Veřejné stránky (/, /kontakt, /gdpr): tlačítka "Přihlášení" a "Vyzkoušet zdarma"
  - "Přihlášení" viditelné i na mobilu
  - Login/Register/Admin: pouze logo bez tlačítek

### 2. Stránka Kontakt (NOVÉ 17.2.2026)
- Hero sekce
- Kontaktní informace (e-mail, telefon, adresa, provozní doba)
- Kontaktní formulář (jméno, e-mail, instituce, předmět, zpráva)
- API endpoint `/api/contact`

### 3. Opravené tarify (OPRAVENO 17.2.2026)
- Pevně definované ceny:
  - Zdarma: 0 Kč (navždy)
  - Basic: 990/9900 Kč (měsíčně/ročně)
  - Standard: 1990/19900 Kč
  - Premium: 3990/39900 Kč
- Správné zobrazení při přepínání měsíčně/ročně

### 4. Role systém
**3 role s různými oprávněními:**

| Role | Oprávnění |
|------|-----------|
| **Administrátor** | Plný přístup - správa týmu, nastavení, všechny funkce |
| **Zaměstnanec** | Správa programů, rezervací, škol |
| **Návštěvník** | Pouze prohlížení dat |

### 5. Registrace instituce - 4-krokový wizard
- Krok 1: Základní údaje (název, typ, země, email, heslo, GDPR)
- Krok 2: Informace o instituci (adresa, město, IČ/DIČ, logo, barvy)
- Krok 3: Nabídka návštěvní doby (dny, časové bloky, termín)
- Krok 4: Hlavní nastavení programů

### 6. Správa programů - 2 záložky
- **Tab Detail:** základní info, kapacita/trvání, ceník, nastavení, status
- **Tab Nastavení:** nabízené dny, časové bloky, termín, parametry rezervace

### 7. GDPR stránka pro ČR
- 9 sekcí podle českých právních požadavků
- Aktualizovaný název na Budeživo.cz

### 8. Admin Dashboard
- Přehled rezervací, rychlé akce, statistiky
- Role-based navigace

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
│   ├── Header.js (BudezivoLogo, isPublicPage logika)
│   ├── Footer.js
│   └── AdminLayout.js
├── pages/
│   ├── public/
│   │   ├── HomePage.js
│   │   ├── LoginPage.js
│   │   ├── RegisterPage.js
│   │   ├── BookingPage.js
│   │   ├── GDPRPage.js
│   │   └── ContactPage.js (NOVÉ)
│   └── admin/
│       └── ...
```

### Backend API
- `POST /api/contact` - kontaktní formulář
- `GET /api/team` - seznam členů týmu
- `POST /api/team/invite` - pozvání člena
- `PATCH /api/team/{id}/role` - změna role
- `DELETE /api/team/{id}` - odebrání člena

---

## Přihlašovací údaje pro testování
- Admin: test@muzeum.cz / password123
- Staff: kolega@muzeum.cz / f7471883

---

Poslední aktualizace: 17. února 2026
