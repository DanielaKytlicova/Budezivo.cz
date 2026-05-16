# Google Calendar OAuth — Setup Guide

This SaaS supports a per-lecturer Google Calendar integration that mirrors the
existing Outlook (Microsoft Graph) flow. Events from each lecturer's primary
Google calendar are pulled every 5 minutes by APScheduler and stored as
`availability_blocks` (source='google'), where the existing collision service
treats them identically to Outlook events.

The integration is **off by default**: when `GOOGLE_CLIENT_ID` /
`GOOGLE_CLIENT_SECRET` are missing the UI shows a disabled "Připojit Google"
button with the message "Modul není nakonfigurován" and the backend returns
HTTP 503 from `/api/google-calendar/connect`.

## How to enable Google Calendar (one-time)

### 1. Create Google Cloud project
1. Go to <https://console.cloud.google.com>
2. Create project → name it "Budeživo Production" (or similar)

### 2. Enable Google Calendar API
1. APIs & Services → Library
2. Search "Google Calendar API" → Enable

### 3. Configure OAuth consent screen
1. APIs & Services → OAuth consent screen
2. Choose **External** → Create
3. Fill in:
   - App name: `Budeživo`
   - User support email: your email
   - Developer contact: your email
4. Save & Continue
5. Scopes — Add:
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/userinfo.email`
6. Save & Continue
7. Test users (during development) — Add the email of every lecturer who will
   connect their calendar before you publish the app.

### 4. Create OAuth Client ID
1. APIs & Services → Credentials → Create Credentials → OAuth client ID
2. Application type: **Web application**
3. Name: `Budeživo backend`
4. Authorized JavaScript origins:
   - `https://budezivo.cz`
   - `https://school-crm-pilot.preview.emergentagent.com` (preview env, optional)
5. Authorized redirect URIs:
   - `https://budezivo.cz/api/google-calendar/callback`
   - `https://school-crm-pilot.preview.emergentagent.com/api/google-calendar/callback`
6. Click **Create** → copy the Client ID and Client Secret

### 5. Add credentials to backend `.env`
```env
GOOGLE_CLIENT_ID=<client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-<secret>
GOOGLE_REDIRECT_URI=https://budezivo.cz/api/google-calendar/callback
```

Then restart backend: `sudo supervisorctl restart backend`.

### 6. Verify
- Lectro logs in → Lektorský profil → "Připojit Google" button is now blue/enabled
- Click → Google consent popup → authorize → popup posts message → toast confirms
- After ~15 s the lecturer's busy events appear in the week calendar greyed out
- APScheduler then re-syncs every 5 minutes automatically

## Common pitfalls

- **`refresh_token` only returned on first consent**: if a user previously
  consented and we lost the refresh token, they need to revoke access at
  <https://myaccount.google.com/permissions> and reconnect. Our implementation
  always passes `prompt=consent` to mitigate, but Google occasionally still
  omits the refresh token on re-consent — instruct users to revoke first.
- **Redirect URI exact match**: every redirect URI must be in the Authorized
  list including the exact scheme (https) and trailing path. Mismatch returns
  `redirect_uri_mismatch` in the popup.
- **OAuth consent screen in Testing mode**: tokens expire after 7 days. Publish
  to Production before the pilot ends.
- **All-day events are intentionally skipped** — only events with explicit
  `dateTime` start/end create availability blocks. (Outlook does the same.)

## Production checklist

- [ ] OAuth consent screen status: **In production** (not Testing)
- [ ] Privacy policy URL filled (Budeživo `/gdpr` page)
- [ ] App domain verified in Google Search Console (for unverified-app warning)
- [ ] Authorized redirect URIs pruned to just production domain
