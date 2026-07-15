"""Pure, side-effect-free helpers for Google Calendar two-way sync.

Kept free of network/DB access so the sync decisions can be unit-tested.
"""
from __future__ import annotations

from typing import Optional, Tuple

CALENDAR_TIMEZONE = "Europe/Prague"

# Required OAuth scopes (never the broad calendar scope).
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/userinfo.email",
]
EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"

CANCELLED_STATUSES = {"cancelled", "canceled"}

STATUS_LABELS = {
    "pending": "Čeká na potvrzení",
    "confirmed": "Potvrzeno",
    "completed": "Dokončeno",
    "no_show": "Nedostavili se",
}


def has_events_scope(granted_scopes: Optional[str]) -> bool:
    """True if the stored grant includes calendar.events (needed for export)."""
    if not granted_scopes:
        return False
    return EVENTS_SCOPE in granted_scopes.split()


def is_budezivo_event(ev: dict) -> bool:
    """True if a Google event was created by Budeživo (export). Such events must
    NOT be re-imported as availability blocks (prevents a sync loop)."""
    props = (ev.get("extendedProperties") or {}).get("private") or {}
    return props.get("source") == "budezivo"


def _parse_block(time_block: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse 'HH:MM' or 'HH:MM-HH:MM' into (start_min, end_min|None)."""
    try:
        if "-" in time_block:
            a, b = time_block.split("-", 1)
            sh, sm = map(int, a.strip().split(":"))
            eh, em = map(int, b.strip().split(":"))
            return sh * 60 + sm, eh * 60 + em
        h, m = map(int, time_block.strip().split(":"))
        return h * 60 + m, None
    except (ValueError, AttributeError, IndexError):
        return None, None


def _fmt(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def reservation_local_times(date_str: str, time_block: str, duration: Optional[int]) -> Optional[Tuple[str, str]]:
    """Return (start_iso_local, end_iso_local) 'YYYY-MM-DDTHH:MM:00' or None if invalid.

    Times are LOCAL (Europe/Prague); the caller attaches the timeZone so Google
    resolves DST correctly.
    """
    if not date_str or not time_block:
        return None
    start_min, end_min = _parse_block(time_block)
    if start_min is None:
        return None
    if end_min is None:
        end_min = start_min + (duration or 60)
    if end_min <= start_min:
        return None
    return (
        f"{date_str}T{_fmt(start_min)}:00",
        f"{date_str}T{_fmt(end_min)}:00",
    )


def build_export_event_body(
    *,
    booking_id: str,
    institution_id: str,
    user_id: str,
    program_name: str,
    status: str,
    date_str: str,
    time_block: str,
    duration: Optional[int],
    institution_name: str,
    room_name: Optional[str],
    school_name: Optional[str],
    group_type: Optional[str],
    num_students: Optional[int],
    admin_base_url: str,
) -> Optional[dict]:
    """Build a Google event body for an exported reservation.

    Only non-sensitive data is included. Explicitly NEVER includes contact phone,
    personal e-mail, internal notes or special requirements.
    """
    times = reservation_local_times(date_str, time_block, duration)
    if not times:
        return None
    start_iso, end_iso = times
    status_label = STATUS_LABELS.get(status, status or "")

    desc_lines = [f"Instituce: {institution_name}"]
    if school_name:
        desc_lines.append(f"Skupina: {school_name}")
    if group_type:
        desc_lines.append(f"Typ skupiny: {group_type}")
    if num_students:
        desc_lines.append(f"Počet žáků: {num_students}")
    desc_lines.append(f"Stav: {status_label}")
    desc_lines.append(f"Otevřít v Budeživo: {admin_base_url}/admin/reservations?id={booking_id}")

    body = {
        "summary": f"{program_name} ({status_label})" if status_label else program_name,
        "description": "\n".join(desc_lines),
        "start": {"dateTime": start_iso, "timeZone": CALENDAR_TIMEZONE},
        "end": {"dateTime": end_iso, "timeZone": CALENDAR_TIMEZONE},
        "extendedProperties": {
            "private": {
                "source": "budezivo",
                "booking_id": str(booking_id),
                "institution_id": str(institution_id),
                "user_id": str(user_id),
            }
        },
        "reminders": {"useDefault": True},
    }
    if room_name:
        body["location"] = room_name
    return body


def reservation_assigned_user_ids(reservation) -> set:
    """All lecturer user-ids assigned to a reservation (main + additional)."""
    ids = set()
    if getattr(reservation, "assigned_lecturer_id", None):
        ids.add(str(reservation.assigned_lecturer_id))
    for uid in (getattr(reservation, "assigned_lecturer_ids", None) or []):
        if uid:
            ids.add(str(uid))
    return ids
