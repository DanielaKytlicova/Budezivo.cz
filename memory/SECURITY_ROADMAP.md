# Bezpečnostní plán oprav — Budeživo.cz

## Implementováno (10. dubna 2026)

### KRITICKÉ (HIGH) — Hotovo
| # | Nález | Oprava | Status |
|---|-------|--------|--------|
| H1 | Email debug endpoint veřejně vystavoval API klíče | Endpoint vyžaduje auth, nevrací raw klíče | DONE |
| H2 | SQL Injection v `/programs/debug/{id}` | Parametrizované dotazy + auth | DONE |
| H3 | SQL Injection v `schools.py` IN clause | Parametrizované dotazy s `id_params` dict | DONE |
| H4 | ICS Calendar feedy bez autentizace | HMAC-podepsané tokeny v URL | DONE |
| H5 | Public API vystavovalo business logiku | Whitelist povolených fieldů (26 z 40+) | DONE |

### STŘEDNÍ (MEDIUM) — Hotovo
| # | Nález | Oprava | Status |
|---|-------|--------|--------|
| M1 | JWT fallback secret v reset-password | Odstraněn fallback, chybějící secret = HTTP 500 | DONE |
| M3 | Swagger docs veřejně přístupné | Podmíněno preview env (`_is_preview` check) | DONE |
| M4 | `postMessage("*")` wildcard origin | Restrictive origin z env proměnných | DONE |
| M6 | Žádný rate limiting na veřejných endpointech | slowapi na /public/*, /programs/public, /bookings/public | DONE |
| L3 | Absence HSTS hlavičky | `Strict-Transport-Security: max-age=31536000; includeSubDomains` | DONE |

---

## Plánováno (Budoucí iterace)

### P1 — Střední priorita
| # | Nález | Plán opravy | Status |
|---|-------|------------|--------|
| M2 | JWT platnost 7 dní bez revokace | ~~Implementovat refresh token + blacklist~~ | **DONE** |
| M5 | In-memory OAuth state | ~~Přesunout `_oauth_states` do DB~~ | **DONE** |
| L1 | JWT v localStorage (XSS riziko) | ~~httpOnly Secure cookie s SameSite=Lax~~ | **DONE** |
| L2 | Booking response vrací interní metadata | ~~Filtrovat interní pole z public response~~ | **DONE** |

### P2 — Nižší priorita (anti-cloning posílení)
| # | Plán | Status |
|---|------|--------|
| AC1 | Source map removal v produkčním buildu (GENERATE_SOURCEMAP=false) | **DONE** |
| AC2 | JS bundle obfuskace (terser-webpack-plugin s mangle) | TODO |
| AC3 | API response minimalizace — další filtry na booking responses | **DONE** |

### P3 — Infrastrukturní (long-term)
| # | Plán | Status |
|---|------|--------|
| I1 | Alembic migrace místo raw SQL | **DONE** (inicializováno, baseline stamp) |
| I2 | WAF (Web Application Firewall) pro API | **DONE** (SQL/XSS/timing bloky) |
| I3 | CAPTCHA na veřejné formuláře | DEFERRED (rate limiting stačí) |

---

## Anti-Cloning Score

**Před opravami:** 5/10
**Po opravách:** 7/10

| Oblast | Před | Po |
|--------|------|-----|
| Business logic v API | Plně vystavena | Skryta (whitelist) |
| ICS feed data | Veřejné PII | HMAC tokeny |
| Debug endpointy | Veřejné + SQL injection | Auth + parametrizováno |
| API dokumentace | Veřejný Swagger | Podmíněno prostředím |
| Rate limiting | Žádné | 5-30 req/min na veřejných |
| Collision logic | Backend only | Backend only (beze změny) |

---

## FÁZE 1-9 AUDIT (12. června 2026) — COMPLETNÍ SECURITY, LOAD & RESILIENCE AUDIT

### Opraveno a otestováno (`backend/tests/test_audit_phase1_fixes.py` — 5/5 PASS)
| # | Závažnost | Nález | Oprava | Status |
|---|-----------|-------|--------|--------|
| A1 | 🔴 P0 | `POST /api/plan/setup-columns` — nechráněný endpoint spouštěl DDL (`ALTER TABLE`) + hromadný `UPDATE ... SET plan='pro_plus'` na všech institucích bez auth | Endpoint kompletně odstraněn (migrace patří do Alembic). Ověřeno: 404. | DONE |
| A2 | 🟠 P2 | Slabá entropie dočasných hesel (`uuid.uuid4()[:8]`) v `team.py` + `institution_join.py` | `secrets.token_urlsafe(12)` | DONE |
| A3 | 🟠 P2 | `GET /event-payments/by-ref/{refId}` vracel plný `applicant_email` komukoliv se znalostí UUID | E-mail maskován (`ja***@skola.cz`) | DONE |
| A4 | 🟠 P2 | `GET /public/prefill` umožňoval enumeraci PII (jméno/telefon/škola) per e-mail | Rate-limit zpřísněn z 20→6/min | DONE |
| A5 | 🔴 P1 | CORS: `.env CORS_ORIGINS="*"` → `"*"` v allowlistu + `allow_credentials=True` → FastAPI reflektoval libovolný origin | `config.py` natvrdo filtruje `"*"`; `.env` explicitní allowlist. Ověřeno: cizí origin se na app vrstvě nereflektuje | DONE |

### Ověřeno jako BEZPEČNÉ (žádná akce)
- Auth rate-limiting: login 5/min, forgot-password 3/min, reset 10/min, register — OK.
- Cookies: `httpOnly + Secure + SameSite=Lax` → silná CSRF ochrana.
- SQL: `schools.py` f-string IN-klauzule jsou parametrizované; `collision_service` advisory lock = int64 hash. Bez injection.
- Webhooky (Comgate/Stripe) + `mock/complete` — signature ověření + MOCK-mode guard.

### Otevřené / DEFERRED (vyžadují rozhodnutí)
| # | Závažnost | Nález | Pozn. |
|---|-----------|-------|-------|
| A6 | 🟠 P2 | `JWT_SECRET` = slabá výchozí hodnota `"...change_in_production"` | Rotace odhlásí všechny uživatele → vyžaduje souhlas / ops okno |
| A7 | 🟡 P3 | Perimeter (Cloudflare/ingress) vrací `Access-Control-Allow-Origin: *` | Infrastruktura preview prostředí; v produkci na budeživo.cz řídí provozovatel. Cookie posture (SameSite=Lax) hrozbu mitiguje |
| A8 | 🟢 Low | `GET .../application/{id}/pdf` IDOR přes neuhádnutelné UUID | Akceptovatelný confirmation-link vzor |

### Zbývající fáze auditu (TODO)
- FÁZE 6: hloubkový injection/mass-assignment sken všech write endpointů
- FÁZE 7: race conditions (souběžné bookingy, plan limity, event kapacity)
- FÁZE 8: GDPR — kompletní export/anonymize/retence audit
- FÁZE 10: finální prioritizovaný report

### FÁZE 6-8 — Dokončeno (12. června 2026)
| # | Záv. | Nález | Stav / Doporučení |
|---|------|-------|-------------------|
| A9 | ✅ | Mass-assignment v `events/rooms/programs` update | BEZPEČNÉ — uzavřená Pydantic schémata (bez `institution_id`/`role`); `institution_id` se předává server-side zvlášť |
| A10 | 🟠 P2 | `POST /events/public/{id}/apply` NEMÁ kontrolu kapacity → události lze přeplnit (`spots_left` může jít do mínusu) | OTEVŘENO — vyžaduje rozhodnutí: vynutit kapacitu (s row-lock proti race) nebo je over-booking záměr (manuální výběr + waitlist)? |
| A11 | 🟠 P2 | Numerické plan limity (`programs_limit`, `bookings_monthly_limit`) se NEvynucují server-side (jen feature-flag gating funguje) → free/start plán může překročit kvóty (revenue leak) | OTEVŘENO — vyžaduje rozhodnutí: tvrdé vynucení limitů vs. soft-limit + upsell |
| A12 | 🟡 P3 | GDPR `/anonymize` upraví jen user řádek, ne PII v souvisejících bookingách | REVIEW — admin PII je v user tabulce (OK), PII žáků/škol je samostatný data-subject; doporučeno doplnit rozsah erasure |

