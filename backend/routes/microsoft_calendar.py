"""
Microsoft Outlook Calendar Integration.
OAuth2 flow, token management, calendar sync, availability blocks.
"""
import logging
import os
import uuid
import secrets
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
from database.models import UserCalendarIntegration, AvailabilityBlock

router = APIRouter(prefix="/microsoft-calendar", tags=["Microsoft Calendar"])
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────

CLIENT_ID = os.environ.get("MICROSOFT_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET", "")
TENANT_ID = os.environ.get("MICROSOFT_TENANT_ID", "")
REDIRECT_URI = os.environ.get("MICROSOFT_REDIRECT_URI", "")

AUTHORITY = f"https://login.microsoftonline.com/common"
SCOPES = ["Calendars.Read", "User.Read", "offline_access"]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# In-memory store for OAuth state → user_id mapping (simple for single-instance)
_oauth_states: dict = {}


def _get_redirect_uri(request: Request) -> str:
    """Build redirect URI from the current request's public-facing host."""
    # Prefer X-Forwarded-Host (set by reverse proxy/ingress)
    fwd_host = request.headers.get("x-forwarded-host")
    fwd_proto = request.headers.get("x-forwarded-proto", "https")
    if fwd_host:
        return f"{fwd_proto}://{fwd_host}/api/microsoft-calendar/callback"
    
    # Fallback: use Origin/Referer header
    origin = request.headers.get("origin") or request.headers.get("referer")
    if origin:
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return f"{base}/api/microsoft-calendar/callback"
    
    return REDIRECT_URI or "https://budezivo.cz/api/microsoft-calendar/callback"


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
):
    """
    Step 1: Redirect user to Microsoft login.
    Frontend opens this URL in a new window/popup.
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Microsoft OAuth není nakonfigurován")

    redirect = _get_redirect_uri(request)

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "user_id": current_user["user_id"],
        "institution_id": current_user["institution_id"],
        "redirect_uri": redirect,
    }

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
        return _close_popup_html(f"Chyba: {error_description or error}")

    if not code or not state:
        return _close_popup_html("Chybí autorizační kód")

    user_data = _oauth_states.pop(state, None)
    if not user_data:
        return _close_popup_html("Neplatný stav relace. Zkuste to znovu.")

    # Exchange code for tokens — use redirect_uri matching the one used in /connect
    redirect = user_data.get("redirect_uri", REDIRECT_URI)
    try:
        token_data = await _exchange_code_for_tokens(code, redirect)
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        return _close_popup_html(f"Nepodařilo se získat token: {e}")

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
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
            is_active=True,
        )
        db.add(integration)

    await db.commit()

    # Trigger initial sync
    try:
        await _sync_calendar_events(db, integration)
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

    return {
        "connected": True,
        "microsoft_user_id": integration.microsoft_user_id,
        "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
        "sync_error": integration.sync_error,
        "expires_at": integration.expires_at.isoformat() if integration.expires_at else None,
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
        count = await _sync_calendar_events(db, integration)
        return {"message": f"Synchronizováno {count} událostí z Outlooku", "synced_count": count}
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

    return [_block_to_dict(b) for b in blocks]


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
        "block": _block_to_dict(block),
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
    Fetches next 30 days of events and upserts blocks.
    """
    token = await _get_valid_token(db, integration)
    if not token:
        integration.sync_error = "Nepodařilo se obnovit token"
        await db.commit()
        raise Exception("Token refresh failed")

    # Fetch events for next 30 days
    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=30)

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


def _close_popup_html(error: Optional[str]) -> "HTMLResponse":
    """Return HTML that communicates result to parent window and closes popup."""
    from fastapi.responses import HTMLResponse
    if error:
        script = f'window.opener && window.opener.postMessage({{type:"outlook_error",error:"{error}"}}, "*"); window.close();'
    else:
        script = 'window.opener && window.opener.postMessage({type:"outlook_connected"}, "*"); window.close();'
    html = f"""<!DOCTYPE html><html><body>
    <p>{"Chyba: " + error if error else "Připojeno! Toto okno se zavře..."}</p>
    <script>{script}</script>
    </body></html>"""
    return HTMLResponse(content=html)


# ── Background Sync (called from scheduler) ─────────────────────────


async def sync_all_integrations():
    """Sync all active Microsoft integrations. Called from APScheduler."""
    from database.supabase import async_session_maker
    async with async_session_maker() as db:
        result = await db.execute(
            select(UserCalendarIntegration).where(
                UserCalendarIntegration.is_active == True
            )
        )
        integrations = result.scalars().all()

        for integration in integrations:
            try:
                await _sync_calendar_events(db, integration)
                logger.info(f"Background sync completed for user {integration.user_id}")
            except Exception as e:
                logger.error(f"Background sync failed for user {integration.user_id}: {e}")
