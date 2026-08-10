# Budeživo.cz - Deployment Guide

## Architektura

```
┌─────────────────┐                    ┌─────────────────┐     ┌─────────────────┐
│     Vercel      │                    │     Railway     │────▶│    Supabase     │
│   (Frontend)    │──── API calls ────▶│    (Backend)    │     │  (PostgreSQL)   │
│   React SPA     │   (cross-origin)   │   FastAPI API   │     │    Database     │
└─────────────────┘                    └─────────────────┘     └─────────────────┘
```

## DŮLEŽITÉ: Cross-Origin API Architecture

Frontend přímo volá Railway backend API (cross-origin).
Backend povoluje pouze explicitně vyjmenované frontend domény. Nepoužívejte
wildcard `*`; backend ji z bezpečnostních důvodů ignoruje.

## 1. Backend - Railway

### Nastavení
1. Připojte GitHub repo k Railway
2. Nastavte root directory: `backend`
3. Railway automaticky detekuje `Dockerfile`

### Environment Variables (Railway)
```
DATABASE_URL=postgresql://postgres.[supabase-ref]:password@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
JWT_SECRET=your-secure-jwt-secret-min-32-chars
CORS_ORIGINS=https://www.budezivo.cz,https://budezivo.cz
FRONTEND_URL=https://www.budezivo.cz
BACKEND_URL=https://YOUR-RAILWAY-URL.up.railway.app
RESEND_API_KEY=re_xxxxxx (optional)
SENDER_EMAIL=noreply@yourdomain.com (optional)
```

Pro preview nebo testovací frontend přidejte konkrétní preview URL do
`CORS_ORIGINS` jako další hodnotu oddělenou čárkou. Nikdy nenastavujte
`CORS_ORIGINS=*`.

### Ověření backendu
Po deployment zkontrolujte:
```bash
curl https://YOUR-RAILWAY-URL.up.railway.app/api/
# Mělo by vrátit: {"message": "KulturaBooking API v2.0 - Supabase Edition"}
```

## 2. Frontend - Vercel

### Nastavení
1. Připojte GitHub repo k Vercel
2. Nastavte root directory: `frontend`
3. Framework: Create React App

### Environment Variables (Vercel) - KRITICKÉ!
```
REACT_APP_BACKEND_URL=https://YOUR-RAILWAY-URL.up.railway.app
```

⚠️ **DŮLEŽITÉ:** 
- Tato proměnná MUSÍ ukazovat na váš Railway backend
- Frontend bude volat API přímo na Railway (cross-origin)
- Backend musí mít ve `CORS_ORIGINS` uvedenou přesnou frontend doménu

### Po nastavení env variable
1. **Redeploy** projekt na Vercel (nebo nový commit)
2. Vercel musí rebuild s novou env variable

## 3. Database - Supabase

### Nastavení
1. Vytvořte projekt na supabase.com
2. Použijte Transaction Pooler connection string (port 6543)
3. Spusťte migrace: `alembic upgrade head`

### Connection String Format
```
postgresql://postgres.[project-ref]:[password]@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
```

## 4. Domain Setup (budezivo.cz)

### Vercel (Frontend) - budezivo.cz, www.budezivo.cz
1. Settings → Domains → Add domain
2. Přidejte DNS záznamy u Wedos:

```
A     @     76.76.21.21
CNAME www   cname.vercel-dns.com
```

### Railway (Backend)
Není potřeba custom domain - frontend používá Railway URL přímo.

## 5. Testovací přístup
Testovací účet a heslo nastavte bezpečným kanálem mimo repozitář. Do dokumentace
ani zdrojových souborů nevkládejte konkrétní hesla.

---

## Troubleshooting

### ❌ HTTP 405 "Method Not Allowed"
**Příčina:** `REACT_APP_BACKEND_URL` není nastavena nebo ukazuje na špatnou URL.

**Řešení:**
1. Na Vercel → Settings → Environment Variables
2. Přidejte/opravte: `REACT_APP_BACKEND_URL` = `https://YOUR-RAILWAY-URL.up.railway.app`
3. Redeploy projekt

### ❌ CORS chyby
**Příčina:** Backend nepovoluje cross-origin požadavky.

**Řešení:**
1. Na Railway → Backend → Variables nastavte konkrétní frontend domény:
   `CORS_ORIGINS=https://www.budezivo.cz,https://budezivo.cz`
2. Pro preview přidejte také přesnou preview URL, například:
   `CORS_ORIGINS=https://www.budezivo.cz,https://budezivo.cz,https://preview.example.vercel.app`
3. Proveďte redeploy backendu.

### ❌ Login nefunguje ale curl funguje
**Příčina:** Frontend env variable chybí nebo nebyl proveden redeploy.

**Řešení:**
1. Zkontrolujte `REACT_APP_BACKEND_URL` na Vercel
2. Proveďte redeploy (nebo nový commit)

### ❌ Demo programy se nenačítají
**Příčina:** Stejná jako HTTP 405 - API volání nejdou na Railway.

**Řešení:** Nastavte správně `REACT_APP_BACKEND_URL` na Vercel.
