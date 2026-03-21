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

### Fáze 3 - Team Invitation System ✅ (Březen 2026)
- [x] **Database:** Tabulka `team_invitations` s tokenem, rolí, expirací
- [x] **API Endpoints:**
  - `POST /api/invitations/send` - Odeslání pozvánky (Admin)
  - `GET /api/invitations/pending` - Seznam čekajících pozvánek (Admin)
  - `DELETE /api/invitations/{id}` - Zrušení pozvánky (Admin)
  - `GET /api/invitations/verify/{token}` - Ověření tokenu (Public)
  - `POST /api/invitations/accept` - Přijetí pozvánky a vytvoření účtu (Public)
  - `POST /api/invitations/test-email` - Testovací email (Admin)
  - `POST /api/invitations/setup-table` - Vytvoření DB tabulky (Admin)
- [x] **Email šablona:** `team_invitation` s personalizovaným obsahem
- [x] **Frontend:** `/accept-invite?token=xxx` stránka
  - Zobrazení info o instituci a roli
  - Formulář na zadání jména a hesla
  - Validace hesla (min 8 znaků, shoda)
  - Chybové stavy (neplatný/expirovaný/použitý token)
  - Úspěšný stav s přesměrováním na login
- [x] **Bezpečnost:**
  - Secure random token (secrets.token_urlsafe)
  - 48 hodin expirace
  - Jednorázové použití tokenu

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
│   │   ├── models.py               # SQLAlchemy modely včetně Feedback, TeamInvitation
│   │   └── supabase.py             # Async session
│   ├── routes/
│   │   ├── feedback.py             # Feedback system API
│   │   ├── invitations.py          # Team Invitation API
│   │   └── ...
│   ├── services/
│   │   └── email_service.py        # Resend integrace
│   └── templates/emails/
│       └── templates.py            # Email šablony včetně team_invitation
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
│               ├── FeedbackPage.js
│               └── AcceptInvitePage.js  # Stránka pro přijetí pozvánky
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

### Team Invitation System
| Metoda | Endpoint | Popis | Role |
|--------|----------|-------|------|
| POST | /api/invitations/send | Odeslání pozvánky | Admin/Správce |
| GET | /api/invitations/pending | Seznam čekajících pozvánek | Auth |
| DELETE | /api/invitations/{id} | Zrušení pozvánky | Admin/Správce |
| GET | /api/invitations/verify/{token} | Ověření tokenu | Public |
| POST | /api/invitations/accept | Přijetí pozvánky | Public |
| POST | /api/invitations/test-email | Testovací email | Admin |
| POST | /api/invitations/setup-table | Vytvoření DB tabulky | Admin |

### Legal System
| Metoda | Endpoint | Popis | Role |
|--------|----------|-------|------|
| GET | /api/legal/terms | Podmínky používání | Public |
| GET | /api/legal/reservation-terms | Text checkboxu + disclaimer | Public |
| GET | /api/legal/terms/version | Aktuální verze | Public |

### Plan Management
| Metoda | Endpoint | Popis | Role |
|--------|----------|-------|------|
| GET | /api/plan/status | Stav plánu a funkce | Auth |
| PUT | /api/plan/upgrade | Aktivace PRO | Admin/Správce |
| PUT | /api/plan/downgrade | Downgrade na FREE | Admin/Správce |
| GET | /api/plan/check-feature/{name} | Ověření přístupu | Auth |
| POST | /api/plan/setup-columns | Migrace DB sloupců | Public |

---

## Testovací přístupy
- **Demo účet:** demo@budezivo.cz / Demo2026!
- **Role:** admin
- **Instituce:** Test Muzeum

---

## Backlog (P0-P2)

### P0 - Kritické
- [ ] DNS nastavení domény budezivo.cz (čeká na uživatele - A záznam ve Wedos)

### P1 - Vysoká priorita ✅ (Dokončeno 21. března 2026)
- [x] Integrovat Team Invitation do TeamPage.js (Admin UI pro odesílání pozvánek)
  - Dialog pro pozvání kolegy (jméno, email, výběr role)
  - Sekce čekajících pozvánek s možností zrušení
  - Zobrazení aktivních členů s rolemi
- [x] Statistiky feedbacku na stats stránce
  - Přehledové karty (celkem, průměr, doporučení)
  - Graf rozložení hodnocení
  - Graf hodnocení podle programu
  - Odkaz na detail zpětné vazby
- [x] Reminder email pro nevyplněné zpětné vazby (7 dní)
  - APScheduler job běží denně v 9:00 CET
  - Odesílá připomínku 7 dní po prvním emailu
  - Sledování reminder_sent_at v Feedback modelu

### Fáze 4 - Legal & PRO Plan ✅ (Březen 2026)

#### Legal/Terms System
- [x] **Podmínky používání** (`/terms`):
  - 11 článků včetně nového "Článek 10: Odpovědnost za realizaci rezervací"
  - Verzovaný systém právních textů (`v1`)
  - API: `GET /api/legal/terms`, `GET /api/legal/reservation-terms`
- [x] **Booking form checkbox**:
  - Povinný checkbox "Odesláním rezervace beru na vědomí..."
  - Frontend + Backend validace (`terms_accepted=true`)
  - DB sloupce: `terms_accepted`, `terms_accepted_at`, `terms_accepted_text_version`
- [x] **Email disclaimer**:
  - "Důležité informace" sekce v potvrzovacím emailu
  - Žlutý banner s právním upozorněním
- [x] **Admin detail rezervace**:
  - Zobrazení souhlasu (ano/ne), datum, verze podmínek

#### PRO Plan Upgrade
- [x] **Plan Management API**:
  - `GET /api/plan/status` - stav plánu a dostupné funkce
  - `PUT /api/plan/upgrade` - aktivace PRO (admin only)
  - `PUT /api/plan/downgrade` - downgrade na FREE (admin only)
  - `GET /api/plan/check-feature/{name}` - ověření přístupu k funkci
- [x] **Settings UI** (`/admin/settings` → PRO funkce):
  - Karta "Nastavení tarifu" s aktuálním plánem (FREE/PRO badge)
  - Tlačítko "Aktivovat PRO" s potvrzovacím modalem
  - Feature gating pro CSV export, bulk email, pokročilé statistiky
- [x] **DB rozšíření**:
  - `institutions.plan_updated_at` (timestamp)

### P2 - Střední priorita
- [ ] i18n přepínač jazyků
- [ ] Hromadné akce pro rezervace (Confirm/Cancel multiple)
- [ ] GDPR správa dat (Export/Delete personal data)

### P3 - Backlog
- [ ] Platební integrace (Stripe)
- [ ] Mobilní aplikace
- [ ] Pokročilá analytika

---

*Poslední aktualizace: 21. března 2026*