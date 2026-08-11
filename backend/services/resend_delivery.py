"""Pure Resend delivery-event normalization helpers."""
from __future__ import annotations

from datetime import datetime, timezone


STATUS_BY_EVENT = {
    "email.delivered": "delivered",
    "email.delivery_delayed": "bounced_soft",
    "email.bounced": "bounced_hard",
    "email.complained": "complained",
    "email.suppressed": "suppressed",
    "email.failed": "failed",
    "email.unsubscribed": "unsubscribed",
}

PERMANENT_SUPPRESSION = {"bounced_hard", "complained", "suppressed", "unsubscribed"}


def parse_datetime(value) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def delivery_reason(data: dict, status: str) -> str | None:
    bounce = data.get("bounce") or {}
    return (
        bounce.get("message")
        or bounce.get("subType")
        or bounce.get("type")
        or data.get("reason")
        or {
            "complained": "Příjemce označil zprávu jako spam",
            "suppressed": "Adresa je na suppression seznamu poskytovatele",
            "unsubscribed": "Příjemce se odhlásil",
            "bounced_soft": "Doručení je dočasně zpožděné",
        }.get(status)
    )


def delivery_update_from_payload(payload: dict) -> dict | None:
    """Normalize a verified Resend event into the fields persisted by the webhook."""
    event_type = payload.get("type")
    status = STATUS_BY_EVENT.get(event_type)
    if not status:
        return None

    data = payload.get("data") or {}
    if event_type == "email.bounced":
        bounce_type = str((data.get("bounce") or {}).get("type") or "").lower()
        if bounce_type in {"transient", "soft"}:
            status = "bounced_soft"

    to_value = data.get("to") or []
    recipient_email = (to_value[0] if isinstance(to_value, list) and to_value else to_value) or None
    recipient_email = recipient_email.strip().lower() if isinstance(recipient_email, str) else None

    return {
        "event_type": event_type,
        "status": status,
        "provider_email_id": data.get("email_id") or data.get("id"),
        "recipient_email": recipient_email,
        "event_at": parse_datetime(payload.get("created_at") or data.get("created_at")),
        "reason": delivery_reason(data, status),
    }
