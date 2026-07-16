"""
Calendar export routes - ICS feed generation for Outlook/Google Calendar integration.
Generates .ics feeds for reservations (read-only export).
All ICS feeds require HMAC-signed tokens or JWT authentication.
"""
import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from icalendar import Calendar, Event, vText
import pytz

from database.supabase import get_db
from database.models import Reservation, Program, Institution, CalendarFeedToken, User
from core.security import get_current_user
import secrets
import uuid as _uuid

router = APIRouter(prefix="/calendar", tags=["Calendar"])
logger = logging.getLogger(__name__)

PRAGUE_TZ = pytz.timezone("Europe/Prague")

MANAGER_ROLES = {"admin", "spravce"}
LECTURER_ROLES = {"edukator", "lektor"}


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def _resolve_feed_scope(db: AsyncSession, current_user: dict, feed_type: str, entity_id: Optional[str]) -> str:
    """Verify OWNERSHIP + role permission and return the backend-decided scope.

    Knowing a UUID is never enough — everything is checked against the caller's
    institution and role. Raises 403/404 on any mismatch.
    """
    role = current_user.get("role")
    inst = current_user["institution_id"]

    if feed_type == "institution":
        if entity_id and entity_id != inst:
            raise HTTPException(status_code=403, detail="Přístup k feedu jiné instituce je zakázán")
        if role not in MANAGER_ROLES:
            raise HTTPException(status_code=403, detail="Institucionální feed smí vytvořit pouze správce")
        return "institution"

    if feed_type == "program":
        if not entity_id:
            raise HTTPException(status_code=400, detail="Chybí ID programu")
        prog = (await db.execute(
            select(Program).where(Program.id == _uuid.UUID(entity_id))
        )).scalar_one_or_none()
        if not prog or str(prog.institution_id) != inst:
            raise HTTPException(status_code=404, detail="Program nenalezen")
        if role not in MANAGER_ROLES:
            raise HTTPException(status_code=403, detail="Feed programu smí vytvořit pouze správce")
        return "institution"

    if feed_type == "lecturer":
        # Lecturer feed = only reservations assigned to that user; must be self (or manager).
        target = entity_id or current_user["user_id"]
        if target != current_user["user_id"] and role not in MANAGER_ROLES:
            raise HTTPException(status_code=403, detail="Nelze vytvořit feed jiného uživatele")
        u = (await db.execute(select(User).where(User.id == _uuid.UUID(target)))).scalar_one_or_none()
        if not u or str(u.institution_id) != inst:
            raise HTTPException(status_code=404, detail="Uživatel nenalezen")
        return "assigned"

    raise HTTPException(status_code=400, detail="Neplatný typ feedu")


def _get_ics_signing_key() -> bytes:
    """Derive a stable signing key from JWT_SECRET."""
    secret = os.environ.get("JWT_SECRET", "")
    return hashlib.sha256(f"ics-feed-{secret}".encode()).digest()


def _sign_feed_token(entity_type: str, entity_id: str) -> str:
    """Generate HMAC token for an ICS feed URL."""
    key = _get_ics_signing_key()
    msg = f"{entity_type}:{entity_id}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()[:32]


def _verify_feed_token(entity_type: str, entity_id: str, token: str) -> bool:
    """Verify HMAC token for an ICS feed URL."""
    expected = _sign_feed_token(entity_type, entity_id)
    return hmac.compare_digest(expected, token)


def _parse_time_block(time_block: str) -> tuple:
    """Parse time_block like '09:00-10:30' or '09:00' into (start_hour, start_min)."""
    start_part = time_block.split("-")[0].strip()
    parts = start_part.split(":")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0


def _build_vevent(reservation: dict, program: dict, institution: dict, minimal: bool = True) -> Event:
    """Build a VEVENT. When `minimal` (default, used for shareable feeds) we omit
    personal contact details and free-text notes to avoid leaking data via a URL."""
    event = Event()

    # UID
    event.add("uid", f"{reservation['id']}@budezivo.cz")

    # SUMMARY
    program_name = program.get("name_cs") or program.get("name_en") or "Program"
    event.add("summary", program_name)

    # DTSTART / DTEND
    date_str = reservation.get("date", "")  # YYYY-MM-DD
    time_block = reservation.get("time_block", "09:00")
    duration_min = program.get("duration") or 60

    try:
        year, month, day = map(int, date_str.split("-"))
        start_h, start_m = _parse_time_block(time_block)
        dt_start = PRAGUE_TZ.localize(datetime(year, month, day, start_h, start_m))
        dt_end = dt_start + timedelta(minutes=duration_min)
    except (ValueError, IndexError):
        dt_start = PRAGUE_TZ.localize(datetime.now())
        dt_end = dt_start + timedelta(hours=1)

    event.add("dtstart", dt_start)
    event.add("dtend", dt_end)

    # DESCRIPTION
    desc_lines = []
    if reservation.get("school_name"):
        desc_lines.append(f"Škola: {reservation['school_name']}")
    if reservation.get("num_students"):
        desc_lines.append(f"Počet dětí: {reservation['num_students']}")
    if reservation.get("num_teachers"):
        desc_lines.append(f"Počet učitelů: {reservation['num_teachers']}")
    if not minimal:
        # Full detail only for one-off private downloads, never for shareable feeds.
        if reservation.get("contact_name"):
            desc_lines.append(f"Kontakt: {reservation['contact_name']}")
        if reservation.get("contact_email"):
            desc_lines.append(f"Email: {reservation['contact_email']}")
        if reservation.get("contact_phone"):
            desc_lines.append(f"Telefon: {reservation['contact_phone']}")
        if reservation.get("special_requirements"):
            desc_lines.append(f"Poznámka: {reservation['special_requirements']}")
    status_label = {
        "pending": "Čeká na potvrzení",
        "confirmed": "Potvrzeno",
        "cancelled": "Zrušeno",
        "completed": "Dokončeno",
    }.get(reservation.get("status", ""), reservation.get("status", ""))
    desc_lines.append(f"Stav: {status_label}")
    event.add("description", "\n".join(desc_lines))

    # LOCATION
    address = institution.get("address") or institution.get("name") or ""
    if address:
        event["location"] = vText(address)

    # STATUS
    status_map = {"confirmed": "CONFIRMED", "cancelled": "CANCELLED"}
    ical_status = status_map.get(reservation.get("status"), "TENTATIVE")
    event.add("status", ical_status)

    # CREATED / LAST-MODIFIED
    if reservation.get("created_at"):
        try:
            created = reservation["created_at"]
            if isinstance(created, str):
                created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            event.add("created", created)
        except Exception:
            pass

    return event


def _build_calendar(name: str, events: list) -> bytes:
    """Build a full iCalendar with VCALENDAR wrapper."""
    cal = Calendar()
    cal.add("prodid", "-//Budezivo.cz//Calendar//CS")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", name)
    cal.add("x-wr-timezone", "Europe/Prague")

    for ev in events:
        cal.add_component(ev)

    return cal.to_ical()


def _ics_response(cal_bytes: bytes, filename: str) -> Response:
    """One-off DOWNLOAD response (attachment, current snapshot)."""
    return Response(
        content=cal_bytes,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


def _ics_feed_response(cal_bytes: bytes) -> Response:
    """Live SUBSCRIPTION response (inline, cacheable, fetched server-side by Google/MS)."""
    return Response(
        content=cal_bytes,
        media_type="text/calendar; charset=utf-8",
        headers={"Cache-Control": "max-age=900, public"},
    )


async def _get_institution(db: AsyncSession, institution_id: str) -> dict:
    """Fetch institution dict."""
    from database.supabase_repositories import to_dict
    import uuid
    result = await db.execute(
        select(Institution).where(Institution.id == uuid.UUID(institution_id))
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")
    return to_dict(inst)


async def _get_programs_lookup(db: AsyncSession, institution_id: str) -> dict:
    """Build {program_id_str: program_dict} lookup."""
    from database.supabase_repositories import to_dict
    import uuid
    result = await db.execute(
        select(Program).where(Program.institution_id == uuid.UUID(institution_id))
    )
    programs = result.scalars().all()
    return {str(to_dict(p)["id"]): to_dict(p) for p in programs}


async def _get_reservations(db: AsyncSession, institution_id: str, program_id: str = None, statuses: list = None) -> list:
    """Fetch reservations with optional program filter."""
    from database.supabase_repositories import to_dict
    import uuid
    conditions = [Reservation.institution_id == uuid.UUID(institution_id)]
    if program_id:
        conditions.append(Reservation.program_id == uuid.UUID(program_id))
    if statuses:
        conditions.append(Reservation.status.in_(statuses))
    else:
        conditions.append(Reservation.status.in_(["pending", "confirmed", "completed"]))

    result = await db.execute(
        select(Reservation).where(and_(*conditions)).order_by(Reservation.date.asc())
    )
    return [to_dict(r) for r in result.scalars().all()]


async def _get_reservations_for_scope(db: AsyncSession, institution_id: str, scope: str, owner_user_id: Optional[str], program_id: str = None) -> list:
    from database.supabase_repositories import to_dict
    conditions = [
        Reservation.institution_id == _uuid.UUID(institution_id),
        Reservation.status.in_(["pending", "confirmed", "completed"]),
    ]
    if program_id:
        conditions.append(Reservation.program_id == _uuid.UUID(program_id))
    if scope == "assigned" and owner_user_id:
        conditions.append(Reservation.assigned_lecturer_id == _uuid.UUID(owner_user_id))
    result = await db.execute(
        select(Reservation).where(and_(*conditions)).order_by(Reservation.date.asc())
    )
    return [to_dict(r) for r in result.scalars().all()]


def _feed_base_url() -> str:
    base = (os.environ.get("BACKEND_URL") or os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
    return base


def _subscription_url(feed_type: str, entity_id: Optional[str], token: str) -> str:
    base = _feed_base_url()
    if feed_type == "institution":
        path = f"/api/calendar/institution/{entity_id}.ics"
    elif feed_type == "program":
        path = f"/api/calendar/program/{entity_id}.ics"
    else:
        path = f"/api/calendar/lecturer/{entity_id}.ics"
    return f"{base}{path}?token={token}" if base else f"{path}?token={token}"


# ── ICS Feed token management (revocable) ───────────────────────────


@router.post("/feed-tokens")
async def create_feed_token(
    body: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a fresh revocable subscription token. Any previous ACTIVE token for the
    same owner+type+entity is revoked (regenerate = old URL stops working)."""
    feed_type = body.get("feed_type")
    entity_id = body.get("entity_id")
    if feed_type not in ("institution", "program", "lecturer"):
        raise HTTPException(status_code=400, detail="Neplatný typ feedu")

    scope = await _resolve_feed_scope(db, current_user, feed_type, entity_id)
    inst = current_user["institution_id"]
    owner = current_user["user_id"]
    resolved_entity = entity_id or (inst if feed_type == "institution" else owner)

    # Revoke existing active token(s) for the same owner+type+entity.
    now = datetime.now(timezone.utc)
    existing = (await db.execute(
        select(CalendarFeedToken).where(and_(
            CalendarFeedToken.institution_id == _uuid.UUID(inst),
            CalendarFeedToken.user_id == _uuid.UUID(owner),
            CalendarFeedToken.feed_type == feed_type,
            CalendarFeedToken.entity_id == _uuid.UUID(resolved_entity),
            CalendarFeedToken.revoked_at.is_(None),
        ))
    )).scalars().all()
    for t in existing:
        t.revoked_at = now

    raw = secrets.token_urlsafe(32)
    row = CalendarFeedToken(
        institution_id=_uuid.UUID(inst),
        user_id=_uuid.UUID(owner),
        feed_type=feed_type,
        entity_id=_uuid.UUID(resolved_entity),
        scope=scope,
        token_hash=_hash_token(raw),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "id": str(row.id),
        "feed_type": feed_type,
        "scope": scope,
        "url": _subscription_url(feed_type, resolved_entity, raw),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/feed-tokens")
async def list_feed_tokens(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the caller's ACTIVE feed tokens (raw token never returned)."""
    rows = (await db.execute(
        select(CalendarFeedToken).where(and_(
            CalendarFeedToken.institution_id == _uuid.UUID(current_user["institution_id"]),
            CalendarFeedToken.user_id == _uuid.UUID(current_user["user_id"]),
            CalendarFeedToken.revoked_at.is_(None),
        )).order_by(CalendarFeedToken.created_at.desc())
    )).scalars().all()
    return [{
        "id": str(r.id),
        "feed_type": r.feed_type,
        "scope": r.scope,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "last_used_at": r.last_used_at.isoformat() if r.last_used_at else None,
    } for r in rows]


@router.post("/feed-tokens/{token_id}/revoke")
async def revoke_feed_token(
    token_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a feed token (its URL immediately stops working). Tenant/owner-safe."""
    row = (await db.execute(
        select(CalendarFeedToken).where(and_(
            CalendarFeedToken.id == _uuid.UUID(token_id),
            CalendarFeedToken.institution_id == _uuid.UUID(current_user["institution_id"]),
            CalendarFeedToken.user_id == _uuid.UUID(current_user["user_id"]),
        ))
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Odkaz nenalezen")
    if not row.revoked_at:
        row.revoked_at = datetime.now(timezone.utc)
        await db.commit()
    return {"revoked": True}


async def _consume_feed_token(db: AsyncSession, feed_type: str, entity_id: str, token: str) -> CalendarFeedToken:
    """Validate a subscription token from the DB (hash lookup), bump last_used_at."""
    if not token:
        raise HTTPException(status_code=403, detail="Chybí token pro ICS feed")
    row = (await db.execute(
        select(CalendarFeedToken).where(and_(
            CalendarFeedToken.token_hash == _hash_token(token),
            CalendarFeedToken.feed_type == feed_type,
            CalendarFeedToken.entity_id == _uuid.UUID(entity_id),
            CalendarFeedToken.revoked_at.is_(None),
        ))
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=403, detail="Neplatný nebo zneplatněný odkaz")
    row.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return row


# ── Single-reservation one-off download token (short deterministic, private) ──


@router.get("/public-feed-token/reservation/{reservation_id}")
async def generate_public_reservation_token(reservation_id: str):
    """Token for a single reservation .ics DOWNLOAD (post-booking, attachment)."""
    token = _sign_feed_token("reservation", reservation_id)
    return {"token": token}


# ── Live subscription feeds (inline, minimized, revocable) ──────────


@router.get("/institution/{institution_id}.ics")
async def institution_calendar_feed(
    institution_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    await _consume_feed_token(db, "institution", institution_id, token)
    institution = await _get_institution(db, institution_id)
    programs_lookup = await _get_programs_lookup(db, institution_id)
    reservations = await _get_reservations_for_scope(db, institution_id, "institution", None)
    events = [_build_vevent(r, programs_lookup.get(r.get("program_id"), {}), institution, minimal=True) for r in reservations]
    cal_bytes = _build_calendar(f"Rezervace – {institution.get('name', 'Instituce')}", events)
    return _ics_feed_response(cal_bytes)


@router.get("/program/{program_id}.ics")
async def program_calendar_feed(
    program_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    await _consume_feed_token(db, "program", program_id, token)
    from database.supabase_repositories import to_dict
    program = (await db.execute(select(Program).where(Program.id == _uuid.UUID(program_id)))).scalar_one_or_none()
    if not program:
        raise HTTPException(status_code=404, detail="Program nenalezen")
    program_dict = to_dict(program)
    inst_id = program_dict["institution_id"]
    institution = await _get_institution(db, inst_id)
    reservations = await _get_reservations_for_scope(db, inst_id, "institution", None, program_id=program_id)
    events = [_build_vevent(r, program_dict, institution, minimal=True) for r in reservations]
    cal_bytes = _build_calendar(f"{program_dict.get('name_cs', 'Program')} – Rezervace", events)
    return _ics_feed_response(cal_bytes)


@router.get("/lecturer/{user_id}.ics")
async def lecturer_calendar_feed(
    user_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    row = await _consume_feed_token(db, "lecturer", user_id, token)
    institution = await _get_institution(db, str(row.institution_id))
    programs_lookup = await _get_programs_lookup(db, str(row.institution_id))
    reservations = await _get_reservations_for_scope(db, str(row.institution_id), "assigned", user_id)
    events = [_build_vevent(r, programs_lookup.get(r.get("program_id"), {}), institution, minimal=True) for r in reservations]
    cal_bytes = _build_calendar("Moje rezervace – Budeživo", events)
    return _ics_feed_response(cal_bytes)


@router.get("/reservation/{reservation_id}.ics")
async def reservation_ics_download(
    reservation_id: str,
    token: str = Query(..., description="Signed HMAC token"),
    db: AsyncSession = Depends(get_db),
):
    """Download a single reservation as .ics file. Requires signed token."""
    if not _verify_feed_token("reservation", reservation_id, token):
        raise HTTPException(status_code=403, detail="Neplatný token pro ICS feed")
    from database.supabase_repositories import to_dict
    import uuid

    result = await db.execute(
        select(Reservation).where(Reservation.id == uuid.UUID(reservation_id))
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervace nenalezena")
    res_dict = to_dict(reservation)

    # Fetch program
    prog_result = await db.execute(
        select(Program).where(Program.id == uuid.UUID(res_dict["program_id"]))
    )
    program = prog_result.scalar_one_or_none()
    prog_dict = to_dict(program) if program else {}

    # Fetch institution
    institution = await _get_institution(db, res_dict["institution_id"])

    event = _build_vevent(res_dict, prog_dict, institution)
    cal_bytes = _build_calendar(
        prog_dict.get("name_cs", "Rezervace"), [event]
    )
    return _ics_response(cal_bytes, f"rezervace-{reservation_id[:8]}.ics")
