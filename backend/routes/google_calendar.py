"""
Google Calendar Integration — mirrors the Microsoft Outlook integration.

OAuth 2.0 Authorization Code flow (offline access for refresh_token), token
management, calendar event polling, availability blocks. Reuses the existing
``user_calendar_integrations`` table with ``provider='google'`` and the same
``microsoft_user_id`` column to store the Google user id (kept for schema
parity — no migration needed).

Graceful "not configured" behaviour: when GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
are unset, ``/connect`` returns 503 with a Czech message, but all other
endpoints (``/status``, ``/blocks``, scheduler) keep working without crashing.
"""
from __future__ import annotations

import logging
import os
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.supabase import get_db
from database.models import (
    UserCalendarIntegration, AvailabilityBlock, OAuthState, Program,
    Reservation, Room, Institution, CalendarEventExport,
)
from services.plan_service import require_feature
from services.google_calendar_helpers import (
    SCOPES, EVENTS_SCOPE, has_events_scope, is_budezivo_event,
    build_export_event_body, reservation_assigned_user_ids, CANCELLED_STATUSES,
)
from pydantic import BaseModel


router = APIRouter(
    prefix="/google-calendar",
    tags=["Google Calendar"],
    dependencies=[Depends(require_feature("outlook_sync"))],
)
logger = logging.getLogger(__name__)


# ── Config ──────────────────────────────────────────────────────────

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
USERINFO_URI = "https://www.googleapis.com/oauth2/v2/userinfo"
CALENDAR_EVENTS_URI = (
    "https://www.googleapis.com/calendar/v3/calendars/primary/events"
)

SCOPES = SCOPES  # imported from helpers (calendar.readonly + calendar.events + userinfo.email)
PROVIDER = "google"
SOURCE = "google"
OAUTH_STATE_TTL_MINUTES = 10


def _is_configured() -> bool:
    return bool(CLIENT_ID and CLIENT_SECRET)


def _get_redirect_uri(request: Request) -> str:
    """Build redirect URI from the current request's public-facing host."""
    fwd_host = request.headers.get("x-forwarded-host")
    fwd_proto = request.headers.get("x-forwarded-proto", "https")
    if fwd_host:
        return f"{fwd_proto}://{fwd_host}/api/google-calendar/callback"
    origin = request.headers.get("origin") or request.headers.get("referer")
    if origin:
        parsed = urlparse(origin)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return f"{base}/api/google-calendar/callback"
    return REDIRECT_URI or "https://budezivo.cz/api/google-calendar/callback"


# ── OAuth Flow ──────────────────────────────────────────────────────


@router.get("/connect")
async def connect_google(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 1: build the Google consent URL and persist OAuth state."""
    if not _is_configured():
        raise HTTPException(
            status_code=503,
            detail="Google OAuth není nakonfigurován. Kontaktujte správce platformy.",
        )

    redirect = _get_redirect_uri(request)
    state = secrets.token_urlsafe(32)

    db.add(OAuthState(
        state=state,
        user_id=uuid.UUID(current_user["user_id"]),
        institution_id=uuid.UUID(current_user["institution_id"]),
        redirect_uri=redirect,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OAUTH_STATE_TTL_MINUTES),
    ))
    await db.commit()

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect,
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",     # required to receive refresh_token
        "prompt": "consent",          # force refresh_token on every consent
        "include_granted_scopes": "true",
    }
    return {"auth_url": f"{AUTH_URI}?{urlencode(params)}"}


@router.get("/callback")
async def oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Step 2: exchange the authorization code for tokens and persist them."""
    if error:
        logger.error(f"Google OAuth error: {error} - {error_description}")
        return _close_popup_html(f"Chyba: {error_description or error}")

    if not code or not state:
        return _close_popup_html("Chybí autorizační kód")

    result = await db.execute(select(OAuthState).where(OAuthState.state == state))
    oauth_row = result.scalar_one_or_none()
    if not oauth_row or oauth_row.expires_at < datetime.now(timezone.utc):
        if oauth_row:
            await db.delete(oauth_row)
            await db.commit()
        return _close_popup_html("Neplatný stav relace. Zkuste to znovu.")

    user_data = {
        "user_id": str(oauth_row.user_id),
        "institution_id": str(oauth_row.institution_id),
        "redirect_uri": oauth_row.redirect_uri,
    }
    await db.delete(oauth_row)
    await db.commit()

    redirect = user_data.get("redirect_uri") or REDIRECT_URI
    try:
        token_data = await _exchange_code_for_tokens(code, redirect)
    except Exception as e:
        logger.error(f"Google token exchange failed: {e}")
        return _close_popup_html(f"Nepodařilo se získat token: {e}")

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    granted_scopes = token_data.get("scope") or ""
    expires_in = token_data.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Pull user identity (email) for diagnostics & to store as google_user_id
    google_user_id = None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                USERINFO_URI,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            if resp.status_code == 200:
                profile = resp.json()
                # Prefer the stable "id" field; fall back to email.
                google_user_id = profile.get("id") or profile.get("email")
    except Exception as e:
        logger.warning(f"Google userinfo failed: {e}")

    user_uuid = uuid.UUID(user_data["user_id"])
    inst_uuid = uuid.UUID(user_data["institution_id"])

    result = await db.execute(
        select(UserCalendarIntegration).where(and_(
            UserCalendarIntegration.user_id == user_uuid,
            UserCalendarIntegration.provider == PROVIDER,
        ))
    )
    integration = result.scalar_one_or_none()

    if integration:
        integration.access_token = access_token
        # Google only returns refresh_token on first consent; preserve old one.
        if refresh_token:
            integration.refresh_token = refresh_token
        integration.expires_at = expires_at
        integration.microsoft_user_id = google_user_id  # reused col
        integration.is_active = True
        integration.sync_error = None
        integration.granted_scopes = granted_scopes
        # New grant with events scope clears any pending reconnect requirement.
        integration.needs_reconnect = not has_events_scope(granted_scopes)
        integration.updated_at = datetime.now(timezone.utc)
    else:
        integration = UserCalendarIntegration(
            user_id=user_uuid,
            institution_id=inst_uuid,
            provider=PROVIDER,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            microsoft_user_id=google_user_id,
            is_active=True,
            granted_scopes=granted_scopes,
            needs_reconnect=not has_events_scope(granted_scopes),
        )
        db.add(integration)

    await db.commit()

    try:
        await _full_sync(db, integration)
    except Exception as e:
        logger.error(f"Initial Google sync failed: {e}")

    return _close_popup_html(None)


@router.get("/status")
async def get_connection_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return whether the current user has an active Google connection."""
    user_uuid = uuid.UUID(current_user["user_id"])
    result = await db.execute(
        select(UserCalendarIntegration).where(and_(
            UserCalendarIntegration.user_id == user_uuid,
            UserCalendarIntegration.provider == PROVIDER,
        ))
    )
    integration = result.scalar_one_or_none()

    if not integration or not integration.is_active:
        return {"connected": False, "configured": _is_configured()}

    return {
        "connected": True,
        "configured": _is_configured(),
        "google_user_id": integration.microsoft_user_id,
        "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
        "sync_error": integration.sync_error,
        "expires_at": integration.expires_at.isoformat() if integration.expires_at else None,
        "import_enabled": integration.import_enabled,
        "export_enabled": integration.export_enabled,
        "auto_sync_enabled": integration.auto_sync_enabled,
        "needs_reconnect": integration.needs_reconnect,
        "has_events_scope": has_events_scope(integration.granted_scopes),
    }


class SyncSettingsUpdate(BaseModel):
    import_enabled: Optional[bool] = None
    export_enabled: Optional[bool] = None
    auto_sync_enabled: Optional[bool] = None


@router.put("/settings")
async def update_sync_settings(
    data: SyncSettingsUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's Google sync-mode toggles (own account only)."""
    user_uuid = uuid.UUID(current_user["user_id"])
    result = await db.execute(
        select(UserCalendarIntegration).where(and_(
            UserCalendarIntegration.user_id == user_uuid,
            UserCalendarIntegration.provider == PROVIDER,
        ))
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Google kalendář není připojen")

    if data.import_enabled is not None:
        integration.import_enabled = data.import_enabled
    if data.export_enabled is not None:
        if data.export_enabled and not has_events_scope(integration.granted_scopes):
            integration.needs_reconnect = True
            raise HTTPException(
                status_code=409,
                detail="Pro export je potřeba znovu připojit Google účet (chybí oprávnění calendar.events).",
            )
        integration.export_enabled = data.export_enabled
    if data.auto_sync_enabled is not None:
        integration.auto_sync_enabled = data.auto_sync_enabled
    integration.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {
        "import_enabled": integration.import_enabled,
        "export_enabled": integration.export_enabled,
        "auto_sync_enabled": integration.auto_sync_enabled,
    }


class DisconnectRequest(BaseModel):
    delete_exported: bool = False


@router.post("/disconnect")
async def disconnect_google(
    data: DisconnectRequest = DisconnectRequest(),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove Google connection + imported blocks. Optionally delete exported events.

    Never touches the user's own (non-Budeživo) Google events.
    """
    user_uuid = uuid.UUID(current_user["user_id"])
    result = await db.execute(
        select(UserCalendarIntegration).where(and_(
            UserCalendarIntegration.user_id == user_uuid,
            UserCalendarIntegration.provider == PROVIDER,
        ))
    )
    integration = result.scalar_one_or_none()

    failed_deletes = 0
    if data.delete_exported and integration:
        token = await _get_valid_token(db, integration)
        exports = (await db.execute(
            select(CalendarEventExport).where(and_(
                CalendarEventExport.user_id == user_uuid,
                CalendarEventExport.provider == PROVIDER,
            ))
        )).scalars().all()
        if token:
            for exp in exports:
                if exp.google_event_id and not await _delete_google_event(token, exp.google_event_id):
                    failed_deletes += 1

    # Remove our export links regardless (integration is going away).
    await db.execute(
        delete(CalendarEventExport).where(and_(
            CalendarEventExport.user_id == user_uuid,
            CalendarEventExport.provider == PROVIDER,
        ))
    )
    # Remove imported availability blocks.
    await db.execute(
        delete(AvailabilityBlock).where(and_(
            AvailabilityBlock.user_id == user_uuid,
            AvailabilityBlock.source == SOURCE,
        ))
    )
    await db.execute(
        delete(UserCalendarIntegration).where(and_(
            UserCalendarIntegration.user_id == user_uuid,
            UserCalendarIntegration.provider == PROVIDER,
        ))
    )
    await db.commit()
    msg = "Google kalendář odpojen, importované bloky smazány"
    if data.delete_exported:
        msg += f", exportované události odstraněny"
        if failed_deletes:
            msg += f" ({failed_deletes} se nepodařilo odstranit)"
    return {"message": msg, "failed_deletes": failed_deletes}


@router.post("/sync")
async def trigger_sync(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually run a full (import + export) sync for the current user."""
    user_uuid = uuid.UUID(current_user["user_id"])
    result = await db.execute(
        select(UserCalendarIntegration).where(and_(
            UserCalendarIntegration.user_id == user_uuid,
            UserCalendarIntegration.provider == PROVIDER,
            UserCalendarIntegration.is_active == True,
        ))
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Google kalendář není připojen")

    try:
        stats = await _full_sync(db, integration)
    except Exception as e:
        logger.error(f"Manual Google sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Synchronizace selhala: {e}")

    return {
        "message": (
            f"Importováno {stats['imported']} blokací, vytvořeno {stats['created']}, "
            f"aktualizováno {stats['updated']}, odstraněno {stats['deleted']}, chyb {stats['errors']}"
        ),
        **stats,
    }


# ── Availability Blocks API ─────────────────────────────────────────


@router.get("/blocks")
async def list_blocks(
    user_id: Optional[str] = Query(None, description="Filter by specific user"),
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List Google availability blocks for the institution."""
    inst_uuid = uuid.UUID(current_user["institution_id"])
    conditions = [
        AvailabilityBlock.institution_id == inst_uuid,
        AvailabilityBlock.source == SOURCE,
    ]
    if user_id:
        conditions.append(AvailabilityBlock.user_id == uuid.UUID(user_id))
    if start:
        conditions.append(
            AvailabilityBlock.end_time >= datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
        )
    if end:
        conditions.append(
            AvailabilityBlock.start_time <= datetime.fromisoformat(f"{end}T23:59:59").replace(tzinfo=timezone.utc)
        )

    result = await db.execute(
        select(AvailabilityBlock).where(and_(*conditions)).order_by(AvailabilityBlock.start_time)
    )
    return [_block_to_dict(b) for b in result.scalars().all()]


@router.post("/blocks/{block_id}/override")
async def toggle_override(
    block_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle override on a Google block (allow/disallow bookings during it)."""
    inst_uuid = uuid.UUID(current_user["institution_id"])
    result = await db.execute(
        select(AvailabilityBlock).where(and_(
            AvailabilityBlock.id == uuid.UUID(block_id),
            AvailabilityBlock.institution_id == inst_uuid,
            AvailabilityBlock.source == SOURCE,
        ))
    )
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Blok nenalezen")

    block.override = not block.override
    block.updated_at = datetime.now(timezone.utc)
    await db.commit()

    action = "povoleny" if block.override else "blokovány"
    return {"message": f"Rezervace {action} v tomto čase", "block": _block_to_dict(block)}


# ── Internal Helpers ────────────────────────────────────────────────


async def _exchange_code_for_tokens(code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(TOKEN_URI, data=data, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"Token endpoint returned {resp.status_code}: {resp.text}")
        return resp.json()


async def _refresh_access_token(integration: UserCalendarIntegration) -> Optional[str]:
    """Refresh access token using refresh_token. Returns new access_token or None."""
    if not integration.refresh_token:
        return None

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": integration.refresh_token,
        "grant_type": "refresh_token",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(TOKEN_URI, data=data, timeout=30)
            if resp.status_code == 200:
                td = resp.json()
                integration.access_token = td["access_token"]
                if td.get("refresh_token"):
                    integration.refresh_token = td["refresh_token"]
                integration.expires_at = datetime.now(timezone.utc) + timedelta(seconds=td.get("expires_in", 3600))
                integration.sync_error = None
                return td["access_token"]
            logger.error(f"Google token refresh failed: {resp.status_code}")
            integration.sync_error = f"Token refresh failed: {resp.status_code}"
            # Permanently invalid / revoked grant → require re-connect, keep data.
            body_txt = (resp.text or "").lower()
            if resp.status_code in (400, 401) and ("invalid_grant" in body_txt or "invalid_token" in body_txt):
                integration.needs_reconnect = True
            return None
    except Exception as e:
        logger.error(f"Google token refresh exception: {e}")
        integration.sync_error = str(e)
        return None


async def _get_valid_token(db: AsyncSession, integration: UserCalendarIntegration) -> Optional[str]:
    """Return a valid access token, refreshing if needed."""
    if integration.expires_at and integration.expires_at > datetime.now(timezone.utc) + timedelta(minutes=5):
        return integration.access_token
    new_token = await _refresh_access_token(integration)
    if new_token:
        await db.commit()
    return new_token


async def _sync_calendar_events(db: AsyncSession, integration: UserCalendarIntegration) -> int:
    """Pull events from primary Google calendar into ``availability_blocks`` (source='google')."""
    token = await _get_valid_token(db, integration)
    if not token:
        integration.sync_error = "Nepodařilo se obnovit token"
        await db.commit()
        raise Exception("Token refresh failed")

    # Window: max(180d, max booking horizon + 60d) — same logic as Outlook.
    sync_days = 180
    try:
        result = await db.execute(
            select(Program.max_days_before_booking).where(and_(
                Program.institution_id == integration.institution_id,
                Program.status == 'active',
            ))
        )
        max_values = [row[0] for row in result.fetchall() if row[0] is not None]
        if max_values:
            sync_days = max(max(max_values) + 60, 180)
    except Exception as e:
        logger.warning(f"Could not determine Google sync window, using {sync_days}d: {e}")

    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=sync_days)
    headers = {"Authorization": f"Bearer {token}"}
    base_params = {
        "timeMin": now.isoformat(),
        "timeMax": end_date.isoformat(),
        "singleEvents": "true",     # expand recurring instances
        "orderBy": "startTime",
        "maxResults": 250,
        "showDeleted": "false",
    }

    all_events = []
    page_token = None
    try:
        async with httpx.AsyncClient() as client:
            while True:
                params = dict(base_params)
                if page_token:
                    params["pageToken"] = page_token
                resp = await client.get(CALENDAR_EVENTS_URI, headers=headers, params=params, timeout=30)
                if resp.status_code != 200:
                    error_msg = f"Google Calendar API error {resp.status_code}: {resp.text[:500]}"
                    logger.error(error_msg)
                    integration.sync_error = error_msg
                    await db.commit()
                    raise Exception(error_msg)
                data = resp.json()
                all_events.extend(data.get("items", []))
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
    except httpx.HTTPError as e:
        integration.sync_error = str(e)
        await db.commit()
        raise

    user_uuid = integration.user_id
    inst_uuid = integration.institution_id

    result = await db.execute(
        select(AvailabilityBlock).where(and_(
            AvailabilityBlock.user_id == user_uuid,
            AvailabilityBlock.source == SOURCE,
        ))
    )
    existing = {b.external_event_id: b for b in result.scalars().all()}

    synced_ids: set[str] = set()
    count = 0
    for ev in all_events:
        ev_id = ev.get("id")
        if not ev_id:
            continue
        # Google event ``transparency`` == 'transparent' means "show as free".
        if ev.get("transparency") == "transparent":
            continue
        if ev.get("status") == "cancelled":
            continue
        # Loop prevention: never import an event that Budeživo itself exported.
        if is_budezivo_event(ev):
            continue

        title = ev.get("summary") or "Google událost"
        start_obj = ev.get("start") or {}
        end_obj = ev.get("end") or {}

        # Skip pure all-day events (only date, no dateTime) — these don't block
        # specific time slots. We could expand to all-day blockers later.
        start_str = start_obj.get("dateTime")
        end_str = end_obj.get("dateTime")
        if not start_str or not end_str:
            continue

        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        except (ValueError, IndexError):
            continue

        synced_ids.add(ev_id)

        if ev_id in existing:
            block = existing[ev_id]
            block.start_time = start_dt
            block.end_time = end_dt
            block.title = title
            block.updated_at = datetime.now(timezone.utc)
        else:
            db.add(AvailabilityBlock(
                user_id=user_uuid,
                institution_id=inst_uuid,
                start_time=start_dt,
                end_time=end_dt,
                source=SOURCE,
                external_event_id=ev_id,
                title=title,
                override=False,
            ))
        count += 1

    # Drop stale events (unless overridden by an admin).
    for ext_id, block in existing.items():
        if ext_id not in synced_ids and not block.override:
            await db.delete(block)

    integration.last_sync_at = datetime.now(timezone.utc)
    integration.sync_error = None
    integration.updated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"Synced {count} Google events for user {user_uuid}")
    return count


def _admin_base_url() -> str:
    return os.environ.get("FRONTEND_URL", "https://www.budezivo.cz").rstrip("/")


async def _create_google_event(token: str, body: dict) -> Optional[str]:
    """Create a Google event; return its id or None on failure."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                CALENDAR_EVENTS_URI,
                headers={"Authorization": f"Bearer {token}"},
                json=body,
                timeout=30,
            )
            if resp.status_code in (200, 201):
                return resp.json().get("id")
            logger.error(f"Google event create failed: {resp.status_code}")
            return None
    except Exception as e:
        logger.error(f"Google event create exception: {type(e).__name__}")
        return None


async def _patch_google_event(token: str, event_id: str, body: dict) -> bool:
    """Update a Budeživo-owned Google event. Returns True on success."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{CALENDAR_EVENTS_URI}/{event_id}",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
                timeout=30,
            )
            if resp.status_code == 200:
                return True
            # Event vanished (deleted by user) → treat as needing recreation.
            if resp.status_code in (404, 410):
                return False
            logger.error(f"Google event patch failed: {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"Google event patch exception: {type(e).__name__}")
        return False


async def _delete_google_event(token: str, event_id: str) -> bool:
    """Delete a Budeživo-owned Google event. 404/410 counts as already gone."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{CALENDAR_EVENTS_URI}/{event_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            return resp.status_code in (200, 204, 404, 410)
    except Exception as e:
        logger.error(f"Google event delete exception: {type(e).__name__}")
        return False


async def _export_reservations(db: AsyncSession, integration: UserCalendarIntegration) -> dict:
    """Reconcile the user's assigned reservations with their Google calendar.

    Idempotent: creates missing events, updates changed ones, deletes events for
    reservations the user is no longer assigned to / that were cancelled. Only
    events tracked in ``calendar_event_exports`` (Budeživo-owned) are touched.
    """
    stats = {"created": 0, "updated": 0, "deleted": 0, "errors": 0}
    if not integration.export_enabled:
        return stats
    if not has_events_scope(integration.granted_scopes):
        integration.needs_reconnect = True
        await db.commit()
        return stats

    token = await _get_valid_token(db, integration)
    if not token:
        await db.commit()
        return stats

    user_id = str(integration.user_id)
    inst_id = integration.institution_id
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    res_rows = (await db.execute(
        select(Reservation).where(and_(
            Reservation.institution_id == inst_id,
            Reservation.date >= today,
            Reservation.deleted_at.is_(None),
            Reservation.status.notin_(list(CANCELLED_STATUSES)),
        ))
    )).scalars().all()
    assigned = [r for r in res_rows if user_id in reservation_assigned_user_ids(r)]
    assigned_ids = {str(r.id) for r in assigned}

    links = (await db.execute(
        select(CalendarEventExport).where(and_(
            CalendarEventExport.user_id == integration.user_id,
            CalendarEventExport.provider == PROVIDER,
        ))
    )).scalars().all()
    link_by_booking = {str(l.booking_id): l for l in links}

    prog_ids = {r.program_id for r in assigned}
    programs = {}
    if prog_ids:
        programs = {p.id: p for p in (await db.execute(
            select(Program).where(Program.id.in_(prog_ids))
        )).scalars().all()}
    room_ids = {programs[r.program_id].room_id for r in assigned
                if programs.get(r.program_id) and programs[r.program_id].room_id}
    rooms = {}
    if room_ids:
        rooms = {rm.id: rm.name for rm in (await db.execute(
            select(Room).where(Room.id.in_(room_ids))
        )).scalars().all()}
    inst_name = (await db.execute(
        select(Institution.name).where(Institution.id == inst_id)
    )).scalar_one_or_none() or ""
    admin_base = _admin_base_url()

    for r in assigned:
        prog = programs.get(r.program_id)
        body = build_export_event_body(
            booking_id=str(r.id),
            institution_id=str(inst_id),
            user_id=user_id,
            program_name=(prog.name_cs or prog.name_en) if prog else "Program",
            status=r.status,
            date_str=r.date,
            time_block=r.time_block,
            duration=prog.duration if prog else None,
            institution_name=inst_name,
            room_name=rooms.get(prog.room_id) if prog and prog.room_id else None,
            school_name=r.school_name,
            group_type=r.group_type,
            num_students=r.num_students,
            admin_base_url=admin_base,
        )
        if not body:
            continue
        link = link_by_booking.get(str(r.id))
        try:
            if link and link.google_event_id:
                if await _patch_google_event(token, link.google_event_id, body):
                    link.sync_status = "synced"
                    link.sync_error = None
                    link.last_synced_at = now
                    stats["updated"] += 1
                else:
                    # Event gone → recreate.
                    ev_id = await _create_google_event(token, body)
                    if ev_id:
                        link.google_event_id = ev_id
                        link.sync_status = "synced"
                        link.last_synced_at = now
                        stats["created"] += 1
                    else:
                        link.sync_status = "error"
                        stats["errors"] += 1
            else:
                ev_id = await _create_google_event(token, body)
                if ev_id:
                    if link:
                        link.google_event_id = ev_id
                        link.sync_status = "synced"
                        link.last_synced_at = now
                    else:
                        db.add(CalendarEventExport(
                            institution_id=inst_id,
                            user_id=integration.user_id,
                            booking_id=r.id,
                            provider=PROVIDER,
                            google_calendar_id="primary",
                            google_event_id=ev_id,
                            sync_status="synced",
                            last_synced_at=now,
                        ))
                    stats["created"] += 1
                else:
                    stats["errors"] += 1
        except Exception as e:
            logger.error(f"Export sync error booking {r.id}: {type(e).__name__}")
            stats["errors"] += 1

    # Remove events for reservations no longer assigned / cancelled.
    for booking_id, link in link_by_booking.items():
        if booking_id not in assigned_ids:
            if link.google_event_id and not await _delete_google_event(token, link.google_event_id):
                stats["errors"] += 1
            else:
                stats["deleted"] += 1
            await db.delete(link)

    await db.commit()
    return stats


async def _full_sync(db: AsyncSession, integration: UserCalendarIntegration) -> dict:
    """Run import (Google→Budeživo) and export (Budeživo→Google) per the user's flags."""
    stats = {"imported": 0, "created": 0, "updated": 0, "deleted": 0, "errors": 0}
    if integration.import_enabled:
        try:
            stats["imported"] = await _sync_calendar_events(db, integration)
        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Google import failed for user {integration.user_id}: {type(e).__name__}")
    if integration.export_enabled:
        try:
            ex = await _export_reservations(db, integration)
            stats["created"] = ex["created"]
            stats["updated"] = ex["updated"]
            stats["deleted"] = ex["deleted"]
            stats["errors"] += ex["errors"]
        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Google export failed for user {integration.user_id}: {type(e).__name__}")
    integration.last_sync_at = datetime.now(timezone.utc)
    await db.commit()
    return stats


def _block_to_dict(block: AvailabilityBlock) -> dict:
    return {
        "id": str(block.id),
        "user_id": str(block.user_id),
        "start_time": block.start_time.isoformat() if block.start_time else None,
        "end_time": block.end_time.isoformat() if block.end_time else None,
        "source": block.source,
        "external_event_id": block.external_event_id,
        "title": block.title,
        "override": block.override,
    }


def _close_popup_html(error: Optional[str]) -> HTMLResponse:
    """Return HTML that postMessages the parent window then closes the popup.

    If the OAuth flow was opened in a full tab (no ``window.opener``), the
    page falls back to a friendly success screen with a manual close button
    instead of leaving the user stuck on a raw callback URL.
    """
    origin = os.environ.get(
        "FRONTEND_URL",
        os.environ.get("CORS_ORIGINS", "").split(",")[0]
        if os.environ.get("CORS_ORIGINS") else "*",
    )
    if error:
        safe = (error or "").replace("\\", "\\\\").replace('"', '\\"')
        message_type = "google_error"
        body_text = f"Chyba: {error}"
        post_payload = f'{{type:"{message_type}",error:"{safe}"}}'
        emoji = "⚠️"
        title = "Připojení se nezdařilo"
        sub = error
    else:
        message_type = "google_connected"
        body_text = "Připojeno!"
        post_payload = f'{{type:"{message_type}"}}'
        emoji = "✅"
        title = "Google kalendář propojen"
        sub = "Toto okno můžete zavřít a vrátit se do aplikace."

    script = (
        f"if (window.opener) {{"
        f'  window.opener.postMessage({post_payload}, "{origin}");'
        f"  window.close();"
        f"}}"
    )
    html = f"""<!DOCTYPE html>
<html lang=\"cs\">
<head>
  <meta charset=\"utf-8\"/>
  <title>{title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background:#f8fafc; color:#0f172a; margin:0; min-height:100vh;
            display:flex; align-items:center; justify-content:center; padding:24px; }}
    .card {{ max-width:480px; background:white; border:1px solid #e2e8f0;
             border-radius:16px; padding:48px 32px; text-align:center;
             box-shadow:0 4px 14px rgba(15,23,42,.06); }}
    .emoji {{ font-size:56px; line-height:1; margin-bottom:16px; }}
    h1 {{ font-size:22px; font-weight:600; margin:0 0 8px; }}
    p  {{ color:#475569; font-size:15px; line-height:1.5; margin:0 0 24px; }}
    button {{ background:#16a34a; color:white; border:none; padding:10px 24px;
              border-radius:8px; font-size:14px; font-weight:500; cursor:pointer; }}
    button:hover {{ background:#15803d; }}
  </style>
</head>
<body>
  <div class=\"card\">
    <div class=\"emoji\">{emoji}</div>
    <h1>{title}</h1>
    <p>{sub}</p>
    <button onclick=\"window.close()\">Zavřít okno</button>
  </div>
  <script>{script}</script>
</body>
</html>"""
    return HTMLResponse(content=html)


# ── Background Sync (called from scheduler) ─────────────────────────


async def sync_all_integrations() -> None:
    """Sync all active Google integrations. Called from APScheduler every 5 min."""
    if not _is_configured():
        # No env keys → nothing to do; avoid noisy DB hits.
        return

    from database.supabase import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserCalendarIntegration).where(and_(
                UserCalendarIntegration.is_active == True,
                UserCalendarIntegration.provider == PROVIDER,
                UserCalendarIntegration.auto_sync_enabled == True,
            ))
        )
        integrations = result.scalars().all()

        for integration in integrations:
            # Don't loop on a permanently invalid grant — wait for re-connect.
            if integration.needs_reconnect:
                continue
            # A user with everything off has nothing to auto-sync.
            if not integration.import_enabled and not integration.export_enabled:
                continue
            try:
                await _full_sync(db, integration)
                logger.info(f"Background Google sync completed for user {integration.user_id}")
            except Exception as e:
                # One user's failure must not stop the others.
                logger.error(f"Background Google sync failed for user {integration.user_id}: {type(e).__name__}")
