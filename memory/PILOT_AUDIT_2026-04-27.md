# 🔍 PILOT-READINESS AUDIT · Budeživo.cz
**Datum:** 27. 4. 2026 · **Auditováno během jedné session**

---

## 1️⃣ FUNKČNÍ TESTOVÁNÍ (END-TO-END)

### A) Veřejný uživatel (rodič/škola)
| # | Krok | Stav |
|---|------|------|
| 1 | Výběr programu / akce | ✅ `/booking/{id}`, `/events/{id}`, `/programy-pro-skoly` |
| 2 | Vyplnění objednávky | ✅ 4-krokový formulář, validace |
| 3 | Souhlasy (GDPR, VOP) | ✅ 2 checkboxy s linky na 4 dokumenty, submit disabled bez consent |
| 4 | Shrnutí objednávky | ✅ „Shrnutí rezervace" karta před odesláním (booking i events) |
| 5 | Přechod na platební bránu | ⚠️ **Comgate běží v MOCK módu** — na produkci je třeba doplnit reálné API klíče do `institution_payment_settings.gateway_api_key` + `gateway_secret` |
| 6 | Návrat do systému | ✅ Mock `/payment/mock` funguje, návratová URL testována |

### B) Administrátor / instituce
| # | Krok | Stav |
|---|------|------|
| 1 | Přihlášení/odhlášení | ✅ `demo@budezivo.cz` login OK |
| 2 | Správa programů | ✅ CRUD testováno v předchozích iteracích |
| 3 | Správa termínů | ✅ LecturerAvailability systém funkční |
| 4 | Správa rezervací | ✅ `/api/bookings` 200 |
| 5 | Přehled objednávek | ✅ Widget „Rezervace dnes" + Statistiky |
| 6 | Nastavení | ✅ SettingsPage s payment/profile/branding/team |

### C) Platební proces
- ✅ Ceny se propagují z `program.pricing_info` / `event.price`
- ⚠️ **Comgate MOCK** — pro pilot se zapnutou reálnou platbou je nutné aktualizovat `institution_payment_settings` (viz doporučení 🟠)
- ✅ Návratová URL `/events/{inst}/paid?application_id=...` funguje (handler v `routes/events.py`)
- ✅ Status aktualizace: `pending → confirmed` po úspěšné platbě

---

## 2️⃣ LOGIKA A VAZBY
- ✅ **Kolize termínů** — `services/collision_service.py` s `assigned_lecturer_id`, `collision_resources`, `LecturerAvailability`
- ✅ **Kapacita rezervací** — kontrolováno proti `max_capacity` a `max_concurrent_per_block`
- ✅ **Promítání admin→frontend** — všechny endpointy vrací čerstvá data bez cache
- ✅ **Neodpojené části** — health check 10/10 veřejných stránek + klíčové API endpointy OK

---

## 3️⃣ UX/UI

| Oblast | Stav |
|---|---|
| Srozumitelnost formulářů | ✅ CZ jazyk, labely, placeholder, required označení |
| Chybové hlášky | ✅ CZ toast s konkrétní akcí (např. „Přihlásit" v toast nepřihlášeného uživatele při ❤️) |
| Navigace | ✅ Admin sidebar s collapsible skupinami, mobile bottom nav s „Více" |
| Konzistence designu | ✅ Brand barvy #4A6FA5 + #C4AB86 napříč, jednotné Cardy, Tailwind design tokens |
| Mobilní zobrazení | ✅ Responsive grid, viewport 390px testováno, bottom nav z-index bumped |

---

## 4️⃣ DATOVÁ ČISTOTA ✅

Provedeno přes `/app/backend/scripts/pilot_cleanup.py` (idempotentní).

### Smazáno
- **15 testových institucí** (TEST_DeleteInst, TEST_FreePlan_*, Duplicate Test, Testovací Muzeum Supabase 2× — kaskádově padly i programy, rezervace, uživatelé)
- **33 testových škol** (TEST_*, ZŠ Testovací, Load Test School #N)
- **3 testoví uživatelé** (soft delete: `test@budezivo.cz`, `test-kolega@example.com`, `invited_*@budezivo.cz`)
- **1 duplicitní event** („Příměstský tábor Léto 2026" bez pomlčky)
- **Vyčištěny** `teacher_login_attempts` (brute-force counters)

### Zachováno (důležitá pilotní data)
- **Test Muzeum** (ID `669e71b2…`) — hlavní demo instituce s 7 programy, 55 rezervacemi, 3 akcemi + připravený „Příměstský tábor – Léto 2026" za 2 500 Kč (nyní plně bookable: 4 time_blocks, Po-Pá, 1–180 dní)
- **Galerie U Zlatého kohouta** (B2B katalog showcase)
- Všechny reálné instituce (GASK, Botanická zahrada, Památník Lidice, 2× Oblastní galerie Lázně)
- **118 rezervací** na reálných institucích

### Finální stavy v DB
| Entita | Počet |
|---|---|
| institutions | 8 |
| users (aktivní) | 12 |
| programs (aktivní) | 24 |
| reservations | 118 |
| schools | 22 |
| events | 3 |

---

## 5️⃣ BEZPEČNOST A FORMÁLNÍ KONTROLA ✅

- ✅ **GDPR stránka** `/gdpr` s plnou identifikací zpracovatele
- ✅ **Obchodní podmínky** `/obchodni-podminky` (16 sekcí) + `/terms` (podmínky používání)
- ✅ **Reklamace** `/reklamace` (storno 48h, refund 14 dnů, ČOI ADR)
- ✅ **Platební podmínky** `/platebni-podminky` s Comgate kontakty (Gočárova 1754/48b, podpora@comgate.cz, +420 228 224 267)
- ✅ **Footer** s provozovatelem + 4 právními odkazy + Comgate/Visa/Mastercard loga
- ✅ **Formulářová validace** na vstupech (email regex, UUID, min-length passwordu, required checkboxes)
- ✅ **Brute-force ochrana** — teacher login (5 pokusů → 15 min lockout, X-Forwarded-For IP + email klíč)
- ✅ **JWT separation** — admin a teacher tokeny jsou oddělené (`account_type='teacher'`), admin endpoint odmítne teacher token s 401
- ✅ **Žádná citlivá data** veřejně dostupná (public API endpointy prošly audit — vrací pouze nezbytná veřejná pole)

---

## 6️⃣ VÝKON A TECHNICKÝ STAV

- ✅ **Rychlost načítání** — HomePage ~1.5s (hero photo), Catalog ~2s
- ✅ **Konzole** — žádné nové JS errors po restartu
- ✅ **404** — všechny klíčové URL 200, pouze audit-only URL (neexistující endpointy jako `/api/health`) vrací 404 (očekávané)
- ✅ **500 fix** — `GET /api/programs/{program_id}` s non-UUID vstupem dříve vracel 500 → opraveno na 404

---

## 7️⃣ ANALÝZA SLABÝCH MÍST

### 🔴 Kritické problémy (nutné před spuštěním pilotu)
**ŽÁDNÉ.** Všechny P0 compliance + funkční body byly vyřešeny v iteracích 65–70.

### 🟠 Doporučené úpravy (vysoká priorita, před ostrým provozem)
1. **Comgate produkční klíče**
   - *Problém:* Gateway je v MOCK režimu (prázdné `gateway_api_key` / `gateway_secret`)
   - *Proč:* Bez produkčních klíčů nelze přijímat reálné platby
   - *Řešení:* Po schválení Comgate doplnit do `institution_payment_settings` pro každou instituci účastnící se pilotu (Superadmin → Nastavení plateb)
2. **Fakturoid webhook**
   - *Problém:* Automatická aktivace tarifu po platbě běží v režimu „architektura připravena"
   - *Proč:* Při spuštění placených tarifů by se instituce musely aktivovat ručně
   - *Řešení:* Implementovat webhook handler (endpoint existuje, chybí navázat na Fakturoid API klíč)
3. **Smazání nepoužívaných test účtů** (optional)
   - Soft-deleted 3 test users jsou pořád v DB (zachovány kvůli FK constraintům na audit logy). Při velkém objemu auditních dat lze později pročistit `program_email_templates.updated_by` atd. a hard-delete.

### 🟡 Vylepšení (lze řešit po pilotu)
1. **i18n CZ/EN přepínač** — jazykové tlačítko v Headeru (placeholder existuje)
2. **Demo data refresher** — APScheduler úloha, která jednou denně obnoví `end_date` na Test Muzeum +30 dní (demo nikdy nezestárne)
3. **Badge „🔒 Bezpečně přes Comgate"** na placených akcích — zvyšuje konverzi
4. **i18n CZ/EN** pro public stránky + katalog
5. **Auto-renewal scheduler** pro subscriptions
6. **Celery queue** pro advanced mailings (open/click statistiky, plánování)
7. **Mapa — GPS na instituce** (zatím city-level piny; pro Etapu 6 Nominatim geocoding)
8. **Google OAuth pro učitele** (architektura připravena: `auth_provider`, `google_sub` sloupce)
9. **Personalizace na TeacherAccountPage** — „Doporučujeme pro vás" na základě oblíbených

---

## 8️⃣ FINÁLNÍ SHRNUTÍ

### 🟢 Připraveno na pilot: **ANO, S VÝHRADOU**
Systém je plně funkční po stránce CRM, rezervací, compliance a UX. Jedinou výhradou je, že **Comgate platební brána běží v MOCK módu** — pro pilot s reálnými platbami je nutné doplnit produkční klíče (což je na schválení Comgate a samotné instituce).

### 🎯 Posledních 5 doporučených kroků před spuštěním

1. **Dokončit schválení Comgate** a vložit produkční `gateway_api_key` + `gateway_secret` do payment settings pro pilotní instituce
2. **Ověřit e-mailovou doručitelnost přes Resend** — poslat 3 testovací zprávy (potvrzení rezervace, notifikace admina, GDPR potvrzení) a zkontrolovat, že spam score < 2
3. **Prověřit SPF/DKIM/DMARC** záznamy pro doménu `budezivo.cz` (bez nich jdou e-maily často do spamu)
4. **Záloha DB** — před spuštěním pilotu export celé Supabase DB přes `pg_dump` do S3 nebo lokálního souboru, jako jednorázový snapshot (v případě potřeby rollbacku)
5. **Monitorovací alerty** — nastavit alerty pro: HTTP 5xx > 5/min, backend restart > 2× za hodinu, failed login rate > 20/min (UptimeRobot / Better Uptime stačí pro pilot)

---

### Změny provedené během auditu
- `/app/backend/scripts/pilot_cleanup.py` (NEW) — idempotentní cleanup test dat
- `/app/backend/routes/programs.py` — 500 fix při non-UUID vstupu
- DB: 15 test institucí + 33 škol + 3 test users + 1 duplicitní event odstraněno
