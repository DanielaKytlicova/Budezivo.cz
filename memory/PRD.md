# Bude Živo - PRD (Product Requirements Document)

## Přehled projektu
Budeživo.cz je komplexní SaaS platforma pro správu vzdělávacích programů, rezervací a institucí v České republice.

## Technologický stack
- **Frontend:** React 18, TailwindCSS, Shadcn/UI, Axios
- **Backend:** FastAPI, SQLAlchemy Async, Pydantic, slowapi, icalendar, msal, httpx
- **Databáze:** Supabase (PostgreSQL) + pg_advisory_xact_lock
- **Emaily:** Resend API (s ICS přílohou)
- **Integrace:** Microsoft Graph API (Outlook calendar sync)
- **Scheduler:** APScheduler (feedback, GDPR, auto-archivace, Outlook sync 5min)

---

## Implementované funkce

### Fáze 1-16 (předchozí)
- Core MVP, Feedback, Team, Legal, CRM, Booking, Kolize, GDPR
- VOP, Security, One-off bloky, Archive, Onboarding, Email Theming
- Pricing, Mobile fix, Demo data, Statistics fix

### Fáze 17 - Audit Log + Program Filtering (8.4.2026)
- [x] Audit Log: DB + API + admin stránka
- [x] Program filtering: BookingPage filtrační panel + URL params
- [x] Admin URL generátor s filtry

### Fáze 18A - ICS Export (8.4.2026)
- [x] ICS Feed: `/api/calendar/institution/{id}.ics`, `/program/{id}.ics`, `/reservation/{id}.ics`
- [x] Tlačítko "Přidat do Outlooku" (admin + veřejná success stránka)
- [x] ICS příloha v potvrzovacím emailu

### Fáze 18B - Kolizní systém Hardening (9.4.2026)
- [x] Kolize lektora při přiřazení (409 při konfliktu)
- [x] Místnosti: CRUD API + room_id na programech + kolizní kontrola
- [x] Advisory Lock: pg_advisory_xact_lock brání race conditions

### Fáze 18C - Microsoft Outlook Integration (9.4.2026)
- [x] **OAuth2 flow**: `GET /api/microsoft-calendar/connect` → MS login → callback → token storage
- [x] **Token management**: access_token + refresh_token s automatickým obnovením
- [x] **Calendar sync**: Stahuje 30 dní eventů z Outlook → `availability_blocks`
- [x] **Polling sync**: APScheduler job každých 5 minut pro automatickou synchronizaci
- [x] **Override logika**: `POST /blocks/{id}/override` — povolí/zablokuje rezervace v čase Outlook eventu
- [x] **Kolizní integrace**: `check_availability_blocks()` v collision_service kontroluje Outlook bloky
- [x] **Frontend UI**: Outlook karta na stránce Dostupnost — připojit/odpojit/sync/override
- [x] **Popup OAuth**: postMessage komunikace mezi popup oknem a rodičovským oknem

### DB Schema (nové tabulky)
```
user_calendar_integrations: id, user_id, institution_id, provider, access_token, 
    refresh_token, expires_at, microsoft_user_id, is_active, last_sync_at, sync_error
availability_blocks: id, user_id, institution_id, start_time, end_time, source, 
    external_event_id, title, override
rooms: id, institution_id, name, capacity, equipment, is_active
programs: + room_id (FK → rooms.id)
```

---

## Testovací přístupy
- **Demo účet:** demo@budezivo.cz / Demo2026!
- **Test reports:** iteration_21-27

---

## Klíčové API endpointy (nové)
- `GET /api/microsoft-calendar/connect` — zahájí OAuth flow
- `GET /api/microsoft-calendar/callback` — OAuth callback
- `GET /api/microsoft-calendar/status` — stav připojení
- `POST /api/microsoft-calendar/disconnect` — odpojení
- `POST /api/microsoft-calendar/sync` — manuální sync
- `GET /api/microsoft-calendar/blocks` — seznam bloků
- `POST /api/microsoft-calendar/blocks/{id}/override` — toggle override
- `GET/POST /api/rooms` + `PATCH/DELETE /api/rooms/{id}` — CRUD místností

---

## Backlog

### P0 - Hotovo
- [x] Feedback questions propojeny s veřejným formulářem
- [x] Výběr lektorů pro kolizní kontrolu
- [x] Pilotní modul Události a přihlášky + QR platby

### P2 - Střední priorita
- [ ] i18n přepínač jazyků (CZ/EN)

### P3 - Backlog
- [ ] Social proof na landing page
- [ ] Microsoft webhook subscription (real-time místo polling)

### P4 - Budoucnost
- [ ] Pokročilá analytika, Stripe/Fakturoid, PWA, 2FA, Alembic
- [ ] Události: automatické párování plateb z banky
- [ ] Události: Apple Pay / Google Pay (přes gateway)
- [ ] Události: zálohy a doplatky, fakturace
- [ ] Události: QR check-in účastníků, exporty

---

## Důležitá poznámka k OAuth
Pro testování na preview prostředí je potřeba v Azure Portal přidat Redirect URI:
`https://audit-enhance-fix.preview.emergentagent.com/api/auth/microsoft/callback`

Aktuálně je nastaveno pouze: `https://budezivo.cz/api/auth/microsoft/callback`

### Fáze 21 - Refresh Token, WAF, OAuth Persistence, Alembic (10.4.2026)
- [x] Refresh Token: Access token zkrácen na 15 min, refresh token v DB (30 dní), rotace, revokace
- [x] Nové endpointy: POST /api/auth/refresh, POST /api/auth/logout
- [x] Frontend AuthContext přepsán: auto-refresh, 401 interceptor, server-side logout
- [x] OAuth State Persistence: in-memory _oauth_states nahrazen DB tabulkou oauth_states
- [x] WAF middleware: blokace SQL injection, XSS, timing attacks v query/body/path
- [x] Alembic: framework inicializován, baseline migrace stampnuta
- [x] Scheduler: automatické čištění expirovaných tokenů (každou hodinu)

### Fáze 22 - Upload loga instituce (10.4.2026)
- [x] Backend: POST /api/settings/logo/upload (validace typu + velikosti, Emergent Object Storage)
- [x] Backend: GET /api/settings/logo/{path} (veřejné servírování s cache)
- [x] Frontend: Drag & drop zóna, preview, tlačítko odstranit logo
- [x] Integrace: Emergent Object Storage inicializován při startu

### Fáze 23 - httpOnly Cookie, Filtrace, Pokročilá analytika (10.4.2026)
- [x] httpOnly Cookie: JWT v httpOnly Secure SameSite=Lax cookie (dual-mode: cookie + header)
- [x] Filtrace booking response: interní pole odstraněna z veřejného endpointu
- [x] Source Map Removal: GENERATE_SOURCEMAP=false
- [x] Pokročilá analytika: Heatmapa vytíženosti, Roční trend, Top školy, Konverzní poměr
- [x] Backlog: Finanční přehled (čeká na integraci cenníku do programů)

### Fáze 24 - Bugfixy: Kalendář off-by-one + Kolize lektora (11.4.2026)
- [x] Bug 1: formatDate v LecturerAvailabilityPage, DashboardPage, ProgramsPage opravena z toISOString (UTC) na lokální datum
- [x] Bug 2: check_lecturer_available_for_block nyní kontroluje recurring I one-off bloky; lektor s definovanou dostupností ale ne pro daný den = nedostupný
- [x] Zpětná kompatibilita: lektor bez jakékoli dostupnosti = bez omezení

### Fáze 25 - Bugfix: Bílá obrazovka při úpravě rezervace (11.4.2026)
- [x] Bug: updateBooking posílal VŠECHNA pole editData (včetně actual_students=''), Pydantic 422 + React crash při renderování error objektu
- [x] Fix: updateBooking nyní posílá pouze pole relevantní pro aktuální editMode (datetime/attendance/contact/notes)
- [x] Fix: Všechny toast.error handlery bezpečně zpracovávají ne-stringové chybové odpovědi
- [x] Ověřeno: Reschedule email se odesílá rezervujícímu při změně termínu (funguje přes Resend API)

### Fáze 26 - Fix: Kolize lektora v rezervačním systému (12.4.2026)
- [x] Bug: Měsíční kalendář + denní dostupnost nekontrolovaly dostupnost lektora při collision_resources=["lecturer"]
- [x] Fix: Oba endpointy (calendar + availability) nyní kontrolují lektory s definovaným rozvrhem
- [x] Fix: Pokud žádný lektor s rozvrhem nemá čas → blok/den označen jako nedostupný
- [x] Fix: Lektoři bez definovaného rozvrhu nejsou zahrnuti do kolizní logiky
- [x] Podpora assigned_lecturer_id i plošné kontroly všech lektorů s rozvrhem

### Fáze 27 - 4 úkoly (12.4.2026)
- [x] CSS fix: přetékání názvu školy v záložce Rezervace (truncate + min-w-0)
- [x] Bug fix: Auto-dokončení potvrzených rezervací s minulým datem (scheduler job)
- [x] Outlook sync: Dynamické okno synchronizace dle max_days_before_booking + 60 dnů (min 180)
- [x] Zpětná vazba: on/off per program, výchozí (hvězdičky + doporučení), individuální otázky (PRO, max 5, text/scale/yesno)
- [x] DB migrace: feedback_enabled + feedback_questions na tabulce programs (Alembic)

### Fáze 28 - Fix: URL program parameter + expanze časových bloků (12.4.2026)
- [x] Bug 1: BookingPage s ?program=ID nyní přeskočí na kalendář a zobrazí pouze vybraný program
- [x] Bug 2: Časová okna se expandují na individuální sloty dle trvání programu (30min interval)
- [x] 90min program s oknem 08:30-12:00: sloty 08:30-10:00 až 10:30-12:00 (11:00 se NEZOBRAZÍ - přesahuje 12:00)
- [x] Overlap-based booking detekce pro korektní blokování expandovaných slotů
- [x] Programy s přesnými sloty (např. '09:00-10:30') se neexpandují

### Fáze 29 - Validace časových bloků v nastavení programu (12.4.2026)
- [x] Validační dialog při ukládání: upozornění na překrývající se bloky (overlap)
- [x] Validace cleanup_time: varování když mezera mezi bloky < doba úklidu + návrh řešení
- [x] Validace preparation_time: info o kolizi přípravy s předchozím blokem
- [x] Tlačítka "Upravit nastavení" (vrátí na tab) / "Beru na vědomí" (uloží přesto)
- [x] Bez varování pokud se bloky nepřekrývají

### Fáze 30 - Refaktoring + P0 Feedback + Kolize lektorů + Mobile fix (13.4.2026)
- [x] Refaktoring: ProgramsPage.js rozdělena na ProgramCollisionTab, ProgramFeedbackTab, ProgramUrlModal (~1306 → 1306 + 418 + 157 + 242 řádků)
- [x] P0: Veřejný feedback formulář nyní zobrazuje program-level feedback_questions (z JSONB sloupce programs.feedback_questions)
- [x] Kolize lektora: nový sloupec collision_lecturer_ids (JSONB) na tabulce programs — admin může vybrat konkrétní lektory pro kontrolu kolize
- [x] Dostupnost: denní i měsíční kalendář respektuje collision_lecturer_ids (pokud jsou vybrány, kontrolují se jen oni)
- [x] Mobile fix: URL generator modal používá max-h-[85dvh] + overflow-y-auto pro scrollovatelný obsah
- [x] Zpětná kompatibilita: pokud collision_lecturer_ids je prázdné, chování zůstává beze změny (kontrolují se všichni lektoři)

### Fáze 31 - Pilotní modul Události a přihlášky + Platby (13.4.2026)
- [x] Feature flag systém: tabulka feature_flags s key/allowed_institution_ids, služba is_feature_enabled
- [x] Feature flag seeded: events_module pro demo účet (669e71b2-...)
- [x] Modely: Event, EventDate, EventApplication, EventPayment, InstitutionPaymentSettings, FeatureFlag
- [x] Events CRUD API: GET/POST/PUT/DELETE /api/events, s feature flag guardem
- [x] Event dates: POST/DELETE /api/events/{id}/dates
- [x] Přihlášky: POST /api/events/public/{institution_id}/apply (veřejný, bez auth)
- [x] QR platba: SPD formát (SPD*1.0*ACC:...*AM:...*CC:CZK*X-VS:...*MSG:...)
- [x] Platební nastavení: GET/PUT /api/events/settings/payment per instituce
- [x] Admin UI: EventsPage s taby (Detail, Termíny, Formulář, Přihlášky, Platby)
- [x] Admin UI: Navigační položka "Události" viditelná jen pro whitelistované účty
- [x] Admin UI: Správa přihlášek (schválit/zamítnout/označit zaplaceno)
- [x] Admin UI: Formulářový builder (dynamické pole text/email/number/select/checkbox)
- [x] Veřejný flow: PublicEventsPage — seznam → detail → výběr termínu → formulář → QR success
- [x] Izolace: modul neovlivňuje stávající programy/rezervace, oddělený routing /events
- [x] Příprava gateway: InstitutionPaymentSettings s payment_mode (qr/gateway/both), provider pole

### Fáze 31b - UI opravy Události + Platební nastavení v Settings (14.4.2026)
- [x] Přihlášky: field_ID nahrazeny lidsky čitelnými labely z form_fields (Jméno, Mail, Telefonní číslo...)
- [x] Boolean hodnoty zobrazeny jako "Ano"/"Ne" místo "true"/"false"
- [x] Platební nastavení přesunuto do Nastavení → Platební nastavení (PRO badge)
- [x] Platební nastavení viditelné jen pokud je events_module povolený (feature flag)
- [x] Formulářový builder: select options po řádcích (textarea) místo čárkou
- [x] Formulářový builder: šipky nahoru/dolů pro řazení polí
- [x] Veřejná stránka: BookingHeader s logem instituce
- [x] Checkbox: single render bez zdvojení labelu

### DB Schema (nové tabulky - Fáze 31)
```
feature_flags: id, key, enabled, allowed_institution_ids, description
events: id, institution_id, name, type, description, capacity, price, currency, is_active, is_archived, image_url, form_fields
event_dates: id, event_id, start_datetime, end_datetime, capacity_override
event_applications: id, institution_id, event_id, event_date_id, status, payment_status, total_amount, variable_symbol, applicant_data, applicant_email, applicant_name
institution_payment_settings: id, institution_id, payment_mode, provider, iban, account_number, bank_code, account_name, gateway_api_key, gateway_secret
event_payments: id, application_id, institution_id, provider, status, amount, currency, variable_symbol, provider_payment_id, qr_payload, paid_at
```

*Poslední aktualizace: 13. dubna 2026*
