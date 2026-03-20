# Bude Živo - PRD (Product Requirements Document)

## Přehled projektu
Budeživo.cz je komplexní SaaS platforma pro správu vzdělávacích programů, rezervací a institucí v České republice.

## Technologický stack
- **Frontend:** React 18, TailwindCSS, Shadcn/UI, Axios
- **Backend:** FastAPI, SQLAlchemy Async, Pydantic
- **Databáze:** Supabase (PostgreSQL)
- **Emaily:** Resend API
- **Deployment:** Vercel (Frontend), Railway (Backend)
- **Scheduler:** APScheduler (integrován v backendu)

---

## Implementované funkce

### Fáze 1 - Core MVP ✅
- [x] Registrace a přihlášení uživatelů (JWT)
- [x] Správa institucí a programů
- [x] Rezervační systém s kalendářem dostupnosti
- [x] Dynamická témata a loga institucí na booking stránkách
- [x] Správa škol a kontaktů
- [x] Dashboard s přehledem statistik
- [x] Transakční emaily (rezervace, potvrzení, reset hesla)

### Fáze 2 - Feedback System ✅ (Březen 2026)
- [x] **Database:** Tabulky `feedbacks` a `feedback_questions`
- [x] **API Endpoints:**
  - `POST /api/feedback/questions` - Vytvoření otázky (Admin)
  - `GET /api/feedback/questions` - Seznam otázek
  - `PUT /api/feedback/questions/{id}` - Úprava otázky
  - `DELETE /api/feedback/questions/{id}` - Deaktivace otázky
  - `GET /api/feedback/submissions` - Seznam zpětných vazeb s filtry
  - `GET /api/feedback/statistics` - Statistiky
  - `GET /api/feedback/export` - Export do CSV
  - `GET /api/feedback/public/{token}` - Veřejný formulář
  - `POST /api/feedback/public/{token}` - Odeslání zpětné vazby
- [x] **Admin UI:** Stránka `/admin/feedback` se záložkami:
  - Zpětné vazby (tabulka s filtry)
  - Otázky (CRUD správa)
  - Statistiky (rozložení hodnocení, programy)
- [x] **Veřejný formulář:** `/feedback/{token}`
- [x] **APScheduler:** Automatické odesílání emailů 1 pracovní den po rezervaci
- [x] **Role-based access:** Admin (full), Edukator (view/filter)

### UI/UX Aktualizace ✅ (Březen 2026)
- [x] Nové SVG logo Budeživo.cz (navbar, login, footer, emaily)
- [x] Nový favicon
- [x] Barva pozadí změněna z #FDFCF8 na #F8F9FA
- [x] **Dashboard vylepšení:**
  - Přepínač pohledů (Seznam / Kalendář)
  - Seznam: Filtry (Nadcházející události, Nedávno vytvořené)
  - Kalendář: Týdenní pohled s rezervacemi, navigace, barevné bloky
  - Modal s detailem rezervace po kliknutí
  - Responzivní design

---

## Architektura

```
/app
├── backend/
│   ├── main.py                     # FastAPI app + scheduler init
│   ├── scheduler.py                # APScheduler pro feedback emaily
│   ├── core/
│   │   └── security.py             # JWT s role field
│   ├── database/
│   │   ├── models.py               # SQLAlchemy modely včetně Feedback
│   │   └── supabase.py             # Async session
│   ├── routes/
│   │   ├── feedback.py             # Feedback system API
│   │   └── ...
│   └── services/
│       └── email_service.py        # Resend integrace
├── frontend/
│   └── src/
│       ├── components/layout/
│       │   ├── AdminLayout.js      # Navigace s Feedback položkou
│       │   ├── Header.js           # Nové SVG logo
│       │   └── Footer.js           # Nové SVG logo
│       └── pages/
│           ├── admin/
│           │   └── FeedbackAdminPage.js
│           └── public/
│               └── FeedbackPage.js
```

---

## API Endpoints

### Feedback System
| Metoda | Endpoint | Popis | Role |
|--------|----------|-------|------|
| GET | /api/feedback/questions | Seznam otázek | Auth |
| POST | /api/feedback/questions | Vytvoření otázky | Admin |
| PUT | /api/feedback/questions/{id} | Úprava otázky | Admin |
| DELETE | /api/feedback/questions/{id} | Deaktivace otázky | Admin |
| GET | /api/feedback/submissions | Seznam zpětných vazeb | Auth |
| GET | /api/feedback/statistics | Statistiky | Auth |
| GET | /api/feedback/export | CSV export | Admin |
| GET | /api/feedback/public/{token} | Veřejný formulář data | Public |
| POST | /api/feedback/public/{token} | Odeslání zpětné vazby | Public |
| POST | /api/feedback/setup-tables | Vytvoření DB tabulek | Admin |

---

## Testovací přístupy
- **Demo účet:** demo@budezivo.cz / Demo2026!
- **Role:** admin
- **Instituce:** Test Muzeum

---

## Backlog (P0-P2)

### P0 - Kritické
- [ ] DNS nastavení domény budezivo.cz (čeká na uživatele - A záznam ve Wedos)

### P1 - Vysoká priorita
- [ ] Statistiky zpětné vazby na stats stránce (průměrná hodnocení, grafy)
- [ ] Reminder email pro nevyplněné zpětné vazby (7 dní)

### P2 - Střední priorita
- [ ] i18n přepínač jazyků
- [ ] Hromadné akce pro rezervace (Confirm/Cancel multiple)
- [ ] GDPR správa dat (Export/Delete personal data)

### P3 - Backlog
- [ ] Platební integrace (Stripe)
- [ ] Mobilní aplikace
- [ ] Pokročilá analytika

---

*Poslední aktualizace: 20. března 2026*
