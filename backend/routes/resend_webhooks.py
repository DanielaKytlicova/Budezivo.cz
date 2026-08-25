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
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from database.supabase import get_db
from services.resend_delivery import apply_delivery_update, delivery_update_from_payload


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
    return await apply_delivery_update(db, delivery_update, headers["svix-id"])
