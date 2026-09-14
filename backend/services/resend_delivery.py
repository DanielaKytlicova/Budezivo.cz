"""Pure Resend delivery-event normalization helpers."""
from __future__ import annotations

from collections.abc import Mapping
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
TRANSACTIONAL_ALERT_STATUSES = {"bounced_hard", "complained", "suppressed", "failed"}
INVALID_CONTACT_STATUSES = {"bounced_hard", "complained", "suppressed"}

DELIVERY_STATUS_LABELS = {
    "pending": "Čeká na odeslání",
    "sent": "Odesláno poskytovateli",
    "delivered": "Doručeno",
    "opened": "Otevřeno",
    "clicked": "Kliknuto",
    "bounced_soft": "Dočasně nedoručeno",
    "bounced_hard": "Nedoručeno",
    "complained": "Označeno jako spam",
    "suppressed": "Blokováno poskytovatelem",
    "failed": "Selhalo",
    "unsubscribed": "Odhlášeno",
    "unknown": "Neznámý stav",
}

DELIVERED_STATUSES = {"delivered", "opened", "clicked"}
DELIVERY_FAILURE_STATUSES = {
    "bounced_hard",
    "failed",
    "complained",
    "suppressed",
    "unsubscribed",
}


def delivery_status_label(status: str | None) -> str:
    return DELIVERY_STATUS_LABELS.get(status or "unknown", DELIVERY_STATUS_LABELS["unknown"])


def transactional_delivery_alert(logs, current_email: str | None) -> dict | None:
    """Return the latest final delivery failure for the booking's current address."""
    normalized_email = (current_email or "").strip().lower()
    if not normalized_email:
        return None
    for log in logs:
        if isinstance(log, Mapping):
            email = log.get("recipient_email")
            status = log.get("status")
            reason = log.get("error_message")
        else:
            email = getattr(log, "recipient_email", None)
            status = getattr(log, "status", None)
            reason = getattr(log, "error_message", None)
        if (email or "").strip().lower() != normalized_email:
            continue
        if status in TRANSACTIONAL_ALERT_STATUSES:
            return {"status": status, "reason": reason}
    return None


def campaign_delivery_counts(recipients) -> dict[str, int]:
    """Calculate campaign results from the latest per-recipient delivery state.

    ``status == sent`` only confirms that Resend accepted the message. A campaign
    is successful only after a delivery webhook confirms it.
    """
    counts = {
        "accepted_count": 0,
        "delivered_count": 0,
        "delivery_failed_count": 0,
        "awaiting_delivery_count": 0,
        "skipped_count": 0,
    }

    for recipient in recipients:
        if isinstance(recipient, Mapping):
            send_status = recipient.get("status")
            delivery_status = recipient.get("delivery_status")
        else:
            send_status = getattr(recipient, "status", None)
            delivery_status = getattr(recipient, "delivery_status", None)

        delivery_status = delivery_status or send_status or "unknown"
        if send_status == "sent":
            counts["accepted_count"] += 1
        if send_status == "skipped":
            counts["skipped_count"] += 1
        elif delivery_status in DELIVERED_STATUSES:
            counts["delivered_count"] += 1
        elif send_status == "failed" or delivery_status in DELIVERY_FAILURE_STATUSES:
            counts["delivery_failed_count"] += 1
        elif send_status in {"sent", "pending"}:
            counts["awaiting_delivery_count"] += 1

    return counts


def parse_datetime(value) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def delivery_reason(data: dict, status: str) -> str | None:
    bounce = data.get("bounce") or {}
    suppressed = data.get("suppressed") or {}
    failed = data.get("failed") or {}
    return (
        bounce.get("message")
        or bounce.get("subType")
        or bounce.get("type")
        or suppressed.get("message")
        or suppressed.get("reason")
        or suppressed.get("type")
        or failed.get("reason")
        or data.get("reason")
        or {
            "complained": "Příjemce označil zprávu jako spam",
            "suppressed": "Adresa je na suppression seznamu poskytovatele",
            "unsubscribed": "Příjemce se odhlásil",
            "bounced_soft": "Doručení je dočasně zpožděné",
            "failed": "E-mail se nepodařilo odeslat",
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
        if bounce_type in {"transient", "temporary", "soft"}:
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
    from sqlalchemy.exc import IntegrityError

    from database.models import (
        Contact,
        EmailLog,
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

    newer_event_exists = False
    if provider_email_id:
        newer_event_exists = (await db.execute(
            select(ResendWebhookEvent.id).where(and_(
                ResendWebhookEvent.provider_email_id == provider_email_id,
                ResendWebhookEvent.event_at > event_at,
            )).limit(1)
        )).scalar_one_or_none() is not None

    try:
        async with db.begin_nested():
            db.add(ResendWebhookEvent(
                svix_id=svix_id,
                event_type=event_type,
                provider_email_id=provider_email_id,
                recipient_email=recipient_email,
                event_at=event_at,
            ))
            await db.flush()
    except IntegrityError:
        return {"ok": True, "duplicate": True}

    matched = []
    matched_logs = []
    if provider_email_id and not newer_event_exists:
        matched = list((await db.execute(
            select(MailingCampaignRecipient, MailingCampaign.institution_id)
            .join(MailingCampaign, MailingCampaignRecipient.campaign_id == MailingCampaign.id)
            .where(MailingCampaignRecipient.email_provider_id == provider_email_id)
        )).all())
        matched_logs = list((await db.execute(
            select(EmailLog).where(EmailLog.email_id == provider_email_id)
        )).scalars().all())

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

    for email_log in matched_logs:
        email_log.status = status
        email_log.error_message = (
            reason or delivery_status_label(status)
            if status in DELIVERY_FAILURE_STATUSES
            else None
        )

        email = (email_log.recipient_email or recipient_email or "").strip().lower()
        if not email:
            continue
        central_contacts = list((await db.execute(
            select(Contact).where(and_(
                Contact.institution_id == email_log.institution_id,
                func.lower(Contact.email) == email,
            ))
        )).scalars().all())
        school_contacts = list((await db.execute(
            select(SchoolContact).where(and_(
                SchoolContact.institution_id == email_log.institution_id,
                func.lower(SchoolContact.email) == email,
            ))
        )).scalars().all())
        for contact in [*central_contacts, *school_contacts]:
            contact.deliverability_status = status
            contact.deliverability_reason = reason
            contact.deliverability_updated_at = event_at
        if status in INVALID_CONTACT_STATUSES:
            for contact in school_contacts:
                contact.last_email_bounced = status == "bounced_hard"
                contact.status = "invalid"
                contact.email_validation_error = reason or status

    await db.commit()
    return {
        "ok": True,
        "matched_recipients": len(matched),
        "matched_transactional": len(matched_logs),
        "status": status,
    }
