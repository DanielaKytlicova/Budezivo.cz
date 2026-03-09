# Budeživo.cz - Deployment Guide

## Architektura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Vercel      │────▶│     Railway     │────▶│    Supabase     │
│   (Frontend)    │     │    (Backend)    │     │  (PostgreSQL)   │
│   React SPA     │     │   FastAPI API   │     │    Database     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

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

### Environment Variables (Vercel) - DŮLEŽITÉ!
```
REACT_APP_BACKEND_URL=https://your-railway-url.up.railway.app
```

⚠️ **KRITICKÉ:** Tato proměnná MUSÍ ukazovat na váš Railway backend, NE na Vercel URL!

### Časté chyby

#### HTTP 405 Method Not Allowed
**Příčina:** `REACT_APP_BACKEND_URL` ukazuje na Vercel místo Railway
**Řešení:** Nastavte správnou Railway URL v Vercel environment variables

#### CORS errors
**Příčina:** Backend nepovoluje origin Vercel URL
**Řešení:** Nastavte `CORS_ORIGINS=*` nebo konkrétní Vercel URL na Railway

## 3. Database - Supabase

### Nastavení
1. Vytvořte projekt na supabase.com
2. Použijte Transaction Pooler connection string (port 6543)
3. Spusťte migrace: `alembic upgrade head`

### Connection String Format
```
postgresql://postgres.[project-ref]:[password]@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
```

## 4. Domain Setup (volitelné)

### Vercel (Frontend)
1. Settings → Domains → Add domain
2. Přidejte CNAME záznam u registrátora

### Railway (Backend API)
1. Settings → Networking → Add custom domain
2. Přidejte CNAME záznam u registrátora

### DNS záznamy (příklad pro budezivo.cz)
```
# Frontend
CNAME  www          cname.vercel-dns.com
CNAME  @            cname.vercel-dns.com

# Backend API  
CNAME  api          your-app.up.railway.app
```

## 5. Testovací Credentials
```
Email: demo@budezivo.cz
Password: Demo2026!
```

## Troubleshooting

### "Request failed with status code 405"
Frontend posílá API požadavky na špatnou URL. Zkontrolujte `REACT_APP_BACKEND_URL` na Vercel.

### "Network Error" nebo CORS chyby
Backend nepovoluje cross-origin požadavky. Zkontrolujte `CORS_ORIGINS` na Railway.

### Login nefunguje ale API funguje přes curl
Frontend environment variable není správně nastavena nebo nebyl proveden redeploy.
