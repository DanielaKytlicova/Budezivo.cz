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


async def apply_delivery_update(db, delivery_update: dict, svix_id: str) -> dict:
    """Persist a normalized Resend delivery update and update contact health.

    Kept separate from the FastAPI route so an isolated regression database can
    exercise the same persistence path without needing a signed external webhook.
    """
    from sqlalchemy import and_, func, select

    from database.models import (
        Contact,
        MailingCampaign,
        MailingCampaignRecipient,
        ResendWebhookEvent,
        SchoolContact,
    )

    event_type = delivery_update["event_type"]
    if (await db.execute(
        select(ResendWebhookEvent.id).where(ResendWebhookEvent.svix_id == svix_id)
    )).scalar_one_or_none():
        return {"ok": True, "duplicate": True}

    status = delivery_update["status"]
    provider_email_id = delivery_update["provider_email_id"]
    recipient_email = delivery_update["recipient_email"]
    event_at = delivery_update["event_at"]
    reason = delivery_update["reason"]

    db.add(ResendWebhookEvent(
        svix_id=svix_id,
        event_type=event_type,
        provider_email_id=provider_email_id,
        recipient_email=recipient_email,
        event_at=event_at,
    ))

    matched = []
    if provider_email_id:
        matched = list((await db.execute(
            select(MailingCampaignRecipient, MailingCampaign.institution_id)
            .join(MailingCampaign, MailingCampaignRecipient.campaign_id == MailingCampaign.id)
            .where(MailingCampaignRecipient.email_provider_id == provider_email_id)
        )).all())

    for recipient, institution_id in matched:
        if recipient.delivery_event_at and recipient.delivery_event_at > event_at:
            continue
        recipient.delivery_status = status
        recipient.delivery_event_at = event_at
        if status in {"bounced_hard", "failed", "complained", "suppressed"}:
            recipient.failure_reason = reason or status

        email = (recipient.email or recipient_email or "").strip().lower()
        if not email:
            continue

        central_contacts = list((await db.execute(
            select(Contact).where(and_(
                Contact.institution_id == institution_id,
                func.lower(Contact.email) == email,
            ))
        )).scalars().all())
        school_contacts = list((await db.execute(
            select(SchoolContact).where(and_(
                SchoolContact.institution_id == institution_id,
                func.lower(SchoolContact.email) == email,
            ))
        )).scalars().all())

        for contact in [*central_contacts, *school_contacts]:
            if contact.deliverability_updated_at and contact.deliverability_updated_at > event_at:
                continue
            contact.deliverability_status = status
            contact.deliverability_reason = reason
            contact.deliverability_updated_at = event_at

        if status in PERMANENT_SUPPRESSION:
            for contact in school_contacts:
                contact.last_email_bounced = status == "bounced_hard"
                contact.status = "invalid"
                contact.email_validation_error = reason or status

    await db.commit()
    return {"ok": True, "matched_recipients": len(matched), "status": status}
