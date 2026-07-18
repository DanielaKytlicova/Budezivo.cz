"""Public institution-scoped unsubscribe flow and authenticated statistics."""
import html
import uuid
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import APIRouter, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import JWT_ALGORITHM, JWT_SECRET
from core.security import get_current_user
from database.models import Contact, Institution, MarketingSubscription
from database.supabase import get_db

router = APIRouter(prefix="/marketing", tags=["Marketing subscriptions"])

REASONS = {
    "too_frequent": "E-maily chodí příliš často",
    "not_relevant": "Obsah pro mě není relevantní",
    "no_interest": "Již nemám zájem",
    "other": "Jiný důvod",
}


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def create_unsubscribe_token(institution_id: str, email: str) -> str:
    return jwt.encode({
        "purpose": "marketing_unsubscribe",
        "institution_id": str(institution_id),
        "email": _normalize_email(email),
        "exp": datetime.now(timezone.utc) + timedelta(days=730),
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode(token: str) -> tuple[str, str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(400, "Odkaz je neplatný nebo vypršel.")
    if payload.get("purpose") != "marketing_unsubscribe":
        raise HTTPException(400, "Neplatný účel odkazu.")
    return str(payload["institution_id"]), _normalize_email(payload["email"])


async def _set_subscription(db: AsyncSession, institution_id: str, email: str, subscribed: bool):
    try:
        institution_uuid = uuid.UUID(str(institution_id))
    except ValueError:
        raise HTTPException(400, "Neplatná instituce.")
    row = (await db.execute(select(MarketingSubscription).where(and_(
        MarketingSubscription.institution_id == institution_uuid,
        func.lower(MarketingSubscription.email) == email,
    )))).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if not row:
        row = MarketingSubscription(institution_id=institution_uuid, email=email)
        db.add(row)
    row.subscribed = subscribed
    if subscribed:
        row.resubscribed_at = now
        row.unsubscribe_reason = None
        row.unsubscribe_comment = None
    else:
        row.unsubscribed_at = now
    contacts = (await db.execute(select(Contact).where(and_(
        Contact.institution_id == institution_uuid,
        func.lower(Contact.email) == email,
    )))).scalars().all()
    for contact in contacts:
        contact.marketing_consent = subscribed
        contact.marketing_consent_at = now if subscribed else None
    await db.commit()
    return row


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><html lang="cs"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
    <style>body{{font-family:system-ui,sans-serif;background:#f8fafc;color:#172033;margin:0;padding:32px}}
    main{{max-width:620px;margin:8vh auto;background:white;padding:32px;border:1px solid #e2e8f0;border-radius:16px}}
    button{{background:#1e293b;color:white;border:0;border-radius:8px;padding:12px 18px;cursor:pointer}}
    textarea{{width:100%;box-sizing:border-box;margin:8px 0 16px;padding:10px}}label{{display:block;margin:10px 0}}</style>
    </head><body><main><h1>{html.escape(title)}</h1>{body}</main></body></html>""")


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    institution_id, email = _decode(token)
    institution = (await db.execute(select(Institution).where(Institution.id == uuid.UUID(institution_id)))).scalar_one_or_none()
    if not institution:
        raise HTTPException(404, "Instituce nebyla nalezena.")
    await _set_subscription(db, institution_id, email, False)
    options = "".join(
        f'<label><input type="radio" name="reason" value="{key}"> {html.escape(label)}</label>'
        for key, label in REASONS.items()
    )
    safe_token = html.escape(token, quote=True)
    return _page("Odběr byl zrušen", f"""
      <p>Adresa <strong>{html.escape(email)}</strong> už nebude dostávat propagační e-maily instituce <strong>{html.escape(institution.name)}</strong>.</p>
      <p>Pokud chcete, pomozte nám nepovinnou zpětnou vazbou:</p>
      <form method="post" action="/api/marketing/unsubscribe-feedback"><input type="hidden" name="token" value="{safe_token}">{options}
      <textarea name="comment" maxlength="1000" placeholder="Volitelný komentář"></textarea><button type="submit">Odeslat zpětnou vazbu</button></form>
      <form method="post" action="/api/marketing/restore" style="margin-top:24px"><input type="hidden" name="token" value="{safe_token}">
      <button type="submit">Obnovit odběr</button></form>""")


@router.post("/unsubscribe-feedback", response_class=HTMLResponse)
async def unsubscribe_feedback(token: str = Form(...), reason: str = Form(""), comment: str = Form(""), db: AsyncSession = Depends(get_db)):
    institution_id, email = _decode(token)
    row = await _set_subscription(db, institution_id, email, False)
    row.unsubscribe_reason = reason if reason in REASONS else None
    row.unsubscribe_comment = comment.strip()[:1000] or None
    await db.commit()
    return _page("Děkujeme za zpětnou vazbu", "<p>Vaše odpověď byla uložena. Odběr zůstává zrušený.</p>")


@router.post("/restore", response_class=HTMLResponse)
async def restore(token: str = Form(...), db: AsyncSession = Depends(get_db)):
    institution_id, email = _decode(token)
    institution = (await db.execute(select(Institution).where(Institution.id == uuid.UUID(institution_id)))).scalar_one_or_none()
    await _set_subscription(db, institution_id, email, True)
    return _page("Odběr byl obnoven", f"<p>Znovu budete dostávat novinky instituce <strong>{html.escape(institution.name if institution else 'instituce')}</strong>.</p>")


@router.get("/subscription-stats")
async def subscription_stats(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    institution_id = current_user["institution_id"]
    subscribed_contacts = (await db.execute(select(func.count(Contact.id)).where(and_(
        Contact.institution_id == institution_id, Contact.marketing_consent.is_(True)
    )))).scalar() or 0
    rows = (await db.execute(select(MarketingSubscription).where(
        MarketingSubscription.institution_id == institution_id
    ))).scalars().all()
    reasons = {}
    for row in rows:
        if not row.subscribed and row.unsubscribe_reason:
            label = REASONS.get(row.unsubscribe_reason, row.unsubscribe_reason)
            reasons[label] = reasons.get(label, 0) + 1
    month_keys = []
    cursor = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for offset in range(11, -1, -1):
        year = cursor.year
        month = cursor.month - offset
        while month <= 0:
            year -= 1
            month += 12
        month_keys.append(f"{year:04d}-{month:02d}")
    trend = {key: {"month": key, "new_subscriptions": 0, "unsubscribed": 0, "restored": 0} for key in month_keys}
    contacts = (await db.execute(select(Contact.marketing_consent_at).where(and_(
        Contact.institution_id == institution_id,
        Contact.marketing_consent_at.isnot(None),
    )))).scalars().all()
    for consent_at in contacts:
        key = consent_at.strftime("%Y-%m")
        if key in trend:
            trend[key]["new_subscriptions"] += 1
    for row in rows:
        if row.unsubscribed_at:
            key = row.unsubscribed_at.strftime("%Y-%m")
            if key in trend:
                trend[key]["unsubscribed"] += 1
        if row.resubscribed_at:
            key = row.resubscribed_at.strftime("%Y-%m")
            if key in trend:
                trend[key]["restored"] += 1
    return {
        "subscribers": subscribed_contacts,
        "unsubscribed": sum(1 for row in rows if not row.subscribed),
        "restored": sum(1 for row in rows if row.resubscribed_at is not None),
        "unsubscribe_reasons": reasons,
        "trend": list(trend.values()),
    }
