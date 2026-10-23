"""One Czech-local representation of event dates for emails and exports."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


EVENT_TIMEZONE = ZoneInfo("Europe/Prague")
UNRECORDED_SCHEDULE = "Termín není evidován. Ověřte jej prosím u pořadatele."
PREREGISTRATION_SCHEDULE = "Předzápis – termín zatím nebyl stanoven."


def event_local_datetime(value):
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    # Existing API contract accepts historical naive timestamps as UTC.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(EVENT_TIMEZONE)


def format_event_datetime(value):
    return event_local_datetime(value).strftime("%d. %m. %Y %H:%M")


def format_event_schedule(start, end):
    start_local = event_local_datetime(start)
    end_local = event_local_datetime(end)
    if end_local.astimezone(timezone.utc) <= start_local.astimezone(timezone.utc):
        raise ValueError("Event end must be after start")
    start_label = start_local.strftime("%d. %m. %Y %H:%M")
    end_label = end_local.strftime("%H:%M" if start_local.date() == end_local.date() else "%d. %m. %Y %H:%M")
    # Disambiguate the repeated hour at the autumn clock change.
    if start_local.utcoffset() != end_local.utcoffset():
        return f"{start_label} {start_local.tzname()} – {end_label} {end_local.tzname()}"
    return f"{start_label}–{end_label}"
