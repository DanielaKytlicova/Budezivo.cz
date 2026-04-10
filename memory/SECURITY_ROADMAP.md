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
