# Changelog — Budeživo.cz

## 2026-06-12 — COMPLETNÍ SECURITY, LOAD & RESILIENCE AUDIT (FÁZE 1-9)

### Opraveno + otestováno (`backend/tests/test_audit_phase1_fixes.py`, 5/5 PASS; login/auth ověřeno bez regrese)
- **A1 (P0):** Odstraněn nechráněný `POST /api/plan/setup-columns` (spouštěl DDL + hromadný upgrade všech institucí na PRO+ bez auth). Ověřeno 404.
- **A2 (P2):** Dočasná hesla `uuid.uuid4()[:8]` → `secrets.token_urlsafe(12)` v `team.py` a `institution_join.py`.
- **A3 (P2):** `GET /event-payments/by-ref/{refId}` maskuje `applicant_email` (`ja***@x.cz`).
- **A4 (P2):** `GET /public/prefill` rate-limit zpřísněn 20→6/min (anti-enumeration PII).
- **A5 (P1):** CORS — `config.py` natvrdo odfiltruje `"*"`, `.env CORS_ORIGINS` na explicitní allowlist (dříve `"*"` + credentials = reflexe libovolného originu).

### Ověřeno jako bezpečné
- Auth rate-limiting (login 5/min, forgot 3/min…), cookies `httpOnly+Secure+SameSite=Lax`, SQL parametrizováno, webhooky se signature + MOCK guard, mass-assignment (uzavřená schémata).

### Otevřené (vyžadují rozhodnutí — viz SECURITY_ROADMAP.md A6-A12)
- A6 (P2) rotace slabého `JWT_SECRET` (odhlásí uživatele) — odloženo uživatelem.
- A7 (P3) perimeter CORS `*` od Cloudflare/ingress (infra, mitigováno SameSite cookies).
- A10 (P2) event apply bez kontroly kapacity → over-booking.
- A11 (P2) numerické plan limity se nevynucují server-side.
- A12 (P3) GDPR anonymize pokrývá jen user řádek.
