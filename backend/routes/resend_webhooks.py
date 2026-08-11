"""Authenticated Resend delivery webhooks.

The signature is verified against the unchanged request body. Only the minimum
delivery metadata needed for audit and suppression is persisted.
"""
from __future__ import annotations

import json
import logging
import os
import binascii

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from database.models import (
    Contact,
    MailingCampaign,
    MailingCampaignRecipient,
    ResendWebhookEvent,
    SchoolContact,
)
from database.supabase import get_db
from services.resend_delivery import PERMANENT_SUPPRESSION, delivery_update_from_payload


router = APIRouter(prefix="/resend", tags=["Resend"])
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def resend_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    secret = os.getenv("RESEND_WEBHOOK_SECRET")
    if not secret:
        logger.error("RESEND_WEBHOOK_SECRET is not configured")
        raise HTTPException(503, "Resend webhook není nakonfigurován")

    raw_body = await request.body()
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }
    if not all(headers.values()):
        raise HTTPException(400, "Chybí podpis webhooku")

    try:
        verified = Webhook(secret).verify(raw_body, headers)
    except (WebhookVerificationError, ValueError, binascii.Error):
        raise HTTPException(400, "Neplatný podpis webhooku")

    payload = verified if isinstance(verified, dict) else json.loads(raw_body)
    delivery_update = delivery_update_from_payload(payload)
    if not delivery_update:
        return {"ok": True, "ignored": True}
    event_type = delivery_update["event_type"]

    svix_id = headers["svix-id"]
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
