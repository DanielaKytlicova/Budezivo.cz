"""
Calendar export routes - ICS feed generation for Outlook/Google Calendar integration.
Generates .ics feeds for reservations (read-only export).
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from icalendar import Calendar, Event, vText
import pytz

from database.supabase import get_db
from database.models import Reservation, Program, Institution

router = APIRouter(prefix="/calendar", tags=["Calendar"])
logger = logging.getLogger(__name__)

PRAGUE_TZ = pytz.timezone("Europe/Prague")


def _parse_time_block(time_block: str) -> tuple:
    """Parse time_block like '09:00-10:30' or '09:00' into (start_hour, start_min)."""
    start_part = time_block.split("-")[0].strip()
    parts = start_part.split(":")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0


def _build_vevent(reservation: dict, program: dict, institution: dict) -> Event:
    """Build a VEVENT from reservation + program + institution data."""
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
    """Return an ICS response with proper headers."""
    return Response(
        content=cal_bytes,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "max-age=300, public",
        },
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


# ── ICS Feed Endpoints ──────────────────────────────────────────────


@router.get("/institution/{institution_id}.ics")
async def institution_calendar_feed(
    institution_id: str,
    status: Optional[str] = Query(None, description="Comma-separated statuses filter"),
    db: AsyncSession = Depends(get_db),
):
    """ICS feed for ALL reservations of an institution."""
    institution = await _get_institution(db, institution_id)
    programs_lookup = await _get_programs_lookup(db, institution_id)

    statuses = [s.strip() for s in status.split(",")] if status else None
    reservations = await _get_reservations(db, institution_id, statuses=statuses)

    events = []
    for r in reservations:
        prog = programs_lookup.get(r.get("program_id"), {})
        events.append(_build_vevent(r, prog, institution))

    cal_bytes = _build_calendar(
        f"Rezervace – {institution.get('name', 'Instituce')}", events
    )
    return _ics_response(cal_bytes, f"budezivo-{institution_id[:8]}.ics")


@router.get("/program/{program_id}.ics")
async def program_calendar_feed(
    program_id: str,
    db: AsyncSession = Depends(get_db),
):
    """ICS feed for reservations of a specific program."""
    from database.supabase_repositories import to_dict
    import uuid

    result = await db.execute(
        select(Program).where(Program.id == uuid.UUID(program_id))
    )
    program = result.scalar_one_or_none()
    if not program:
        raise HTTPException(status_code=404, detail="Program nenalezen")
    program_dict = to_dict(program)
    inst_id = program_dict["institution_id"]

    institution = await _get_institution(db, inst_id)
    reservations = await _get_reservations(db, inst_id, program_id=program_id)

    events = [_build_vevent(r, program_dict, institution) for r in reservations]
    cal_bytes = _build_calendar(
        f"{program_dict.get('name_cs', 'Program')} – Rezervace", events
    )
    return _ics_response(cal_bytes, f"budezivo-program-{program_id[:8]}.ics")


@router.get("/reservation/{reservation_id}.ics")
async def reservation_ics_download(
    reservation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download a single reservation as .ics file (for 'Add to Outlook' button)."""
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
