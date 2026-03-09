# Budeživo.cz - Deployment Guide

## Architektura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Vercel      │────▶│     Railway     │────▶│    Supabase     │
│   (Frontend)    │     │    (Backend)    │     │  (PostgreSQL)   │
│   React SPA     │     │   FastAPI API   │     │    Database     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       ▲
        │   /api/* proxy        │
        └───────────────────────┘
```

## DŮLEŽITÉ: Vercel API Proxy

Frontend používá Vercel rewrites pro proxy API požadavků na Railway backend.
Toto řešení:
- Eliminuje CORS problémy
- Zjednodušuje konfiguraci
- Frontend automaticky detekuje produkční prostředí

## 1. Backend - Railway

### Nastavení
1. Připojte GitHub repo k Railway
2. Nastavte root directory: `backend`
3. Railway automaticky detekuje `Dockerfile`

### Environment Variables (Railway)
```
DATABASE_URL=postgresql://postgres.[supabase-ref]:password@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
JWT_SECRET=your-secure-jwt-secret-min-32-chars
CORS_ORIGINS=*
RESEND_API_KEY=re_xxxxxx (optional)
SENDER_EMAIL=noreply@yourdomain.com (optional)
```

### Ověření
Po deployment zkontrolujte:
```bash
curl https://your-railway-url.up.railway.app/api/
# Mělo by vrátit: {"message": "KulturaBooking API v2.0 - Supabase Edition"}
```

## 2. Frontend - Vercel

### Nastavení
1. Připojte GitHub repo k Vercel
2. Nastavte root directory: `frontend`
3. Framework: Create React App

### Environment Variables (Vercel) - KRITICKÉ!
```
BACKEND_URL=https://your-railway-url.up.railway.app
```

⚠️ **POZOR:** Proměnná se jmenuje `BACKEND_URL` (NE `REACT_APP_BACKEND_URL`)!
Tato proměnná je použita v `vercel.json` pro proxy rewrites.

### Jak funguje proxy
`vercel.json` obsahuje:
```json
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "${BACKEND_URL}/api/:path*" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

Frontend kód automaticky detekuje produkční prostředí (`budezivo.cz`) a používá relativní cesty `/api/*`.

## 3. Database - Supabase

### Nastavení
1. Vytvořte projekt na supabase.com
2. Použijte Transaction Pooler connection string (port 6543)
3. Spusťte migrace: `alembic upgrade head`

### Connection String Format
```
postgresql://postgres.[project-ref]:[password]@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
```

## 4. Domain Setup

### Vercel (Frontend) - budezivo.cz
1. Settings → Domains → Add domain
2. Přidejte DNS záznamy u Wedos:

```
A     @     76.76.21.21
CNAME www   cname.vercel-dns.com
```

### Railway (Backend API) - NENÍ POTŘEBA CUSTOM DOMAIN
Díky Vercel proxy není potřeba nastavovat custom doménu pro Railway.
Všechny API požadavky jdou přes `budezivo.cz/api/*` → Railway.

## 5. Testovací Credentials
```
Email: demo@budezivo.cz
Password: Demo2026!
```

## Troubleshooting

### "Request failed with status code 405"
**Příčina:** Vercel nemá nastavenou `BACKEND_URL` environment variable.
**Řešení:** 
1. Jděte do Vercel → Settings → Environment Variables
2. Přidejte `BACKEND_URL` = `https://your-railway-url.up.railway.app`
3. Redeploy projekt

### Login nefunguje ale API funguje přes curl
**Příčina:** Frontend environment variable není správně nastavena.
**Řešení:** Zkontrolujte že `BACKEND_URL` je nastavena na Vercel a proveďte redeploy.

### CORS chyby
**Příčina:** Backend nepovoluje cross-origin požadavky.
**Řešení:** Nastavte `CORS_ORIGINS=*` na Railway. S proxy by CORS neměl být problém.

### Demo programy se nenačítají
**Příčina:** API požadavky nejdou na Railway backend.
**Řešení:** Stejné jako pro HTTP 405 - zkontrolujte `BACKEND_URL` na Vercel.
