"""
Microsoft Outlook Calendar Integration.
OAuth2 flow, token management, calendar sync, availability blocks.
"""
import logging
import os
import uuid
import secrets
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import msal
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from core.security import get_current_user
from database.supabase import get_db
from database.models import (
    UserCalendarIntegration, AvailabilityBlock, OAuthState, Program,
    Reservation, Room, Institution, CalendarEventExport, User,
)
from services.plan_service import require_feature
from core.permissions import require_roles, CALENDAR_PERSONAL_ROLES
from services.google_calendar_helpers import (
    build_export_event_body, reservation_assigned_user_ids,
)

_CALENDAR_ROLE_MSG = "Vaše role nemá přístup ke kalendářovým integracím."

router = APIRouter(
    prefix="/microsoft-calendar",
    tags=["Microsoft Calendar"],
    dependencies=[
        Depends(require_feature("outlook_sync")),
        Depends(require_roles(CALENDAR_PERSONAL_ROLES, _CALENDAR_ROLE_MSG)),
    ],
)
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────

CLIENT_ID = os.environ.get("MICROSOFT_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET", "")
TENANT_ID = os.environ.get("MICROSOFT_TENANT_ID", "")
REDIRECT_URI = os.environ.get("MICROSOFT_REDIRECT_URI", "")

AUTHORITY = "https://login.microsoftonline.com/common"
# Calendars.ReadWrite is required to EXPORT reservations (create/update/delete our events).
SCOPES = ["Calendars.ReadWrite", "User.Read", "offline_access"]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
PROVIDER = "microsoft"
CANCELLED_STATUSES = {"cancelled", "canceled", "rejected", "declined"}


def _has_write_scope(granted_scopes: Optional[str]) -> bool:
    """Whether the integration was granted calendar write access."""
    if not granted_scopes:
        return False
    return "calendars.readwrite" in granted_scopes.lower()

OAUTH_STATE_TTL_MINUTES = 10


def _get_redirect_uri(request: Request) -> str:
    """Return the OAuth redirect URI.

    The explicit env value MICROSOFT_REDIRECT_URI is authoritative: it must match
    the Microsoft Entra app registration EXACTLY and must be identical for both
    /connect and /callback. We never derive it from the frontend Origin/Referer
    (that would yield the frontend host, e.g. budezivo.cz, which does not match
    the API host api.budezivo.cz registered in Entra).
    """
    if REDIRECT_URI:
        return REDIRECT_URI
    # Dev/preview fallback: derive from the API's OWN public host.
    fwd_host = request.headers.get("x-forwarded-host")
    fwd_proto = request.headers.get("x-forwarded-proto", "https")
    if fwd_host:
        return f"{fwd_proto}://{fwd_host}/api/microsoft-calendar/callback"
    return f"{request.url.scheme}://{request.url.netloc}/api/microsoft-calendar/callback"


def _get_msal_app():
    return msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )


# ── OAuth Flow ──────────────────────────────────────────────────────


@router.get("/connect")
async def connect_outlook(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 1: Redirect user to Microsoft login.
    Frontend opens this URL in a new window/popup.
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Microsoft OAuth není nakonfigurován")

    redirect = _get_redirect_uri(request)

    state = secrets.token_urlsafe(32)

    # Persist state in DB (replaces in-memory dict)
    oauth_state = OAuthState(
        state=state,
        user_id=uuid.UUID(current_user["user_id"]),
        institution_id=uuid.UUID(current_user["institution_id"]),
        redirect_uri=redirect,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OAUTH_STATE_TTL_MINUTES),
    )
    db.add(oauth_state)
    await db.commit()

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect,
        "response_mode": "query",
        "scope": " ".join(SCOPES),
        "state": state,
        "prompt": "consent",
    }
    from urllib.parse import urlencode
    auth_url = f"{AUTHORITY}/oauth2/v2.0/authorize?{urlencode(params)}"
    return {"auth_url": auth_url}


@router.get("/callback")
async def oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: Microsoft redirects here with authorization code.
    Exchange code for tokens, store in DB, close popup.
    """
    if error:
        logger.error(f"OAuth error: {error} - {error_description}")
        if error == "access_denied":
            return _close_popup_html("Souhlas s přístupem ke kalendáři byl odmítnut.")
        return _close_popup_html(error_description or error)

    if not code or not state:
        return _close_popup_html("Chybí autorizační kód")

    # Look up state from DB (replaces in-memory dict)
    result = await db.execute(
        select(OAuthState).where(OAuthState.state == state)
    )
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
    # Delete used state
    await db.delete(oauth_row)
    await db.commit()

    # Exchange code for tokens — use redirect_uri matching the one used in /connect
    redirect = user_data.get("redirect_uri", REDIRECT_URI)
    try:
        token_data = await _exchange_code_for_tokens(code, redirect)
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        return _close_popup_html(f"Nepodařilo se získat token: {e}")

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    granted_scopes = token_data.get("scope")
    expires_in = token_data.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Get Microsoft user profile
    ms_user_id = None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_BASE}/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            if resp.status_code == 200:
                profile = resp.json()
                ms_user_id = profile.get("id")
    except Exception as e:
        logger.warning(f"Failed to get MS profile: {e}")

    # Upsert integration record
    user_uuid = uuid.UUID(user_data["user_id"])
    inst_uuid = uuid.UUID(user_data["institution_id"])

    result = await db.execute(
        select(UserCalendarIntegration).where(and_(
            UserCalendarIntegration.user_id == user_uuid,
            UserCalendarIntegration.provider == "microsoft",
        ))
    )
    integration = result.scalar_one_or_none()

    if integration:
        integration.access_token = access_token
        integration.refresh_token = refresh_token
        integration.expires_at = expires_at
        integration.microsoft_user_id = ms_user_id
        integration.granted_scopes = granted_scopes
        integration.needs_reconnect = not _has_write_scope(granted_scopes)
        integration.is_active = True
        integration.sync_error = None
        integration.updated_at = datetime.now(timezone.utc)
    else:
        integration = UserCalendarIntegration(
            user_id=user_uuid,
            institution_id=inst_uuid,
            provider="microsoft",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            microsoft_user_id=ms_user_id,
            granted_scopes=granted_scopes,
            needs_reconnect=not _has_write_scope(granted_scopes),
            is_active=True,
        )
        db.add(integration)

    await db.commit()

    # Trigger initial sync (import + export per flags)
    try:
        await _full_sync_ms(db, integration)
    except Exception as e:
        logger.error(f"Initial sync failed: {e}")

    return _close_popup_html(None)  # Success


@router.get("/status")
async def get_connection_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if the current user has an active Outlook connection."""
    user_uuid = uuid.UUID(current_user["user_id"])
    result = await db.execute(
        select(UserCalendarIntegration).where(and_(
            UserCalendarIntegration.user_id == user_uuid,
            UserCalendarIntegration.provider == "microsoft",
        ))
    )
    integration = result.scalar_one_or_none()

    if not integration or not integration.is_active:
        return {"connected": False}

    has_write = _has_write_scope(integration.granted_scopes)
    role = current_user.get("role")
    export_scope = "institution" if role in ("admin", "spravce") else "assigned"
    return {
        "connected": True,
        "microsoft_user_id": integration.microsoft_user_id,
        "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
        "sync_error": integration.sync_error,
        "expires_at": integration.expires_at.isoformat() if integration.expires_at else None,
        "import_enabled": integration.import_enabled,
        "export_enabled": integration.export_enabled,
        "has_write_scope": has_write,
        # Export requires write scope — old connections must reconnect first.
        "needs_reconnect": integration.needs_reconnect or not has_write,
        "export_scope": export_scope,
    }


@router.put("/settings")
async def update_ms_settings(
    body: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle import (personal events → blocks) and export (reservations → Outlook)."""
    user_uuid = uuid.UUID(current_user["user_id"])
    integration = (await db.execute(
        select(UserCalendarIntegration).where(and_(
            UserCalendarIntegration.user_id == user_uuid,
            UserCalendarIntegration.provider == "microsoft",
        ))
    )).scalar_one_or_none()
    if not integration or not integration.is_active:
        raise HTTPException(status_code=404, detail="Outlook není připojen")

    if "import_enabled" in body:
        integration.import_enabled = bool(body["import_enabled"])
    if "export_enabled" in body:
        want_export = bool(body["export_enabled"])
        if want_export and not _has_write_scope(integration.granted_scopes):
            # No write permission → require reconnect, never silently enable.
            integration.needs_reconnect = True
            await db.commit()
            raise HTTPException(
                status_code=403,
                detail="Pro export rezervací je potřeba Outlook znovu připojit (chybí oprávnění k zápisu do kalendáře).",
            )
        integration.export_enabled = want_export
    integration.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(integration)
    return {
        "import_enabled": integration.import_enabled,
        "export_enabled": integration.export_enabled,
    }


@router.post("/disconnect")
async def disconnect_outlook(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove Outlook connection and all synced blocks."""
    user_uuid = uuid.UUID(current_user["user_id"])

    # Delete availability blocks from outlook
    await db.execute(
        delete(AvailabilityBlock).where(and_(
            AvailabilityBlock.user_id == user_uuid,
            AvailabilityBlock.source == "outlook",
        ))
    )

    # Delete integration
    await db.execute(
        delete(UserCalendarIntegration).where(and_(
            UserCalendarIntegration.user_id == user_uuid,
            UserCalendarIntegration.provider == "microsoft",
        ))
    )

    await db.commit()
    return {"message": "Outlook odpojen, synchronizované bloky smazány"}


@router.post("/sync")
async def trigger_sync(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger calendar sync."""
    user_uuid = uuid.UUID(current_user["user_id"])
    result = await db.execute(
        select(UserCalendarIntegration).where(and_(
            UserCalendarIntegration.user_id == user_uuid,
            UserCalendarIntegration.provider == "microsoft",
            UserCalendarIntegration.is_active == True,
        ))
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Outlook není připojen")

    try:
        result = await _full_sync_ms(db, integration)
        return {"message": "Synchronizace dokončena", **result}
    except Exception as e:
        logger.error(f"Manual sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Synchronizace selhala: {str(e)}")


# ── Availability Blocks API ─────────────────────────────────────────


@router.get("/blocks")
async def list_blocks(
    user_id: Optional[str] = Query(None, description="Filter by specific user"),
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List availability blocks (outlook + manual) for the institution."""
    inst_uuid = uuid.UUID(current_user["institution_id"])
    conditions = [AvailabilityBlock.institution_id == inst_uuid]

    if user_id:
        conditions.append(AvailabilityBlock.user_id == uuid.UUID(user_id))

    if start:
        conditions.append(AvailabilityBlock.end_time >= datetime.fromisoformat(start).replace(tzinfo=timezone.utc))
    if end:
        conditions.append(AvailabilityBlock.start_time <= datetime.fromisoformat(f"{end}T23:59:59").replace(tzinfo=timezone.utc))

    result = await db.execute(
        select(AvailabilityBlock)
        .where(and_(*conditions))
        .order_by(AvailabilityBlock.start_time)
    )
    blocks = result.scalars().all()

    return [
        _block_to_dict(b, viewer_user_id=current_user["user_id"])
        for b in blocks
    ]


@router.post("/blocks/{block_id}/override")
async def toggle_override(
    block_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle override on an Outlook block (allow/disallow bookings)."""
    inst_uuid = uuid.UUID(current_user["institution_id"])
    result = await db.execute(
        select(AvailabilityBlock).where(and_(
            AvailabilityBlock.id == uuid.UUID(block_id),
            AvailabilityBlock.institution_id == inst_uuid,
        ))
    )
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Blok nenalezen")

    block.override = not block.override
    block.updated_at = datetime.now(timezone.utc)
    await db.commit()

    action = "povoleny" if block.override else "blokovány"
    return {
        "message": f"Rezervace {action} v tomto čase",
        "block": _block_to_dict(block, viewer_user_id=current_user["user_id"]),
    }


# ── Internal Helpers ────────────────────────────────────────────────


async def _exchange_code_for_tokens(code: str, redirect_uri: str = None) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    token_url = f"{AUTHORITY}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri or REDIRECT_URI,
        "grant_type": "authorization_code",
        "scope": " ".join(SCOPES),
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=data, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"Token endpoint returned {resp.status_code}: {resp.text}")
        return resp.json()


async def _refresh_access_token(integration: UserCalendarIntegration) -> Optional[str]:
    """Refresh access token using refresh_token. Returns new access_token or None."""
    if not integration.refresh_token:
        return None

    token_url = f"{AUTHORITY}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": integration.refresh_token,
        "grant_type": "refresh_token",
        "scope": " ".join(SCOPES),
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=data, timeout=30)
            if resp.status_code == 200:
                token_data = resp.json()
                integration.access_token = token_data["access_token"]
                if token_data.get("refresh_token"):
                    integration.refresh_token = token_data["refresh_token"]
                integration.expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600))
                integration.sync_error = None
                return token_data["access_token"]
            else:
                logger.error(f"Token refresh failed: {resp.status_code} {resp.text}")
                integration.sync_error = f"Token refresh failed: {resp.status_code}"
                return None
    except Exception as e:
        logger.error(f"Token refresh exception: {e}")
        integration.sync_error = str(e)
        return None


async def _get_valid_token(db: AsyncSession, integration: UserCalendarIntegration) -> Optional[str]:
    """Get a valid access token, refreshing if needed."""
    if integration.expires_at and integration.expires_at > datetime.now(timezone.utc) + timedelta(minutes=5):
        return integration.access_token

    # Token expired or expiring soon — refresh
    new_token = await _refresh_access_token(integration)
    if new_token:
        await db.commit()
    return new_token


async def _sync_calendar_events(db: AsyncSession, integration: UserCalendarIntegration) -> int:
    """
    Sync Outlook calendar events into availability_blocks.
    Fetches events for a window based on the institution's max booking horizon + 60 day buffer.
    Default: 180 days. Adapts dynamically to max_days_before_booking setting.
    """
    token = await _get_valid_token(db, integration)
    if not token:
        integration.sync_error = "Nepodařilo se obnovit token"
        await db.commit()
        raise Exception("Token refresh failed")

    # Determine sync window from institution's max_days_before_booking
    sync_days = 180  # default
    try:
        result = await db.execute(
            select(Program.max_days_before_booking).where(
                and_(
                    Program.institution_id == integration.institution_id,
                    Program.status == 'active'
                )
            )
        )
        max_values = [row[0] for row in result.fetchall() if row[0] is not None]
        if max_values:
            sync_days = max(max_values) + 60  # max booking window + 60 day buffer
            sync_days = max(sync_days, 180)   # at least 180 days
    except Exception as e:
        logger.warning(f"Could not determine sync window, using default {sync_days}d: {e}")

    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=sync_days)
    logger.info(f"Outlook sync window: {sync_days} days for institution {integration.institution_id}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Prefer": 'outlook.timezone="Europe/Prague"',
    }
    params = {
        "startDateTime": now.isoformat(),
        "endDateTime": end_date.isoformat(),
        "$top": 250,
        "$select": "id,subject,start,end,showAs,isAllDay",
    }

    all_events = []
    url = f"{GRAPH_BASE}/me/calendarView"

    try:
        async with httpx.AsyncClient() as client:
            while url:
                resp = await client.get(url, headers=headers, params=params, timeout=30)
                if resp.status_code != 200:
                    error_body = resp.text
                    error_msg = f"Graph API error {resp.status_code}: {error_body[:500]}"
                    logger.error(error_msg)
                    
                    # If 401, try to decode token scopes for debugging
                    try:
                        import base64, json as _json
                        token_parts = token.split(".")
                        if len(token_parts) >= 2:
                            padded = token_parts[1] + "=" * (4 - len(token_parts[1]) % 4)
                            payload = _json.loads(base64.b64decode(padded))
                            logger.error(f"Token scopes (scp): {payload.get('scp', 'NONE')}")
                            logger.error(f"Token roles: {payload.get('roles', 'NONE')}")
                            logger.error(f"Token aud: {payload.get('aud', 'NONE')}")
                    except Exception as te:
                        logger.error(f"Could not decode token: {te}")
                    
                    # If calendarView fails, try /me/events as fallback
                    if "/calendarView" in url and resp.status_code == 401:
                        logger.info("Trying /me/events as fallback...")
                        fallback_url = f"{GRAPH_BASE}/me/events"
                        fallback_params = {
                            "$top": 250,
                            "$select": "id,subject,start,end,showAs,isAllDay",
                            "$filter": f"start/dateTime ge '{now.strftime('%Y-%m-%dT%H:%M:%S')}'",
                            "$orderby": "start/dateTime",
                        }
                        resp2 = await client.get(fallback_url, headers=headers, params=fallback_params, timeout=30)
                        if resp2.status_code == 200:
                            logger.info("Fallback /me/events succeeded!")
                            all_events.extend(resp2.json().get("value", []))
                            url = None
                            continue
                        else:
                            logger.error(f"Fallback /me/events also failed: {resp2.status_code} {resp2.text[:300]}")
                    
                    integration.sync_error = error_msg
                    await db.commit()
                    raise Exception(error_msg)

                data = resp.json()
                all_events.extend(data.get("value", []))
                url = data.get("@odata.nextLink")
                params = {}  # nextLink already contains params
    except httpx.HTTPError as e:
        integration.sync_error = str(e)
        await db.commit()
        raise

    user_uuid = integration.user_id
    inst_uuid = integration.institution_id

    # Get existing outlook blocks for this user
    result = await db.execute(
        select(AvailabilityBlock).where(and_(
            AvailabilityBlock.user_id == user_uuid,
            AvailabilityBlock.source == "outlook",
        ))
    )
    existing_blocks = {b.external_event_id: b for b in result.scalars().all()}

    synced_event_ids = set()
    count = 0

    for event in all_events:
        event_id = event.get("id")
        if not event_id:
            continue

        # Only sync events that block time (busy, oof, tentative)
        show_as = event.get("showAs", "busy")
        if show_as == "free":
            continue

        title = event.get("subject", "Outlook událost")
        start_str = event.get("start", {}).get("dateTime", "")
        end_str = event.get("end", {}).get("dateTime", "")

        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            # Ensure timezone aware
            if start_dt.tzinfo is None:
                import pytz
                prague = pytz.timezone("Europe/Prague")
                start_dt = prague.localize(start_dt)
                end_dt = prague.localize(end_dt)
        except (ValueError, IndexError):
            continue

        synced_event_ids.add(event_id)

        if event_id in existing_blocks:
            # Update existing block
            block = existing_blocks[event_id]
            block.start_time = start_dt
            block.end_time = end_dt
            block.title = title
            block.updated_at = datetime.now(timezone.utc)
            # Keep override as-is (user explicitly set it)
        else:
            # Create new block
            block = AvailabilityBlock(
                user_id=user_uuid,
                institution_id=inst_uuid,
                start_time=start_dt,
                end_time=end_dt,
                source="outlook",
                external_event_id=event_id,
                title=title,
                override=False,
            )
            db.add(block)
        count += 1

    # Delete blocks for events that no longer exist (unless override=True)
    for ext_id, block in existing_blocks.items():
        if ext_id not in synced_event_ids and not block.override:
            await db.delete(block)

    integration.last_sync_at = datetime.now(timezone.utc)
    integration.sync_error = None
    integration.updated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"Synced {count} Outlook events for user {user_uuid}")
    return count


# ── Reservation EXPORT (Budeživo → Outlook), Microsoft Graph write ──


def _graph_body_from_google(g: dict) -> dict:
    """Translate the shared Google export body into a Microsoft Graph event body."""
    return {
        "subject": g.get("summary", "Rezervace"),
        "body": {"contentType": "text", "content": g.get("description", "")},
        "start": g.get("start"),   # {dateTime, timeZone} — same shape as Graph
        "end": g.get("end"),
        "categories": ["Budeživo"],
    }


async def _graph_request(method: str, token: str, path: str, json_body=None):
    async with httpx.AsyncClient() as client:
        return await client.request(
            method, f"{GRAPH_BASE}{path}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=json_body, timeout=30,
        )


async def _export_reservations_ms(db: AsyncSession, integration: UserCalendarIntegration) -> dict:
    """Reconcile the owner's reservations with their Outlook calendar (idempotent).

    Creates missing events, updates changed ones, deletes events for reservations the
    user is no longer assigned to / that were cancelled. Only events we tracked in
    calendar_event_exports (Budeživo-owned) are ever touched — never personal events.
    Scope is derived from the OWNER's role in the DB (never trusted from the client).
    """
    stats = {"created": 0, "updated": 0, "deleted": 0, "errors": 0}
    if not integration.export_enabled:
        return stats
    if not _has_write_scope(integration.granted_scopes):
        integration.needs_reconnect = True
        await db.commit()
        return stats

    token = await _get_valid_token(db, integration)
    if not token:
        await db.commit()
        return stats

    user_id = str(integration.user_id)
    inst_id = integration.institution_id
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    owner_role = (await db.execute(
        select(User.role).where(User.id == integration.user_id)
    )).scalar_one_or_none()
    institution_scope = owner_role in ("admin", "spravce")

    res_rows = (await db.execute(
        select(Reservation).where(and_(
            Reservation.institution_id == inst_id,
            Reservation.date >= today,
            Reservation.deleted_at.is_(None),
            Reservation.status.notin_(list(CANCELLED_STATUSES)),
        ))
    )).scalars().all()
    assigned = res_rows if institution_scope else [r for r in res_rows if user_id in reservation_assigned_user_ids(r)]
    assigned_ids = {str(r.id) for r in assigned}

    links = (await db.execute(
        select(CalendarEventExport).where(and_(
            CalendarEventExport.user_id == integration.user_id,
            CalendarEventExport.provider == PROVIDER,
        ))
    )).scalars().all()
    link_by_booking = {str(l.booking_id): l for l in links}

    prog_ids = {r.program_id for r in assigned}
    programs = {p.id: p for p in (await db.execute(
        select(Program).where(Program.id.in_(prog_ids))
    )).scalars().all()} if prog_ids else {}
    room_ids = {programs[r.program_id].room_id for r in assigned
                if programs.get(r.program_id) and programs[r.program_id].room_id}
    rooms = {rm.id: rm.name for rm in (await db.execute(
        select(Room).where(Room.id.in_(room_ids))
    )).scalars().all()} if room_ids else {}
    inst_name = (await db.execute(
        select(Institution.name).where(Institution.id == inst_id)
    )).scalar_one_or_none() or ""
    admin_base = os.environ.get("FRONTEND_URL", "").rstrip("/")

    for r in assigned:
        prog = programs.get(r.program_id)
        g_body = build_export_event_body(
            booking_id=str(r.id), institution_id=str(inst_id), user_id=user_id,
            program_name=(prog.name_cs or prog.name_en) if prog else "Program",
            status=r.status, date_str=r.date, time_block=r.time_block,
            duration=prog.duration if prog else None, institution_name=inst_name,
            room_name=rooms.get(prog.room_id) if prog and prog.room_id else None,
            school_name=r.school_name, group_type=r.group_type,
            num_students=r.num_students, admin_base_url=admin_base,
        )
        if not g_body:
            continue
        body = _graph_body_from_google(g_body)
        link = link_by_booking.get(str(r.id))
        try:
            if link and link.external_event_id:
                resp = await _graph_request("PATCH", token, f"/me/events/{link.external_event_id}", body)
                if resp.status_code == 404:
                    resp = await _graph_request("POST", token, "/me/events", body)
                    if resp.status_code in (200, 201):
                        link.external_event_id = resp.json().get("id")
                        stats["created"] += 1
                    else:
                        stats["errors"] += 1
                        continue
                elif resp.status_code in (200, 201):
                    stats["updated"] += 1
                else:
                    stats["errors"] += 1
                    continue
                link.last_synced_at = datetime.now(timezone.utc)
            else:
                resp = await _graph_request("POST", token, "/me/events", body)
                if resp.status_code in (200, 201):
                    ev_id = resp.json().get("id")
                    if link:
                        link.external_event_id = ev_id
                        link.last_synced_at = datetime.now(timezone.utc)
                    else:
                        db.add(CalendarEventExport(
                            institution_id=inst_id, user_id=integration.user_id,
                            booking_id=r.id, provider=PROVIDER,
                            external_event_id=ev_id, last_synced_at=datetime.now(timezone.utc),
                        ))
                    stats["created"] += 1
                else:
                    stats["errors"] += 1
        except Exception as e:  # noqa: BLE001
            logger.error(f"MS export failed for reservation {r.id}: {type(e).__name__}")
            stats["errors"] += 1

    # Remove events for reservations no longer in scope / cancelled.
    for booking_id, link in link_by_booking.items():
        if booking_id in assigned_ids:
            continue
        try:
            if link.external_event_id:
                resp = await _graph_request("DELETE", token, f"/me/events/{link.external_event_id}")
                if resp.status_code not in (200, 204, 404):
                    stats["errors"] += 1
                    continue
            await db.delete(link)
            stats["deleted"] += 1
        except Exception as e:  # noqa: BLE001
            logger.error(f"MS export delete failed for booking {booking_id}: {type(e).__name__}")
            stats["errors"] += 1

    integration.last_sync_at = datetime.now(timezone.utc)
    await db.commit()
    return stats


async def _full_sync_ms(db: AsyncSession, integration: UserCalendarIntegration) -> dict:
    """Run import (personal events → blocks) and export (reservations → Outlook) per flags."""
    imported = 0
    if integration.import_enabled:
        imported = await _sync_calendar_events(db, integration)
    export_stats = await _export_reservations_ms(db, integration)
    return {"imported": imported, "export": export_stats}



def _block_to_dict(block: AvailabilityBlock, viewer_user_id: Optional[str] = None) -> dict:
    is_external = block.source in ("google", "outlook")
    is_owner = viewer_user_id is not None and str(block.user_id) == str(viewer_user_id)
    redact = is_external and not is_owner
    return {
        "id": str(block.id),
        "user_id": str(block.user_id),
        "start_time": block.start_time.isoformat() if block.start_time else None,
        "end_time": block.end_time.isoformat() if block.end_time else None,
        "source": block.source,
        "external_event_id": None if redact else block.external_event_id,
        "title": "Obsazeno – externí kalendář" if redact else block.title,
        "override": block.override,
    }


def _extract_aadsts(msg: Optional[str]) -> Optional[str]:
    if not msg:
        return None
    m = re.search(r"AADSTS\d+", msg)
    return m.group(0) if m else None


def _close_popup_html(error: Optional[str]) -> "HTMLResponse":
    """Return HTML that posts the result to the opener and closes the popup.

    Error detail is delivered via postMessage as JSON (safely escaped) — never
    interpolated raw into HTML/JS. Secrets/tokens/codes are never included here.
    """
    from fastapi.responses import HTMLResponse
    origin = os.environ.get("FRONTEND_URL") or (
        os.environ.get("CORS_ORIGINS", "").split(",")[0] if os.environ.get("CORS_ORIGINS") else "*"
    )
    if error:
        payload = {"type": "outlook_error", "error": error, "aadsts": _extract_aadsts(error)}
        visible = "Připojení Outlooku se nezdařilo. Toto okno se zavře…"
    else:
        payload = {"type": "outlook_connected"}
        visible = "Připojeno! Toto okno se zavře…"
    payload_json = json.dumps(payload)
    origin_json = json.dumps(origin)
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
    <p>{visible}</p>
    <script>
      try {{ window.opener && window.opener.postMessage({payload_json}, {origin_json}); }} catch (e) {{}}
      window.close();
    </script>
    </body></html>"""
    return HTMLResponse(content=html)


# ── Background Sync (called from scheduler) ─────────────────────────


async def sync_all_integrations():
    """Sync all active Microsoft integrations. Called from APScheduler."""
    from database.supabase import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserCalendarIntegration).where(and_(
                UserCalendarIntegration.is_active == True,
                UserCalendarIntegration.provider == "microsoft",
            ))
        )
        integrations = result.scalars().all()

        for integration in integrations:
            try:
                await _full_sync_ms(db, integration)
                logger.info(f"Background sync completed for user {integration.user_id}")
            except Exception as e:
                logger.error(f"Background sync failed for user {integration.user_id}: {e}")
