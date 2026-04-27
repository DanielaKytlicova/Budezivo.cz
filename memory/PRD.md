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
- [x] Propagační mailingy (kampaně) s relevance engine
- [x] 4-úrovňový plán (Free/Start/PRO/PRO+) s hard-lock feature gating

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
`https://arch-enhance-v59.preview.emergentagent.com/api/auth/microsoft/callback`

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

### Fáze 33 - Export přihlášek (15.4.2026)
- [x] XLSX export: stylovaný Excel s barevným záhlavím, podmíněným formátováním (zelená=zaplaceno, červená=nezaplaceno), české názvy sloupců, sumární řádek
- [x] CSV export: UTF-8 BOM, středníkový oddělovač, české labely polí (ne field_ID)
- [x] PDF potvrzení: hlavička s názvem instituce, údaje události + termínu, údaje účastníka z formuláře, QR platba, status přihlášky
- [x] Veřejný PDF endpoint: automaticky generovaný při přihlášení, ke stažení bez autentifikace
- [x] Admin UI: XLSX/CSV tlačítka v záložce Přihlášky, PDF u každé přihlášky
- [x] Veřejný UI: tlačítko "Stáhnout potvrzení (PDF)" na success stránce po přihlášení
- [x] Oprava diakritiky: 155+ textů v emailových šablonách opraveno (Dobrý den, Připomínka, zpětná vazba...)

### Fáze 34 - Hlídání volného termínu / Waitlist (15.4.2026)
- [x] Nová tabulka `waitlist_entries` (teacher_name, school_name, email, phone, participant_count, request_type, dates, preferred_time, status, admin_note)
- [x] API: POST /api/waitlist (veřejný, bez auth) — validace programu, datumů, duplikátů
- [x] API: GET /api/waitlist (admin, filtry program_id/status), PATCH /api/waitlist/{id} (status + admin_note)
- [x] API: GET /api/waitlist/count/{program_id} (veřejný count aktivních zájemců)
- [x] Admin UI: WaitlistPage — navigace "Zájemci" (Bell ikona), skládací seznam, filtry, detail s kontakty, dialog pro změnu statusu
- [x] Veřejný UI: WaitlistModal v BookingPage — zobrazí se při obsazených slotech ("Hlídat volný termín"), formulář s typem požadavku (konkrétní datum / rozsah), potvrzení
- [x] Potvrzovací email: šablona waitlist_confirmation s údaji programu, datumu, preferencí
- [x] Edge cases: duplikáty blokované (409), minulá data odmítnuta, nevalidní rozsah
- [x] Fáze 2 skeleton: waitlist_service.py s find_matching_entries() a notify_candidates() (loguje, neposílá)
- [x] Fáze 2 IMPLEMENTOVÁNA: Semi-automatické párování — hooky v bookings.py (zrušení rezervace) a unified_availability.py (odstranění výjimky)
- [x] Fáze 2: notify_candidates() odesílá email "Uvolnil se termín" a mění status na 'contacted'
- [x] Fáze 2: find_matching_entries() filtruje podle preferred_time_of_day (morning/midday/afternoon/any)
- [x] PDF diakritika opravena: DejaVuSans font embedován místo Helvetica
- [x] Přihlášky: skládací detail (collapsed/expanded)
- [x] Auto-výběr termínu při jednom dostupném

### Fáze 32 - Sjednocený systém Dostupnosti (14.4.2026)
- [x] Centrální `availability_service.py` — `evaluate_program_slots()` a `evaluate_lecturer_slots()` jako single source of truth
- [x] Dvouvrstvá architektura: Vrstva 1 (base availability + exceptions) → Vrstva 2 (kolize)
- [x] Detailní slot statusy: available / booked / blocked_exception / blocked_lecturer / blocked_room / blocked_parallel / blocked_program / outside_base_availability
- [x] Nová tabulka `availability_exceptions` (scope_type, scope_id, date, start_time, end_time, reason, created_by)
- [x] API: GET/POST/DELETE `/api/availability-unified/exceptions`
- [x] API: GET `/api/availability-unified/program/{id}/slots?date=` a `/lecturer/{id}/slots?date=`
- [x] Exception kontrola integrována do `check_booking_collision()` — rezervace blokována při aktivní výjimce
- [x] Exception kontrola integrována do `check_lecturer_collision_for_assignment()` — přiřazení lektora blokováno
- [x] Frontend: `UnifiedAvailabilityPage.js` s přepínačem Programová/Osobní
- [x] Frontend: Týdenní kalendář s barevně odlišenými sloty + legenda
- [x] Frontend: Kliknutí na dostupný slot → dialog "Uzavřít" s důvodem
- [x] Frontend: Kliknutí na uzavřený slot → dialog "Obnovit dostupnost"
- [x] Záložka Kolize v ProgramsPage zachována beze změny (nadřazená vrstva)

### DB Schema (nové tabulky - Fáze 31)
```
feature_flags: id, key, enabled, allowed_institution_ids, description
events: id, institution_id, name, type, description, capacity, price, currency, is_active, is_archived, image_url, form_fields
event_dates: id, event_id, start_datetime, end_datetime, capacity_override
event_applications: id, institution_id, event_id, event_date_id, status, payment_status, total_amount, variable_symbol, applicant_data, applicant_email, applicant_name
institution_payment_settings: id, institution_id, payment_mode, provider, iban, account_number, bank_code, account_name, gateway_api_key, gateway_secret
event_payments: id, application_id, institution_id, provider, status, amount, currency, variable_symbol, provider_payment_id, qr_payload, paid_at
```

### Fáze 36 - Hierarchický plánový systém (19.4.2026)
- [x] Přepis plan_service.py: FEATURES s plan_level, automatický výpočet PLAN_FEATURES (kumulativní) a PLAN_DELTAS (delta)
- [x] 3 placené plány: Start (490 Kč, 9 features), PRO (990 Kč, +10 features), PRO+ (1990 Kč, +7 features)
- [x] Žádná duplikace features — UI generováno z configu ("Vše z X +")
- [x] Delta view modal: gained/lost features při přepínání plánu
- [x] events_basic (PRO) vs events_payments (PRO+) split
- [x] require_feature() FastAPI dependency pro backend enforcement
- [x] Přímá aktivace PRO trvale zablokována (HTTP 400)
- [x] Request flow: objednávka → pending → platba → admin aktivace

### Fáze 37 - Backend Feature Enforcement (19.4.2026)
- [x] require_feature() dependency aplikován na všechny chráněné endpointy
- [x] Router-level: mailings, audit-log, rooms, microsoft-calendar
- [x] Per-endpoint: events, waitlist, statistics, schools export
- [x] Chybové zprávy v češtině: "Tato funkce vyžaduje plán PRO"
- [x] Testováno: 24/24 backend testů (iteration_49.json)

### Fáze 38 - Frontend Feature Gating + Landing Page Pricing (19.4.2026)
- [x] usePlanFeatures hook + UpgradeModal pro zamčené funkce
- [x] Admin sidebar: lock ikony na zamčených navigacích
- [x] Landing page: tarify aktualizovány na 4 plány s hierarchií
- [x] Settings: "Zobrazit plány" místo "Aktivovat PRO"
- [x] Testováno: 100% frontend (iteration_50.json)

### Fáze 39 - Superadmin + Billing + Usage Metrics (19.4.2026)
- [x] DB: billing_orders, usage_metrics tabulky + billing fields na institutions
- [x] Billing: BillingProviderInterface (Manual + Fakturoid placeholder)
- [x] Usage tracking: track_usage(), get_institution_usage()
- [x] Superadmin dashboard: overview, instituce, detail, plan control, billing orders
- [x] Plan request → automatický billing order
- [x] Testováno: 18/18 (iteration_51.json)


### Fáze 40 - Superadmin delete, PDF font fix, QR IBAN, Auto-renewal + Usage Analytics (20.4.2026)
- [x] Superadmin: DELETE /api/superadmin/institutions/{id} — soft delete s ochranou
  - Vyžaduje přesnou shodu `confirmation_name` s názvem instituce
  - Nelze smazat vlastní instituci
  - Zároveň soft-deletuje všechny uživatele (nelze se přihlásit)
  - Audit trail zapsán do billing_note (kdo, kdy, proč)
- [x] Frontend modal pro mazání instituce s blokovaným tlačítkem dokud se název neshoduje
- [x] PDF generace: DejaVuSans fonty nabalené do /app/backend/fonts/ (nezávislé na instalaci systému)
  - registerFontFamily: `<b>` tagy v Paragraph nyní používají DejaVuSans-Bold
  - Oprava chybných diakritických znaků (■) v PDF přihláškách
- [x] QR platba: SPAYD nyní používá platný CZ IBAN místo surového čísla/banky
  - `cz_account_to_iban()` s mod-97 algoritmem
  - Příklad: 295033917/0300 → CZ6003000000000295033917
- [x] Scheduler: denní job `process_plan_expiration` v 5:00 UTC
  - Pro expired plány: auto_renew=True → billing order; jinak → status=expired + limity na Free
- [x] Superadmin endpoint: GET /api/superadmin/usage-analytics
  - `by_feature` (adoption rate), `by_plan`, `top_institutions`
- [x] Superadmin endpoint: POST /api/superadmin/run-expiration-job (manuální trigger)
- [x] Frontend: záložka Usage + Expirace na Superadmin stránce
- [x] Testováno: 13/13 backend, 100% frontend (iteration_52.json)

### Fáze 41 - Comgate platební brána pro Event přihlášky (P1) (20.4.2026)
- [x] Backend: abstrakce `services/payment_gateways/` (base + factory + comgate)
  - `PaymentGatewayBase` (initiate / parse_webhook / query_status)
  - Módy: MOCK (prázdné klíče) / TEST (prefix `TEST_`) / LIVE
  - Per-instituční přihlašovací údaje (z `InstitutionPaymentSettings`)
- [x] Nové endpointy `/api/event-payments/*`:
  - POST `/initiate` (gated `events_payments` = PRO+)
  - POST `/webhook/comgate` (autorita, validuje merchant+secret)
  - POST `/mock/complete` (pouze MOCK, interní simulátor)
  - GET `/by-vs/{inst}/{vs}` (veřejný polling endpoint)
- [x] Hardening: webhook odmítá externí volání v MOCK režimu (403)
- [x] Webhook auto-potvrzení přihlášky (když instituce má `auto_confirm_paid` feature PRO+)
  - payment_status → paid, status → approved
- [x] Frontend: public `/payment/mock` (CZ simulátor) + `/payment/return` (polling 2s × 15)
- [x] Frontend: veřejná přihláška – tlačítko „Zaplatit online" když `gateway_enabled`
- [x] Admin Nastavení – pole Merchant ID + Secret + nápověda pro TEST_ prefix a mock režim
- [x] VOP § 7.8 — doplněna klauzule „Platby jsou zpracovávány prostřednictvím platební brány třetí strany (např. Comgate)..."
- [x] Otestováno: 13/13 backend + 100% frontend E2E (iteration_53.json)
- [ ] BUDOUCÍ: GoPay jako druhý provider (abstrakce připravena, stačí `gopay.py`)

### Fáze 42 - Social proof na landing page (P3) (20.4.2026)
- [x] Upravený endpoint `GET /api/public/stats` — vrací institutions, reservations, programs, events, institution_types (breakdown), satisfaction (práh snížen na 5 institucí)
- [x] HomePage: nová sekce mezi Hero a Pain Points s:
  - Animovanou stats lištou (count-up animace, `StatCard` komponenta, cs-CZ lokalizace čísel)
  - Institution type chips (Muzea, Galerie, Knihovny, Botanické zahrady, Kulturní centra, Školy) s live countem
  - Dvě testimonial karty (placeholder — skutečné reference budou doplněny po souhlasu institucí)
- [x] data-testid: `social-proof-section`, `trust-stats`, `type-chip-{key}`, `testimonial-{i}`
- [x] Ověřeno screenshotem: sekce renderuje správně s 12+ institucí / 13+ programy+akce / 63+ rezervací / 98%


### Fáze 42b - Social proof úprava: skrytí testimonials (20.4.2026)
- [x] Testimonials karty zakomentovány (`{false && TESTIMONIALS.length > 0 ...}`) — pole `TESTIMONIALS` zůstalo v kódu jako placeholder s instrukcemi, jak je znovu aktivovat (jen přepnout flag)
- [x] Celá Social Proof sekce zabalena do `stats?.show_stats &&` — pokud backend vrátí show_stats=false (méně než 5 institucí), sekce se automaticky ze landing page odstraní
- [x] Akceptační kritérium: čísla a typy institucí zůstávají, ale zobrazí se pouze když máme dostatek reálných dat

- [ ] BUDOUCÍ: Apple Pay — automaticky dostupné jakmile instituce povolí v Comgate dashboardu


### Fáze 35 - Propagační mailingy / Kampanový modul (15.4.2026)

### Fáze 43 - Superadmin: karta zřizovatele + seznam uživatelů instituce (20.4.2026)
- [x] Backend: `/api/superadmin/institutions/{id}` rozšířen o `owner` (první admin uživatel podle created_at) a `users` (všichni non-deleted uživatelé instituce)
  - každý objekt obsahuje: id, name, first_name, last_name, email, role, status, last_login_at, created_at
- [x] Frontend InstitutionDetail: nová karta „Zřizovatel / administrátor účtu" s iniciálou, jménem, e-mailem, rolí, datem registrace, posledním přihlášením a statusem
- [x] Frontend: nový rozbalovací panel „Uživatelé instituce" — klikací header, tabulka read-only (jméno+avatar / e-mail / role / status / registrace / poslední přihlášení) se štítkem „POUZE ČTENÍ"
- [x] Role překlady a barvy (admin/správce/edukátor/lektor/pokladní/viewer)
- [x] Ověřeno screenshotem na instituci „Botanická zahrada Liberec"

- [x] DB modely: MailingCampaign, MailingCampaignProgram, MailingCampaignRecipient, MailingRecipientProgram
- [x] Alembic migrace pro 4 nové tabulky
- [x] Backend CRUD: POST/GET/PUT/DELETE /api/mailings, včetně draft managementu

### Fáze 44 - Superadmin Audit Log (20.4.2026)
- [x] Backend helper `_log_superadmin` pro jednotné logování do `audit_logs` tabulky s flagem `details.superadmin=true`
- [x] Audit zápisy zabudovány do: plan_change, institution_delete, billing_confirm, billing_cancel, run_expiration_job
- [x] Nový endpoint `GET /api/superadmin/audit-log` — platform-wide (JOIN s Institution pro jméno), filtrovatelný dle institution_id
- [x] `GET /api/superadmin/institutions/{id}` rozšířen o `audit_log` (top 20 superadmin zásahů pro danou instituci)
- [x] Frontend: nová záložka „Historie" s tabulkou Čas / Akce / Instituce / Detaily (barevné akční badge, čitelné detaily změn plánu)
- [x] Frontend: v detailu instituce nová karta „Historie zásahů superadmina" (per-instituce)
- [x] Filtr striktní: `details.superadmin = true` (ignoruje regular admin akce i když jsou od superadmin emailu)

- [x] Relevance engine: párování program.target_groups (ms_3_6, zs1_7_12...) ↔ school.tags (MŠ, ZŠ, SŠ...)
- [x] 4 režimy výběru příjemců: relevant_only, all, manual, relevant_plus_manual

### Fáze 45 - Platform migrace + Impersonace (20.4.2026)
- [x] Endpoint `POST /api/superadmin/setup/move-to-platform` — idempotentní, vytvoří instituci „Budeživo Platform" (type=other, PRO+, activated_by=system) a přesune všechny uživatele ze SUPERADMIN_EMAILS tam
- [x] Po migraci už není demo@budezivo.cz vlastníkem Test Muzea, takže Test Muzeum lze volně smazat (blokace „Nelze smazat vlastní instituci" odpadla)
- [x] `create_jwt_token` rozšířeno o parametry `impersonated_by_user_id`, `impersonated_by_email`, `expires_minutes`
- [x] `require_superadmin` striktně odmítá impersonační tokeny (403 „Superadmin akce nelze provést během impersonace")
- [x] Endpointy:
  - `POST /api/superadmin/impersonate/start/{user_id}` — startuje impersonaci (odmítá self, jiné superadminy, neaktivní uživatele; lifetime 30 min)
  - `POST /api/superadmin/impersonate/stop` — ukončí pouze s impersonačním tokenem, vrátí čerstvý token pro původního superadmina
- [x] `/api/auth/me` vrací `impersonation: {active, original_email, original_user_id}`
- [x] AuthContext: funkce `startImpersonation()` a `stopImpersonation()` + `applyImpersonationToken()` (neobnovuje refresh token — zůstává původní pro čistý návrat)
- [x] `ImpersonationBanner` — sticky žlutý banner na vrchu všech admin stránek se štítkem „IMPERSONACE", emailem + rolí cílového usera, jménem skutečného superadmina a tlačítkem „Ukončit impersonaci"
- [x] Sloupec „Akce → Impersonovat" v tabulce uživatelů instituce (disabled pro sebe, jiné superadminy, neaktivní; prompt na důvod)
- [x] Audit log zaznamenává `impersonation_start` (s target_email, role, reason, TTL) a `impersonation_end`
- [x] Testováno: 8/8 backend (iteration_54.json), frontend sidebar + institutions list verified screenshotem

- [x] Preview endpoint: /api/mailings/preview-recipients (statistiky, varování, seznam příjemců)
- [x] Výchozí české šablony pro MŠ/ZŠ/SŠ/obecné publikum
- [x] Background odesílání emailů přes BackgroundTasks (ne v HTTP requestu)
- [x] Snapshoty: content_snapshot, selection_snapshot, programs_snapshot při odeslání

### Fáze 46 - Feature flag management + Password reset (20.4.2026)
- [x] `GET/PUT /api/superadmin/feature-flags[/{key}]` — superadmin nyní může spravovat pilot feature flags (enable/disable globálně nebo per-instituce)
- [x] `POST /api/superadmin/reset-password` — superadmin může resetovat heslo libovolného uživatele; pokud email patří do SUPERADMIN_EMAILS a uživatel neexistuje, vytvoří ho v Budeživo Platform instituci (bootstrap sekundárního superadmina)
- [x] Bootstrapován `admin@budezivo.cz` s heslem `Admin2026!` (zapsáno v test_credentials.md)
- [x] `events_module` feature flag rozšířen o `Oblastní galerie Lázně` (8ca0ac56-…) a `Budeživo Platform` (c18a10b9-…) — události nyní vidí i kytlicova.vanilie@gmail.com
- [x] Audit log zaznamenává `feature_flag_update` (before/after diff) a `superadmin_bootstrap`

- [x] Per-příjemce: matching_reason (proč vybrán), relevantní programy (MailingRecipientProgram)
- [x] Frontend: stránka /admin/mailings s archivem kampaní

### Fáze 47 - UI pro správu Feature flagů (20.4.2026)
- [x] Nová záložka „Feature flagy" v Superadmin panelu (data-testid `tab-features`)
- [x] Komponenta `FeatureFlagCard` zobrazuje:
  - Ikonku + čitelný název + technický klíč + popis
  - Globální toggle „Whitelist režim ↔ Globálně ZAPNUTO" (jedním klikem)
  - Whitelist sekci s vyhledáváním + checkboxy per-instituce (s plan badge)
  - Batch ukládání změn (tlačítko „Uložit změny" se zobrazí pouze když je něco dirty)
  - Upozornění při globálně zapnutém flagu („whitelist se nepoužívá, ale uloží se")
- [x] Metadata pro jednotlivé flagy v `FEATURE_FLAG_LABELS` (zatím jen `events_module`)
- [x] Změny jdou přes existující `PUT /api/superadmin/feature-flags/{key}` → automatický audit log

- [x] Frontend: 4-krokový průvodce (Programy → Příjemci → Text emailu → Odeslání)
- [x] Frontend: detail kampaně s příjemci, programy, snapshoty
- [x] Frontend: tlačítko "Rozeslat nabídku" na kartě programu v ProgramsPage
- [x] Frontend: navigace "Mailingy" v sidebar pod "Školy"

### Fáze 48 - Program: Cena informativní místo Ceníku (22.4.2026)
- [x] Nová Program kolona `pricing_info` (Text) — volný text jako „30,-/dítě – pedagog zdarma"
- [x] ALTER TABLE programs ADD COLUMN pricing_info TEXT (provedeno na DB)
- [x] ProgramCreate schema + create/update routes + repositories + public programs endpoint předávají pricing_info
- [x] Frontend ProgramsPage: „Ceník" sekce nahrazena „Cena pro účastníky" — volné textové pole, max 200 znaků, bez tariff dropdownu, bez číselné ceny
- [x] Odstraněn dead link „Vylepši svůj tarif → Chceš k programům přidat fotografie" (nevedlo nikam)
- [x] Public `/book/{inst}` — zobrazuje pricing_info jako jantarový badge vedle délky programu
- [x] Email template: `_reservation_details_box` zobrazuje řádek „Cena:" pouze pokud je pricing_info vyplněné — řetězec z DB jde escapem přes HTML a nahrazuje newlines za `<br>`
- [x] `_build_email_context` propaguje `program_pricing_info` do všech reservation-related mailů (potvrzení, zrušení, vytvoření)

- [x] UI fix: "Zájemci" přesunuto ze sidebaru do hlavičky stránky Rezervace

### DB Schema (nové tabulky - Fáze 35)
```
mailing_campaigns: id, institution_id, created_by, name, type, status, recipient_mode, subject, greeting, intro_text, closing_text, signature, content_snapshot, selection_snapshot, programs_snapshot, total_recipients, sent_count, failed_count, sent_at
mailing_campaign_programs: id, campaign_id, program_id, display_order
mailing_campaign_recipients: id, campaign_id, school_id, contact_id, email, school_name, contact_name, status, sent_at, failure_reason, email_provider_id, matching_reason
mailing_recipient_programs: id, recipient_id, program_id, program_name, program_target_groups
```

### Fáze 49 - Fotografie programů (feature-flagged) (22.4.2026)
- [x] DB: ALTER TABLE programs ADD COLUMN image_url TEXT (provedeno na Supabase)
- [x] Nový feature flag `program_photos` seed (enabled=false, whitelist ∅ → superadmin volitelně přidá instituci)
- [x] Backend: `GET /api/programs/features/check-access` — vrací {program_photos: bool} pro aktuální instituci
- [x] Backend: `POST /api/programs/{id}/image/upload` (multipart, max 5 MB, ALLOWED_IMAGE_TYPES) — gated `_require_program_photos`
- [x] Backend: `DELETE /api/programs/{id}/image` — gated, nastaví image_url=null
- [x] Backend: `GET /api/programs/image/{path:path}` — veřejné servírování, restrikce path musí začínat `budezivo/programs/`
- [x] `ProgramCreate`/`Program` schéma + repo (`create`) propouští `image_url`; public endpoint přidán do PUBLIC_ALLOWED_FIELDS
- [x] `services/storage_service.py` — nová helper `upload_program_image(...)` (storage cesta `budezivo/programs/{inst}/{prog}/{uuid}.{ext}`) + konstanta MAX_PROGRAM_IMAGE_SIZE=5 MB
- [x] Frontend ProgramsPage: nová karta „Fotografie programu" v Detail tabu — drag&drop upload, náhled, tlačítka Vyměnit / Odstranit; karta se zobrazuje jen když `/api/programs/features/check-access` = true
- [x] Frontend BookingPage (veřejná): pokud `program.image_url` existuje, zobrazuje se hero obrázek nad kartou programu (`program-image-{id}`)
- [x] Frontend SuperadminPage: `FEATURE_FLAG_LABELS.program_photos` registrován (ikona Image, label „Fotografie programů") — whitelist UI v záložce Feature flagy
- [x] Audit log zaznamenává `upload_image` / `delete_image` na entity_type=program
- [x] Testováno: 16/16 backend pytest + 100% frontend (iteration_55.json)


### Fáze 50 — Auto-přiřazení hlavního lektora + režim Hlavní / Náslech (22.4.2026)
- [x] DB: `users.lecturer_mode` (default 'main'), `reservations.assignment_source`, `reservations.assignment_reason`
- [x] Backfill: 40 rezervací → `default_program`, 116 → `unassigned`
- [x] Nová služba `services/lecturer_assignment_service.py::pick_main_lecturer()` — pool = program.assigned_lecturer_id + collision_lecturer_ids, filtrováno na aktivní + `lecturer_mode='main'`, hodnoceno podle rozvrhu + AvailabilityBlock + zatížení za 7 dní
- [x] `routes/bookings.py::_resolve_main_lecturer()` napojen do `create_booking` i `create_public_booking`; pokud jsou konfigurovaní lektoři, ale nikdo není k dispozici → 409 s českou zprávou
- [x] Admin assign: `assign-lecturer-admin` odmítne training-mode lektora s 400 („Náslech“)
- [x] Nový endpoint `PATCH /api/team/{id}/lecturer-mode` (admin only)
- [x] BookingsPage: color-coded badge `assignment-source-badge` + `assignment-reason`; dropdown pro přiřazení filtruje pouze main-mode lektory
- [x] TeamPage: inline toggle „Hlavní lektor ↔ Náslech" (testid `lecturer-mode-toggle-{id}`) pro role `lektor`/`edukator`
- [x] Oprava vedlejšího bugu: `BookingBase.age_or_class: Optional[str]` (GET /api/bookings vracelo 500 pro historické null hodnoty)
- [x] Testování: 12/12 backend pytest + frontend badge ověřen screenshotem (iteration_56.json)



### Fáze 51 — Hromadný ZIP export všech generovaných souborů (22.4.2026)
- [x] Nový endpoint `GET /api/exports/download-bundle` (gated: superadmin OR admin/spravce + plan has `data_export`)
- [x] Bezpečnost: lektor/edukátor dostane 403, free plan → 403 s výzvou k upgrade, superadmin OK
- [x] Obsah: `01_skoly_kontakty.csv`, `02_import_template.xlsx`, `03_zpetna_vazba.csv`, `04-06_statistiky_*.csv`, `07_gdpr_export.json`, `08_kalendar_instituce.ics`, `09_kalendar_program_{name}.ics` + `10_archive_report_{name}.json` na program (cap 20), `MANIFEST.json`
- [x] Helper `_bytes_from_call` zvládá `Response`/`StreamingResponse`/bytes/dict — per-file error do manifestu
- [x] Fix: `Content-Disposition` RFC 5987 kvůli českým diakritikám
- [x] Frontend `SettingsPage → GDPR a export dat`: karta „Hromadný export (ZIP)" s loading state a blob download (testid `bulk-export-card`, `bulk-export-button`)
- [x] Ověřeno: 23 souborů × 227 kB pro Gallery PRO, 403 pro lektora, 200 pro superadmina

### Fáze 52 — JSON → PDF migrace exportů (22.4.2026)
- [x] Nové PDF buildery v `services/export_service.py`: `build_archive_report_pdf()` + `build_gdpr_export_pdf()` (DejaVuSans, kv-table styl, max 80 řádků tabulek s oříznutím)
- [x] `GET /api/programs/{id}/archive-report` výchozí výstup je **PDF** (dříve JSON); `?format=json` zachován pro zpětnou kompatibilitu interních nástrojů
- [x] `GET /api/gdpr/export` výchozí výstup je **ZIP** s `gdpr_export.json` + `gdpr_export.pdf` + `README.txt` vysvětlujícím, že autoritativní formát pro GDPR čl. 20 přenositelnost zůstává JSON; `?format=pdf` a `?format=json` zachovány
- [x] Bundle `GET /api/exports/download-bundle`: `07_gdpr_export.{json,pdf}` bok po boku, archive reporty jako `10_archive_report_*.pdf` (žádné JSON archive)
- [x] SettingsPage `handleExportData`: stahuje jako blob ZIP s datem v názvu souboru; popisky i tlačítko přepsány na „Exportovat moje data (ZIP — JSON + PDF)"
- [x] RFC 5987 filename fix pro české diakritiky v Content-Disposition (jinak Response crashuje na latin-1 encoding)
- [x] Testováno: 9/9 backend pytest + FE end-to-end (iteration_57.json)



### Fáze 53 — Multi-part improvement bundle + PDF report button (22.4.2026)
- [x] Task 1: „Stáhnout PDF report" v kebab menu u každé karty programu (testid `pdf-report-{id}`) — blob download
- [x] PART 1: DB `users` + 4 sloupce (preferred_age_groups, supported_program_ids, learning_program_ids jsonb + admin_note text); `TeamMember` schéma + `PATCH /api/team/{id}/lecturer-profile` (self-edit + admin-only admin_note)
- [x] PART 4: `services/collision_classifier.py` — wrapper `classify(msg) → {blocked, code, source, message_cs, details}`; obě entry-points (public + admin); FE čte `detail.message_cs`
- [x] PART 5: `ProgramCollisionTab.js` — karta „Současně s jinými programy", helper texty bez „paralelní"/technických termínů
- [x] Testováno: 14/14 backend pytest + FE E2E (iteration_58.json)

### Fáze 54 — Oprava crash ArchivePage + Samoobslužný profil lektora + Zjednodušení Náslechu (22.4.2026)
- [x] **Fix P0**: `/app/frontend/src/pages/admin/ArchivePage.js` – volání `/api/programs/{id}/archive-report` doplněno o `?format=json` (default se stal PDF po Fázi 52) + null-safe render `reportData && reportData.program`; TypeError při kliku na „Report" u archivovaného programu vyřešen
- [x] **Self-service profil lektora**: Nová stránka `/admin/my-profile` (MyProfilePage.js) dostupná všem rolím:
  - Úprava jména
  - Preferované věkové skupiny (ms_3_6 / zs1_7_12 / zs2_12_16 / ss_15_19 / adults)
  - Programy „mohu vést" (supported_program_ids) a „chci se naučit / náslech" (learning_program_ids) s mutual exclusion
  - Zobrazení admin_note (read-only pro ne-adminy)
  - Save přes `PATCH /api/team/{user_id}/lecturer-profile`
- [x] **Zjednodušení Náslechu** (dle uživatele: odstranění duplicity):
  - ❌ ODSTRANĚNO: celý router `/app/backend/routes/observers.py` (5 endpointů /api/bookings/{id}/naslech*)
  - ❌ ODSTRANĚNO: `PATCH /api/team/{id}/lecturer-mode` endpoint
  - ❌ ODSTRANĚNO: filtr `lecturer_mode == "main"` v `pick_main_lecturer` a `bookings.py`
  - ❌ ODSTRANĚNO: komponenta `NaslechPanel` v BookingsPage.js a tlačítko toggle `lecturer-mode-toggle-*` v TeamPage.js
  - ✅ Náslech je nyní jen „poznámka" v profilu lektora — program v `learning_program_ids` znamená „tento program zatím nevedu" (systém mě u něj automaticky nepřiřadí jako hlavního lektora); po absolvování lektor sám přesune program do `supported_program_ids`
- [x] Sidebar: nová položka „Můj profil" (`nav-my-profile`) viditelná pro všechny role
- [x] Pytest: `test_my_profile_and_naslech_removal.py` — 7/7 PASS
- [x] Testováno: 100% backend + 100% frontend E2E (iteration_59.json)


### Fáze 55 — Landing page redesign sekcí dle mockupů (23.4.2026)
- [x] **Sekce „Znáte tuto realitu?"**: přepracováno ze 6 karet do porovnávacího layoutu *Bez systému* (červené karty) → šipky → *S Budeživo* (modré karty); 5 párů problém/řešení
- [x] **Sekce Benefits (Úleva pro zaměstnance / Přínos pro vedení)**: split layout přes celou šířku — levá strana bílá (employee), pravá strana `#2B3E50` (management); každý benefit má ikonu + název + popisek; zlaté `#C4AB86` akcenty
- [x] **Sekce „Jak to funguje?"**: rozšíření ze 3 na 4 kroky v horizontální timeline s propojovací linkou; modré kruhy `#4A6FA5` s ikonou + zlatý badge čísla
- [x] Nové ikony importovány z lucide-react (ArrowRight, MailCheck, CheckCircle2, CalendarDays, UserPlus, Smile, atd.)
- [x] Odstraněn nepoužívaný `painPoints` array
- [x] Lint: ✅ No issues


### Fáze 56 — Feature flag pro Social Proof sekci (23.4.2026)
- [x] **Skrytí sekce Social Proof** (stats 8+/21+/173+/98% + „Důvěřují nám"): default **VYPNUTO**
- [x] **Nový feature flag** `social_proof` automaticky vytvořen při startup seedu (`main.py startup_event`, idempotentní `INSERT ... ON CONFLICT (key) DO NOTHING`)
- [x] `/api/public/stats` nyní čte `FeatureFlag.enabled` pro klíč `social_proof` a podle něj nastavuje `show_stats` (místo staré podmínky ≥5 institucí)
- [x] **Superadmin UI bez úprav** — flag se automaticky objeví v existující sekci *Feature flags* s přepínačem *Globálně ZAPNUTO / Whitelist režim* (dle přání uživatele — nová sekce nevznikla)
- [x] Testováno curl:
  - flag OFF → `show_stats=False`, sekce skryta (ověřeno v DOM: `document.querySelector('[data-testid=social-proof-section]') === null`)
  - PUT enabled=true → `show_stats=True`, sekce se objeví



### Fáze 57 — B2B Katalog „Programy pro školy" (ETAPA 1 MVP) (25.4.2026)
- [x] **DB schema (idempotent migrace)**: nový sloupec `programs.is_in_catalog` BOOLEAN NOT NULL DEFAULT FALSE — ALTER TABLE IF NOT EXISTS v `main.py startup_event`
- [x] **SQLAlchemy model**: `Program.is_in_catalog` + Pydantic `ProgramBase.is_in_catalog: bool = False`
- [x] **Backend route** `/app/backend/routes/catalog.py`:
  - `GET /api/public/catalog` — list s filtry `?city=&age=ms|zs1|zs2|ss&category=&q=&sort=popular|newest`, paginace, facets (cities/categories/age_groups)
  - `GET /api/public/catalog/{program_id}` — detail s description_full, institution.address
  - Hard filtr: `is_in_catalog=TRUE AND deleted_at IS NULL AND is_published=TRUE AND status='active' AND i.deleted_at IS NULL`
  - Reservation count z `reservations` (counted statuses: confirmed/pending_approval/done/approved)
  - **CRITICAL FIX iter60**: `(p.target_groups)::jsonb ?| :age_codes` — sloupec je JSON, ne JSONB; cast nutný pro `?|` operátor
- [x] **Admin toggle**: nový Switch `program-is-in-catalog` v `ProgramsPage.js` editoru programu (vedle is_published) — popisek „Zobrazit v katalogu „Programy pro školy"
- [x] **Veřejné stránky** (oba s data-testid):
  - `/programy-pro-skoly` (`CatalogPage.js`) — hero, search bar, 4 filtry (city/age/category/sort), URL-driven přes `useSearchParams`, aktivní filter chips, grid 3-col karet, empty state
  - `/programy-pro-skoly/:id` (`CatalogDetailPage.js`) — cover, název, institution, meta (city/duration/capacity), categories, popis, sticky sidebar s CTA „Vybrat termín" (→ `/booking/{inst}?program={id}`) a „Nezávazně poptat" (otevře dialog → POST `/api/public/contact` s prefixem source)
- [x] **NENÍ linkováno z hlavní stránky** (per user request) — Header/HomePage/Footer žádný odkaz, přístup pouze přes URL
- [x] **Testing iter60**: backend 12/12 PASS po fixu age operátoru, frontend 100% PASS (list + filtry + detail + inquiry + admin Switch)


### Fáze 58 — Katalog ETAPA 2: Inspirace & Discovery + SEO slugy (25.4.2026)
- [x] **🔥 Sekce „Nejoblíbenější"** + **🆕 Sekce „Novinky"** nad hlavním gridem, viditelné jen když nejsou aktivní filtry/slug; kompaktní 4-sloupcové karty (`discover-card-{id}`) využívají existující endpoint s `?sort=popular&limit=4` / `?sort=newest&limit=4`
- [x] **SEO URL slugy** `/programy-pro-skoly/{slug}` — slug client-side resolved:
  - `ms` / `zs1` / `zs2` / `ss` → age filter (např. „Programy pro mateřské školy")
  - `praha` / `brno` / `…` → city filter (slug porovnán proti facets.cities)
  - `vytvarna-vychova` / `hudebni` / … → category filter
  - Slug-aware H1: „Programy v lokalitě Brno", „Programy pro 1. stupeň ZŠ" atd.
  - Změna filtru opouští slug a přejde na `?city=…` query (zachování URL pro sdílení)
- [x] **Routing reorganizace**: detail přesunut na `/programy-pro-skoly/p/{id}` aby nedošlo ke kolizi se slug routou; ProgramCard a CompactProgramCard updated
- [x] **Slugify helper** `/app/frontend/src/lib/slugify.js` (NFD strip + lowercase + dash) + `AGE_SLUGS`, `AGE_SLUG_LABELS`, `UUID_RE`
- [x] **Testováno**: curl + screenshot — `?sort=popular&limit=4` a `?sort=newest&limit=4` vrací správně (4 + 4 položky, oba viditelné v UI), `/brno` filtruje, `/ms` filtruje, `/p/{id}` otevírá detail
- [x] Lint: ✅ No issues


### Fáze 59 — Landing redesign sekcí „Vše na jednom místě" + „Vyzkoušejte si to" (25.4.2026)
- [x] **„Vše na jednom místě"** — kompletně přepracováno:
  - Pozadí změněno na tmavě modré `#2B3E50` (per styleguide) s jemným grid backdrop
  - **DashboardPreview komponenta** — stylizovaná ilustrace admin panelu (sidebar, header, 4 statkarty, kalendář s žluto/zlatými booking bloky — jako mockup); pouze visual, žádná data
  - 6 feature pills níže (Automatická potvrzení, Bez registrace pro školy, Statistiky pro vedení, Správa kapacit, Online platby, Týmové role) v outline-glass stylu
  - Odstraněn starý 6-card grid (`features` array smazán)
- [x] **„Vyzkoušejte si to"** přepracováno na **„Nastavení za 15 minut."** dark CTA sekci:
  - Pozadí `#2B3E50` se zlatým radial accent
  - Eyebrow „Připraveni začít?"
  - **Vynechány věty:** „První měsíc zdarma." a „Bez smlouvy, bez závazků." (per user)
  - 2 CTA: „Zaregistrovat instituci" (zlaté → /register) + „Domluvit online ukázku" (outline → #contact)
  - Divider s ikonou oka „Podívejte se, jak to uvidí váš zákazník"
  - **Glass karta** „POHLED VAŠEHO ZÁKAZNÍKA / Jak jednoduché to bude pro učitele?" se 3 checks + zlatým „Spustit ukázku rezervace" (target="_blank") + „Otevře se v novém okně · Pouze demo data"
- [x] Lint: ✅ + smoke screenshoty potvrdily render obou sekcí (4 cta-tlačítka, 1 dashboard-preview, 6 feature-pills, 1 try-booking-demo)


### Fáze 60 — Reorder sekcí na hlavní stránce + smazání CTA (25.4.2026)
- [x] **Nové pořadí sekcí** (po Hero):
  1. Znáte tuto realitu?
  2. Jak to funguje? (přesunuto vpřed)
  3. Vše na jednom místě.
  4. Úleva pro zaměstnance / Přínos pro vedení
  5. Nastavení za 15 minut.
  6. Tarify
  7. FAQ
- [x] **Smazána sekce** „Dopřejte svému týmu více času na skutečnou práci." (modré CTA před FAQ) — duplicitní s „Nastavení za 15 minut."
- [x] Lint: ✅ + smoke screenshot ověřil nové pořadí v DOM


### Fáze 61 — Katalog ETAPA 3: Prefill formuláře z e-mailu (26.4.2026)
- [x] **Backend `GET /api/public/prefill?email=…`** — privacy-first endpoint:
  - Vrátí `{found: false}` (NIKDY 404) pro neznámé/neplatné e-maily — ochrana proti enumeraci
  - Pro existující e-mail vrátí pouze 8 safe pole: `school_name`, `contact_name`, `contact_phone`, `group_type`, `age_or_class`, `num_students`, `num_teachers`, `special_requirements`
  - **NIKDY** nevrací reservation_id, program_id, institution_id, datum ani časové bloky
  - Case-insensitive lookup (LOWER(contact_email))
  - **Defense-in-depth IP rate limit** 20/min/IP (in-process, X-Forwarded-For aware) — testing agent identifikoval že existující `Limiter(key_func=...)` pattern v ostatních route souborech ne-enforcuje (slowapi vyžaduje SlowAPIMiddleware), proto manuální token-bucket přímo v endpointu — ověřeno curl: req 21+ → 429
- [x] **Frontend (BookingPage.js krok 4)**:
  - Hint pod e-mail inputem: „Pokud už jste u nás jednou rezervovali, údaje vám předvyplníme." (`data-testid=booking-prefill-hint`)
  - `onBlur` na e-mail → `tryPrefillFromEmail()` → vyplní jen prázdná pole (only-fill-empty politika, žádné přepisování uživatelského vstupu)
  - Toast „Vyplnili jsme za vás údaje z minulé rezervace." s tlačítkem „Vrátit zpět" (snapshot uložen v `lastSnapshotRef`, undo restoruje předchozí stav)
  - Dedupe: opakovaný blur stejného e-mailu nezavolá API (`prefilledFromEmail` state)
- [x] **Pytest** `/app/backend/tests/test_public_prefill.py` — 4/4 PASSED (unknown, invalid, safe-subset, case-insensitive)
- [x] **Testing agent iter61**: backend 4/4 + frontend 7/7 PASSED — verified hint visibility, prefill on blur, toast undo, dedupe, only-fill-empty, unknown-email no-toast


### Fáze 62 — Refaktor menu + sloučení Dostupnost+Můj profil → Lektorský profil (26.4.2026)
- ❗ **Striktně UI-only**: nezměněn žádný backend endpoint, payload, feature flag, role ani DB
- [x] **Sidebar přebudován** do 3 zón:
  - Daily flat: Přehled, Programy, Rezervace, Akce *(rename z Události, feature flag `events_basic` zachován)*, Propagace *(rename z Mailingy, feature flag `mailing` zachován)*
  - Collapsible „Správa": Školy, Zpětná vazba (default open if active route uvnitř)
  - Lower flat: **Lektorský profil**, Statistiky, Nastavení (+ Superadmin pro platform owner)
  - **Odstraněno ze sidebaru** (kód neztracen, pouze nezobrazeno): Dostupnost, Můj profil, Tým
- [x] **Renames** UI only: Události → **Akce**, Mailingy → **Propagace** (URL i feature flagy nezměněny)
- [x] **Nová stránka** `/admin/lecturer-profile` (`LecturerProfilePage.js`) — tenká UI kompozice; renderuje `<UnifiedAvailabilityPage />` + `<MyProfilePage />` jako celé sub-trees, čímž 100% přebírá jejich logiku (žádný rewrite, žádná duplicita)
- [x] **Zpětná kompatibilita redirecty**:
  - `/admin/availability` → `<Navigate to="/admin/lecturer-profile" replace />`
  - `/admin/my-profile`   → `<Navigate to="/admin/lecturer-profile" replace />`
  - Tým zůstává na `/admin/team`, přístupný přes Nastavení → „Uživatelé a role"
- [x] **Settings reorganizace** UI only — přidán `group` field na každou položku v `SETTINGS_MENU` + nový `SETTINGS_GROUPS` array; render seskupený s nadpisy:
  - Obecné (Instituce, Notifikace, Jazyk a místo)
  - Uživatelé a přístup (Uživatelé a role)
  - Platby a PRO (PRO funkce, Platební nastavení)
  - Data a legislativa (GDPR, VOP)
  - Systém (Audit log)
- [x] **Mobile bottom nav**: filtruje group items, používá jen flat
- [x] Lint ✅, smoke screenshot ověřil sidebar+settings struktura, redirecty fungují (curl-style probe)


### Fáze 63 — Bug fix: dvojitý AdminLayout v Lektorském profilu (26.4.2026)
- 🐛 **Iter62 testing agent identifikoval kritický bug**: `/admin/lecturer-profile` renderoval 2× AdminLayout (2 sidebary, 2 mobile nav), protože vnořené `MyProfilePage` a `UnifiedAvailabilityPage` měly vlastní wrapper
- [x] **Fix**: přidán `embedded` prop do 4 komponent — `MyProfilePage`, `UnifiedAvailabilityPage`, `LecturerAvailabilityPage`, `ProgramAvailabilityView`. Když `embedded=true`, vrací pouze content; jinak fallback do `<AdminLayout>` (zpětná kompatibilita s budoucím standalone použitím)
- [x] **LecturerProfilePage** nyní vlastní jediný `<AdminLayout>` a předává `embedded` propy dolů
- [x] **Babel parsing fix**: refaktor IIFE pattern na lineární `const content = ...; return embedded ? content : <AdminLayout>{content}</AdminLayout>` — babel-plugin-visual-edits od Emergentu nezvládá IIFE uvnitř JSX
- [x] LecturerAvailabilityPage `<>...</>` fragment kolem hlavního div + Dialog (sibling elementy)
- [x] **Iter63 re-test 100% PASS**:
  - aside=1, mobile_nav=1 ✅
  - Toggle Programová/Osobní zachovává jediný layout
  - 12/12 sekcí z user prompt-u zelené
  - Backend pytest 7/7 PASS (`test_my_profile_and_naslech_removal.py`)
  - Žádné console errors, žádné 4xx/5xx

### Fáze 64 — UI/UX vylepšení landing page + Mobile nav + Today widget (27.4.2026)
- [x] **Hero**: nová muzeální fotografie (žena u laptopu v galerii) jako pozadí; gradient `from-[#2B3E50] from-30% via-50% to-transparent` (na mobilu silnější + vertikální fade dolů pro čitelnost)
- [x] **Sekce „Jak to funguje?"** převedena z LIGHT (`#F1F4FA`) na DARK navy (`#243446`) s bílým textem, `ring-4 ring-[#243446]` kolem zlatých step badges, jemný radial backdrop
- [x] **Sekce „Vše na jednom místě."** převedena z DARK (`#2B3E50`) na LIGHT (`#EEF2F9`) s eyebrow „POHLED ADMINISTRÁTORA", grid backdrop v brand modré, feature pills s bílým pozadím + `border-[#D9E1F0]`
- [x] **Mobile responsivita DashboardPreview**: `grid-cols-1 md:grid-cols-[200px_1fr]` (sidebar `hidden md:block` skrytý na mobilu), kalendář obalen `overflow-x-auto` + `min-w-[520px]` pro horizontální scroll
- [x] **Alternace bg sekcí**: Hero(DARK) → Pain Points(LIGHT) → How It Works(DARK) → Features(LIGHT) → Benefits(SPLIT) → CTA(DARK) → Pricing(LIGHT) → FAQ(WHITE)
- [x] **Brand barvy zachovány**: `#4A6FA5` (světle modrá) v ikonách, eyebrows a feature pills; `#C4AB86` (zlatobéžová) v step badges, ikonách a CTA
- [x] **„Rezervace dnes" widget** (`DashboardPage.js`): nová karta nad statistikami pro role `admin`/`spravce`/`lektor`/`edukator`/`pokladni`
  - Pro `lektor`/`edukator`: filtrováno na `assigned_lecturer_id == user.id`, label „Moje rezervace dnes", empty „Dnes vás žádný program nečeká..."
  - Pro `admin`/`spravce`/`pokladni`: zobrazeny všechny dnešní rezervace, label „Rezervace dnes"
  - Klik na rezervaci otevře existující ReservationDetailModal
  - Testidy: `today-bookings-widget`, `today-bookings-count`, `today-bookings-empty`, `today-booking-{id}`
- [x] **Mobile bottom nav**: 5. slot rezervován pro „Více" (testid `mobile-nav-more`) když existuje overflow (>4 flat items); odkazuje na `/admin/settings`
- [x] **SettingsPage**: nová mobile-only sekce „Rychlý přístup" (testid `settings-mobile-quick-access`) — 3-sloupcový grid 9 dlaždic dle role (Přehled, Programy, Rezervace, Akce, Propagace, Školy, Zpětná vazba, Lektorský profil, Statistiky, Superadmin); skryto na desktop přes `md:hidden`
- [x] **Testing agent iter64**: 100% DOM/visual acceptance PASS; pouze minor preview-env překryv s Emergent badge přes 5. nav slot — vyřešeno bumpem na `z-[60]`

### Fáze 65 — Compliance audit pro platební bránu (Comgate) (27.4.2026)
- 🔍 **Audit identifikoval problémy**: chybějící samostatná stránka pro reklamace/storno, chybějící samostatná stránka pro platební podmínky, footer s typem `bubezivo.cz` + bez identifikace provozovatele a právních odkazů, ContactPage s fake daty (Příkladová 123, +420 123 456 789), booking flow bez explicitního shrnutí objednávky a s odkazem jen na `/terms`
- [x] **NEW page** `/reklamace` (`ReklamacePage.js`) — Reklamační a stornovací podmínky pro koncového zákazníka:
  - Storno 48h předem zdarma, 14 dnů na vrácení platby, zrušení ze strany pořadatele s plnou náhradou, mimosoudní řešení sporů (ČOI + EU ODR platforma)
  - Provozovatel: Daniela Kytlicová, IČO 07407971, Mlýnská 538
  - Testidy: `reklamace-page`, `reklamace-provider`, `reklamace-cancel`, `reklamace-refund`, `reklamace-organizer-cancel`, `reklamace-complaint`, `reklamace-adr`, `reklamace-contact`
- [x] **NEW page** `/platebni-podminky` (`PaymentTermsPage.js`) — Platební a dodací podmínky:
  - 6 sekcí: provozovatel, předmět plnění, způsoby platby (na místě / převod / online brána), bezpečnost (Comgate IČO 27924505, PCI-DSS), cena/měna (CZK), doklad o platbě, link na reklamace
  - Testidy: `payment-terms-page`, `payment-provider`, `payment-subject`, `payment-methods`, `payment-security`, `payment-price`, `payment-receipt`, `payment-cancel-link`
- [x] **Footer rewrite** (`Footer.js`):
  - Opravený typo `bubezivo.cz` → `info@budezivo.cz`
  - Nová sekce „Provozovatel" s identifikačními údaji (Daniela Kytlicová, IČO 07407971, Mlýnská 538, email) — testid `footer-provider-info`
  - 4 právní odkazy: VOP, GDPR, Reklamace, Platební podmínky — testidy `footer-link-{vop,gdpr,reklamace,payment}`
  - Nahrazen mailto Kontakt v patičce React Routerem `<Link to="/kontakt">`
- [x] **ContactPage cleanup** (`ContactPage.js`): odstraněn fake telefon `+420 123 456 789`, fake adresa `Příkladová 123, Praha 1` nahrazena reálným provozovatelem (Daniela Kytlicová, IČO 07407971, Mlýnská 538); přejmenováno „Adresa" → „Provozovatel"
- [x] **BookingPage step 4 — Shrnutí objednávky**: nová karta `booking-summary` na začátku kroku 4 s přehledem (program, datum, čas, cena z `pricing_info`, poskytovatel = instituce); textové vysvětlení že smluvní vztah vzniká mezi zákazníkem a institucí, Budeživo je technický zprostředkovatel
- [x] **BookingPage checkboxes** doplněny o linky:
  - GDPR checkbox: link `/gdpr` (testid `booking-gdpr-link`)
  - Terms checkbox: 3 odkazy `/obchodni-podminky` + `/reklamace` + `/platebni-podminky` (testidy `booking-terms-link-{vop,reklamace,payment}`)
- [x] **App.js**: zaregistrovány routy `/reklamace` a `/platebni-podminky`
- [x] **Testing agent iter65**: 96% PASS (23/24 live assertions). Kód-level verifikace booking step-4 testidů úspěšná; live walkthrough nelze dokončit kvůli omezení seed dat Test Muzea (žádné dostupné termíny v 8 následujících měsících)

### Fáze 66 — Demo produkt B2C: Příměstský tábor + Compliance flow v Events (27.4.2026)
- 🎯 **Účel**: vytvořit realistický B2C scénář (rodič kupuje příměstský tábor) pro demonstraci platebního flow Comgate; doplnit chybějící compliance prvky v Events flow (souhrn + checkbox souhlasu)
- [x] **Seed skript** `/app/backend/scripts/seed_demo_camp.py` (idempotentní):
  - Vytvoří/aktualizuje Event „Příměstský tábor – Léto 2026" pod Test Muzeum (institution `669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5`)
  - Type `camp`, kapacita 20, cena 2500 CZK, popis 5denního programu pro děti 7-12, výtvarné dílny, prohlídky, závěrečná vernisáž
  - 8 form_fields: jméno dítěte, věk, škola, jméno rodiče, e-mail rodiče, telefon, alergie, souhlas s focením
  - Termín 1.–5. července 2026, 8:00–16:30
  - Whitelistuje `events_module` flag pro Test Muzeum
  - Vytvoří payment_settings (Comgate MOCK + QR, account 295033917/0300, IBAN CZ60..., account_name „Test Muzeum")
- [x] **PublicEventsPage rozšíření** (`PublicEventsPage.js`):
  - Step `form` doplněn o povinnou kartu „Shrnutí objednávky" (testid `event-order-summary`) — produkt, termín, cena, poskytovatel + textové vysvětlení smluvního vztahu
  - Testidy: `summary-event-name`, `summary-event-date`, `summary-event-price`, `summary-event-provider`
  - 2 nové povinné checkboxy: GDPR (`event-gdpr-consent` + link `event-gdpr-link` → /gdpr) a Terms (`event-terms-consent` + 3 linky `event-terms-link-{vop,reklamace,payment}`)
  - Submit button disabled, dokud nejsou oba consenty zaškrtnuté; text se mění na „Objednat a přejít k platbě" při ceně > 0
  - `handleSubmit` validuje souhlasy před POST + zobrazí toast error
- [x] **End-to-end smoke test (manual screenshot)**: list → detail (1 termín auto-selected) → form → summary card s "Cena: 2500 CZK" + "Poskytovatel: Pořadatel akce" + checkboxy fungují (disabled bez consent, enabled s consent, btn text "Objednat a přejít k platbě")
- [x] **Stale build issue**: webpack hot-reload nezachytil změny v PublicEventsPage; `sudo supervisorctl restart frontend` vyřešil. (Deja-vu z iter65 — připomínka pro budoucí refaktor.)

### Fáze 67 — Comgate brand requirements (loga + kontakty + platební metody) (27.4.2026)
- 🎯 **Compliance požadavek od Comgate**: na webu musí být uveden poskytovatel platební brány s odkazem, vysvětlení platebních metod, kontaktní údaje Comgate, a v patičce loga Comgate / Visa / Mastercard
- [x] **PaymentTermsPage sekce 4 přepracována** na „Poskytovatel platební brány a bezpečnost online plateb":
  - Hlavní odkaz na `https://www.comgate.eu/cs/platebni-brana` (testid `comgate-gateway-link`)
  - Detailní vysvětlení 2 platebních metod:
    - **Platba kartou (Visa, Mastercard)**: 3-D Secure flow + odkaz na `https://help.comgate.cz/v1/docs/cs/platby-kartou` (testid `comgate-card-help-link`)
    - **Platební tlačítka bank** (online převod): odkaz na `https://help.comgate.cz/docs/bankovni-prevody` (testid `comgate-transfer-help-link`)
  - **Kontaktní karta Comgate** (testid `comgate-contact-card`): Comgate, a.s., Gočárova třída 1754/48b, 500 02 Hradec Králové, podpora@comgate.cz, +420 228 224 267, s upozorněním kam směřovat reklamace plateb
- [x] **NEW komponenta `PaymentBrandsBar.js`** (`/app/frontend/src/components/layout/`):
  - Inline SVG loga: Comgate (gradient C + wordmark), Visa (italic 1A1F71), Mastercard (klasický red+orange+yellow překryv)
  - Comgate logo je klikatelné → odkazuje na oficiální brand URL
  - Testidy: `payment-brands-bar`, `brand-comgate`, `brand-visa`, `brand-mastercard`
- [x] **Footer rozšířen**: pod copyright sekci přidán PaymentBrandsBar s eyebrow „AKCEPTUJEME ONLINE PLATBY PŘES" (left-aligned na desktop, centered na mobil); copyright v pravé části flexu
- [x] **Smoke test**: všech 7 testidů + 4 odkazy nalezeny v DOM, loga renderována, Comgate kontakt obsahuje všechny povinné údaje (e-mail, telefon, Gočárova)

### Fáze 68 — B2B Catalog Etapa 4: Učitelské účty (B2C) + Oblíbené + Historie + Prefill (27.4.2026)
- 🎯 **Cíl**: registrace/přihlášení externích učitelů (mimo institucionální admin systém), uložené oblíbené programy, historie rezervací, autoprefill rezervačního formuláře pro přihlášené uživatele
- 👤 **Volby uživatele**: 1a) vlastní JWT email/password (architektonicky připraveno na Google později), 2) MVP + prefill (ne notifikace), 3a) separátní `teacher_accounts` tabulka

#### Backend
- [x] **NEW migration `003_teacher_accounts.sql`** (idempotentní):
  - `teacher_accounts` (id, email UNIQUE, password_hash, name, school_name, phone, auth_provider DEFAULT 'password', google_sub, is_active, last_login_at, created_at, updated_at, deleted_at)
  - `teacher_favorites` (teacher_id FK CASCADE, program_id FK CASCADE, institution_id FK CASCADE, UNIQUE(teacher_id, program_id))
  - `teacher_login_attempts` (identifier UNIQUE, failed_count, last_failed_at, locked_until) — pro brute-force ochranu
- [x] **NEW modely** `TeacherAccount`, `TeacherFavorite`, `TeacherLoginAttempt` v `database/models.py`
- [x] **NEW router `routes/teacher.py`**:
  - **Auth**: `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `PATCH /me`
  - **Favorites**: `GET /favorites` (s embedded program data), `POST /favorites` (idempotent), `DELETE /favorites/{program_id}`
  - **Bookings**: `GET /bookings` (filtruje rezervace podle `contact_email == teacher.email`)
  - **JWT**: 14denní TTL, payload obsahuje `account_type='teacher'`, cookie `teacher_token` (httpOnly secure samesite=lax), Bearer fallback
  - **Brute-force lockout**: dvojitý klíč `email:{email}` + `ip:{ip}` (z X-Forwarded-For), 5 pokusů → 15 min lockout
  - Heslo bcrypt-hashed, bezpečné error messages bez user enumeration
- [x] **🐛 SECURITY FIX `core/security.get_current_user`**: nyní explicitně odmítá tokeny s `account_type != 'admin'` a tokeny bez `user_id` → 401 místo 500 KeyError. Předchází leakage informací při náhodném použití teacher tokenu na admin endpoint
- [x] **Lockout fix `routes/teacher.py`**: `_client_ip()` helper čte `X-Forwarded-For` first hop místo `request.client.host` (které za Kubernetes ingress rotuje)

#### Frontend
- [x] **NEW context `TeacherAuthContext.js`** (oddělený od institucionálního AuthContext): cookie + localStorage `bz_teacher_token` Bearer fallback (pro cross-subdomain ingress preview), automatický refresh `/me` při mountu, format API errors helper
- [x] **NEW stránky** v `pages/teacher/`:
  - `/ucitel/registrace` — TeacherRegisterPage (jméno, email, heslo, škola, telefon + checkbox VOP/GDPR)
  - `/ucitel/prihlaseni` — TeacherLoginPage
  - `/ucitel/ucet` — TeacherAccountPage s 3 tab záložkami: **Oblíbené** / **Historie** / **Profil**
- [x] **NEW komponenta `FavoriteButton.js`** s 2 variantami:
  - `variant='icon'` — kruhové srdíčko v top-right rohu catalog karty
  - `variant='pill'` — pill na catalog detail page „Uložit" / „V oblíbených"
  - Lazy fetch oblíbených při mountu (jen pokud je teacher přihlášen)
  - Při kliknutí bez přihlášení → toast s tlačítkem „Přihlásit"
- [x] **CatalogPage** (`programy-pro-skoly`): srdíčko v top-right rohu každé karty
- [x] **CatalogDetailPage** (`programy-pro-skoly/p/{slug}`): pill u nadpisu programu
- [x] **BookingPage prefill**: `useTeacherAuth` integration — pokud je teacher přihlášen, jeden-shot autofill `contact_name/email/phone/school_name` z teacher profilu (jen prázdné pole, neutrhne user input), s toast „Údaje byly předvyplněny z vašeho účtu"
- [x] **App.js**: `TeacherAuthProvider` wrap (oddělený od `AuthProvider`), 3 nové public routy

#### Test
- [x] **Iter66 testing agent**: 13/15 backend pytest PASS + 100% frontend testable flows. 2 HIGH backend bugy nalezeny:
  1. ❌→✅ Admin endpoint vrátil 500 KeyError při teacher tokenu — opraveno (401)
  2. ❌→✅ Brute-force lockout nikdy nesepnul přes ingress — opraveno (X-Forwarded-For + email klíč)
- [x] **Curl re-verifikace po opravách**:
  - Admin login OK ✅, /me OK ✅
  - Teacher login OK ✅
  - **Teacher token na admin /me → HTTP 401** „Tento token nepatří administrátorovi platformy." ✅
  - **5 wrong attempts → 401, 6. attempt → 429**, dokonce i správné heslo během lockoutu vrací 429 ✅
- [x] Carry-over: BookingPage step-4 live walkthrough stále blokován seed-daty Test Muzea (žádné dostupné termíny) — nesouvisí s Etapou 4




