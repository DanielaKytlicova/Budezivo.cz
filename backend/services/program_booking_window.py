from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9 fallback
    ZoneInfo = None


def parse_program_datetime(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date_type):
        parsed = datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    if parsed.tzinfo:
        return parsed.astimezone(timezone.utc)
    return parsed.replace(tzinfo=timezone.utc)


def booking_opens_message(program: dict, now: Optional[datetime] = None) -> Optional[str]:
    opens_at = parse_program_datetime((program or {}).get("booking_opens_at"))
    if not opens_at:
        return None

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)

    if current >= opens_at:
        return None

    display_tz = ZoneInfo("Europe/Prague") if ZoneInfo else timezone.utc
    display = opens_at.astimezone(display_tz).strftime("%d.%m.%Y %H:%M")
    return f"Rezervace tohoto programu se spustí až {display}."


def program_booking_window_message(
    program: dict,
    booking_date: date_type,
    now: Optional[datetime] = None,
) -> Optional[str]:
    """Return a safe user-facing reason when a date is outside program rules."""
    opens_error = booking_opens_message(program, now)
    if opens_error:
        return opens_error

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)

    min_days = int((program or {}).get("min_days_before_booking") or 0)
    if min_days and booking_date < current.date() + timedelta(days=min_days):
        return f"Termín je možné rezervovat nejdříve {min_days} dní předem."

    max_days = int((program or {}).get("max_days_before_booking") or 0)
    if max_days and booking_date > current.date() + timedelta(days=max_days):
        return f"Termín je možné rezervovat nejvýše {max_days} dní předem."

    start_date = parse_program_datetime((program or {}).get("start_date"))
    if start_date and booking_date < start_date.date():
        return "Vybraný termín je před začátkem období programu."

    end_date = parse_program_datetime((program or {}).get("end_date"))
    if end_date and booking_date > end_date.date():
        return "Vybraný termín je po skončení období programu."

    return None
