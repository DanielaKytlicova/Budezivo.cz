"""PII-free booking analytics helpers.

Analytics is strictly best-effort. It must never affect booking decisions,
database transactions, or the response shown to a visitor.
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import BookingAnalyticsEvent
from database.supabase import AsyncSessionLocal

logger = logging.getLogger(__name__)

BOOKING_SESSION_HEADER = "x-booking-session-id"

ALLOWED_EVENT_TYPES = {
    "booking_started",
    "booking_submit_attempted",
    "booking_failed",
    "booking_blocked",
    "booking_completed",
    "reservation_created",
    "reservation_rescheduled",
    "reservation_cancelled",
    "reservation_completed",
    "reservation_no_show",
}

PII_KEYS = {
    "name",
    "email",
    "phone",
    "contact_name",
    "contact_email",
    "contact_phone",
    "school_name",
    "special_requirements",
    "notes",
    "applicant_name",
    "applicant_email",
    "teacher_name",
}

_SESSION_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


def safe_uuid(value: Any) -> Optional[uuid.UUID]:
    if not value:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def safe_session_id(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip()
    if not _SESSION_RE.fullmatch(text):
        return None
    return text[:128]


def safe_metadata(metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not metadata:
        return {}
    out: dict[str, Any] = {}
    for key, value in metadata.items():
        key_text = str(key)
        if key_text.lower() in PII_KEYS:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[key_text[:80]] = str(value)[:300] if isinstance(value, str) else value
    return out


def classify_booking_failed(detail: Any, status_code: Optional[int] = None) -> str:
    if status_code == 422 or status_code == 400:
        return "validation_error"
    if status_code and status_code >= 500:
        return "server_error"
    if isinstance(detail, dict) and detail.get("field"):
        return "validation_error"
    return "unknown_error"


def classify_booking_blocked(detail: Any) -> str:
    if isinstance(detail, dict):
        code = str(detail.get("code") or "").upper()
        source = str(detail.get("source") or "").lower()
        if code == "ROOM_TAKEN" or source == "room":
            return "room_conflict"
        if code in {"LECTURER_BUSY", "NO_LECTURER_AVAILABLE"} or source == "lecturer":
            return "lecturer_conflict"
        if code == "EXCEPTION" or source == "exception":
            return "availability_block"
        if code in {"SEPARATE_ONLY", "PROGRAM_BLOCKS_OTHERS", "FULL_BLOCK"}:
            return "program_conflict"
        if code == "MAX_CONCURRENT":
            return "program_concurrency_limit"
    text = str(detail or "")
    lower_text = text.lower()
    if "kapacita souběžných rezervací" in lower_text:
        return "program_concurrency_limit"
    if "kolize místnosti" in lower_text:
        return "room_conflict"
    if "kolize lektora" in lower_text or "hlavní lektor" in lower_text:
        return "lecturer_conflict"
    if "slot je jednorázově uzavřen" in lower_text or "blokace" in lower_text or "nedostup" in lower_text:
        return "availability_block"
    if "program z odkazu" in lower_text or "není dostupný" in lower_text:
        return "program_unavailable"
    if "rezervace tohoto programu se spustí" in lower_text or "rezervací spustí" in lower_text:
        return "booking_not_open_yet"
    return "unknown_block"


async def record_booking_event(
    db: AsyncSession,
    event_type: str,
    *,
    institution_id: Any = None,
    program_id: Any = None,
    reservation_id: Any = None,
    session_id: Any = None,
    reason: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> bool:
    if event_type not in ALLOWED_EVENT_TYPES:
        return False
    event = BookingAnalyticsEvent(
        event_type=event_type,
        institution_id=safe_uuid(institution_id),
        program_id=safe_uuid(program_id),
        reservation_id=safe_uuid(reservation_id),
        session_id=safe_session_id(session_id),
        reason=(reason or "")[:80] or None,
        metadata_json=safe_metadata(metadata),
    )
    db.add(event)
    try:
        await db.commit()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("booking analytics event write failed: %s", exc)
        await db.rollback()
        return False


async def _write_booking_event(event_type: str, kwargs: dict[str, Any]) -> None:
    if AsyncSessionLocal is None:
        return
    try:
        async with AsyncSessionLocal() as db:
            await record_booking_event(db, event_type, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("booking analytics background write failed: %s", exc)


def schedule_booking_event(event_type: str, **kwargs: Any) -> None:
    """Fire-and-forget analytics write using its own DB session."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_write_booking_event(event_type, kwargs))
    except RuntimeError:
        logger.warning("booking analytics scheduling skipped: no running event loop")
    except Exception as exc:  # noqa: BLE001
        logger.warning("booking analytics scheduling failed: %s", exc)
