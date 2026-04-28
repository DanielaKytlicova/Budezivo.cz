"""Event payment gateway routes.

Public flow:
1. Applicant submits event application → `EventApplication` created with VS.
2. Applicant clicks "Zaplatit online" on confirmation page → frontend calls
   POST /api/event-payments/initiate {institution_id, application_id} and
   receives a redirect_url to provider (or our mock page).
3. Provider POSTs webhook → /api/event-payments/webhook/comgate.
4. Webhook updates EventPayment.status, and for auto_confirm_paid enabled
   institutions auto-confirms the application.
5. Provider redirects user back → /payment/return?vs=...&status=... on frontend,
   which polls GET /api/event-payments/by-vs/{vs} until status is final.

Feature gated by `events_payments` (PRO+).
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.supabase import get_db
from database.models import (
    EventApplication, EventPayment, Event, EventDate, Institution,
    InstitutionPaymentSettings,
)
from services.payment_gateways import get_gateway_for_institution, GatewayMode
from services.plan_service import has_feature_access

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/event-payments", tags=["Event Payments"])


# ---- Pydantic ----

class InitiateBody(BaseModel):
    institution_id: str
    application_id: str


# ---- Helpers ----

def _to_dict(obj) -> dict:
    if obj is None:
        return None
    d = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name)
        if isinstance(v, uuid.UUID):
            v = str(v)
        elif isinstance(v, datetime):
            v = v.isoformat()
        d[c.name] = v
    return d


async def _get_institution_and_check(db: AsyncSession, inst_id: str) -> Institution:
    inst_result = await db.execute(select(Institution).where(Institution.id == inst_id))
    inst = inst_result.scalar_one_or_none()
    if not inst or inst.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")
    if not has_feature_access(inst.plan or "free", inst.plan_status or "inactive", "events_payments"):
        raise HTTPException(status_code=402, detail="Online platby vyžadují plán PRO+")
    return inst


def _build_public_base_url(request: Request) -> str:
    """Detect our public base URL from the incoming request (respecting proxy headers).

    Used for the WEBHOOK URL (must point to the backend / API host).
    """
    import os
    env = os.environ.get("PUBLIC_BASE_URL")
    if env:
        return env.rstrip("/")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.hostname
    return f"{proto}://{host}"


def _build_frontend_base_url(request: Request) -> str:
    """Detect the public-facing FRONTEND base URL (where the user's browser is).

    Strategy:
    1. Explicit env var ``FRONTEND_BASE_URL`` (e.g. ``https://budezivo.cz``).
    2. The ``Origin`` header of the AJAX call from the frontend.
    3. The ``Referer`` header (best-effort).
    4. Strip a leading ``api.`` from the request host as last-resort heuristic.
    """
    import os
    from urllib.parse import urlsplit
    env = os.environ.get("FRONTEND_BASE_URL")
    if env:
        return env.rstrip("/")
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("referer")
    if referer:
        parts = urlsplit(referer)
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.hostname or ""
    if host.startswith("api."):
        host = host[4:]
    return f"{proto}://{host}"


# ---- Initiate payment ----

@router.post("/initiate")
async def initiate_payment(
    body: InitiateBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Start a gateway payment for an already-submitted event application."""
    inst = await _get_institution_and_check(db, body.institution_id)

    # Load application
    app_result = await db.execute(
        select(EventApplication).where(and_(
            EventApplication.id == body.application_id,
            EventApplication.institution_id == inst.id,
        ))
    )
    application = app_result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Přihláška nenalezena")
    if application.payment_status == "paid":
        return {"already_paid": True, "application_id": str(application.id)}
    if not application.total_amount or application.total_amount <= 0:
        raise HTTPException(status_code=400, detail="Tato přihláška není placená")

    gateway, settings, mode = await get_gateway_for_institution(db, str(inst.id))
    if gateway is None:
        raise HTTPException(
            status_code=400,
            detail="Platební brána není nakonfigurována. Kontaktujte instituci.",
        )

    base = _build_public_base_url(request)
    frontend_base = _build_frontend_base_url(request)
    return_url = f"{frontend_base}/payment/return"
    webhook_url = f"{base}/api/event-payments/webhook/{gateway.provider_key}"

    # Fetch event for description
    ev_res = await db.execute(select(Event).where(Event.id == application.event_id))
    event = ev_res.scalar_one_or_none()
    desc = (event.name if event else "Přihláška")[:40]

    result = await gateway.initiate(
        amount_czk=float(application.total_amount),
        variable_symbol=application.variable_symbol or "",
        description=desc,
        ref_id=str(application.id),
        return_url=return_url,
        webhook_url=webhook_url,
        customer_email=application.applicant_email,
    )
    if not result.ok:
        raise HTTPException(status_code=502, detail=result.error or "Platební brána selhala")

    # Persist/Update EventPayment record
    pay_result = await db.execute(
        select(EventPayment).where(and_(
            EventPayment.application_id == application.id,
            EventPayment.provider == gateway.provider_key,
        ))
    )
    payment = pay_result.scalar_one_or_none()
    if not payment:
        payment = EventPayment(
            application_id=application.id,
            institution_id=inst.id,
            provider=gateway.provider_key,
            amount=application.total_amount,
            currency="CZK",
            variable_symbol=application.variable_symbol,
        )
        db.add(payment)
    payment.provider_payment_id = result.transaction_id
    payment.status = "pending"
    application.payment_status = "pending"
    await db.commit()

    return {
        "ok": True,
        "redirect_url": result.redirect_url,
        "transaction_id": result.transaction_id,
        "mode": result.mode.value,
        "application_id": str(application.id),
        "variable_symbol": application.variable_symbol,
    }


# ---- Webhook ----

async def _process_payment_paid(db: AsyncSession, payment: EventPayment, transaction_id: str | None):
    """Mark EventPayment paid + auto-confirm application if institution has auto_confirm_paid."""
    now = datetime.now(timezone.utc)
    payment.status = "paid"
    payment.paid_at = now
    if transaction_id:
        payment.provider_payment_id = transaction_id

    app_result = await db.execute(
        select(EventApplication).where(EventApplication.id == payment.application_id)
    )
    application = app_result.scalar_one_or_none()
    if not application:
        return
    application.payment_status = "paid"

    # Auto-confirm registration if institution has the feature + it's currently pending
    inst_res = await db.execute(select(Institution).where(Institution.id == application.institution_id))
    inst = inst_res.scalar_one_or_none()
    if inst and has_feature_access(inst.plan or "free", inst.plan_status or "inactive", "auto_confirm_paid"):
        if application.status in (None, "pending"):
            application.status = "approved"
            logger.info(f"Auto-confirmed application {application.id} after successful payment.")


@router.post("/webhook/comgate")
async def comgate_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Comgate webhook endpoint. Authenticates via merchant+secret from payload."""
    # Comgate posts form-urlencoded
    form = await request.form()
    payload = {k: v for k, v in form.items()}
    logger.info(f"[Comgate webhook] received: refId={payload.get('refId')} status={payload.get('status')}")

    ref_id = payload.get("refId")
    trans_id = payload.get("transId")
    if not ref_id:
        return Response(content="code=1&message=missing refId", media_type="text/plain", status_code=400)

    # Load payment by application ref_id
    try:
        app_uuid = uuid.UUID(ref_id)
    except Exception:
        return Response(content="code=1&message=invalid refId", media_type="text/plain", status_code=400)

    pay_result = await db.execute(
        select(EventPayment).where(and_(
            EventPayment.application_id == app_uuid,
            EventPayment.provider == "comgate",
        ))
    )
    payment = pay_result.scalar_one_or_none()
    if not payment:
        return Response(content="code=1&message=payment not found", media_type="text/plain", status_code=404)

    # Build gateway with THIS institution's credentials (per-tenant auth)
    gateway, _settings, _mode = await get_gateway_for_institution(db, str(payment.institution_id))
    if not gateway:
        return Response(content="code=1&message=gateway not configured", media_type="text/plain", status_code=500)

    # Hardening: in MOCK mode the gateway has no shared secret to validate,
    # so we refuse external webhooks to prevent spoofed "paid" signals.
    # Tests / integrators must use POST /api/event-payments/mock/complete instead.
    from services.payment_gateways import GatewayMode as _GM
    if _mode == _GM.MOCK:
        logger.warning(f"[Comgate webhook] rejected in MOCK mode for inst {payment.institution_id}")
        return Response(content="code=1&message=mock mode - use /mock/complete", media_type="text/plain", status_code=403)

    try:
        status = await gateway.parse_webhook(payload)
    except ValueError as e:
        logger.warning(f"[Comgate webhook] auth failed: {e}")
        return Response(content="code=1&message=invalid signature", media_type="text/plain", status_code=403)

    if status.paid:
        await _process_payment_paid(db, payment, status.transaction_id or trans_id)
    elif status.failed:
        payment.status = "failed"
        if status.transaction_id:
            payment.provider_payment_id = status.transaction_id
    else:
        payment.status = "pending"

    await db.commit()
    # Comgate expects plain-text ack
    return Response(content="code=0&message=OK", media_type="text/plain")


# ---- Mock simulator (only works when mode=mock) ----

class MockCompleteBody(BaseModel):
    institution_id: str
    variable_symbol: str
    outcome: str = "paid"  # paid | cancelled


@router.post("/mock/complete")
async def mock_complete(body: MockCompleteBody, db: AsyncSession = Depends(get_db)):
    """Simulate a successful/cancelled payment in mock mode.

    Only allowed when the institution's gateway resolves to MOCK mode.
    Mirrors what a real webhook would do for the same payment.
    """
    gateway, _settings, mode = await get_gateway_for_institution(db, body.institution_id)
    if gateway is None or mode != GatewayMode.MOCK:
        raise HTTPException(status_code=400, detail="Mock simulátor je dostupný pouze v mock režimu")

    pay_result = await db.execute(
        select(EventPayment).where(and_(
            EventPayment.institution_id == body.institution_id,
            EventPayment.variable_symbol == body.variable_symbol,
            EventPayment.provider == gateway.provider_key,
        )).order_by(EventPayment.created_at.desc()).limit(1)
    )
    payment = pay_result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Platba nenalezena")

    if body.outcome == "paid":
        await _process_payment_paid(db, payment, payment.provider_payment_id)
        await db.commit()
        return {"ok": True, "status": "paid"}

    payment.status = "failed"
    await db.commit()
    return {"ok": True, "status": "failed"}


# ---- Status polling (public) ----

@router.get("/by-ref/{ref_id}")
async def get_payment_by_ref(
    ref_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Public lookup by ``refId`` (= application_id).

    Used by the customer-return page when Comgate-portal-configured URLs are
    in play (they substitute ``${refId}`` automatically without needing the
    institution_id). We resolve institution from the application itself.
    """
    try:
        app_uuid = uuid.UUID(ref_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Neplatný refId")

    pay_result = await db.execute(
        select(EventPayment).where(
            EventPayment.application_id == app_uuid
        ).order_by(EventPayment.created_at.desc()).limit(1)
    )
    payment = pay_result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Platba nenalezena")

    app_res = await db.execute(select(EventApplication).where(EventApplication.id == payment.application_id))
    app = app_res.scalar_one_or_none()

    return {
        "payment_status": payment.status,
        "amount": payment.amount,
        "currency": payment.currency,
        "provider": payment.provider,
        "variable_symbol": payment.variable_symbol,
        "institution_id": str(payment.institution_id),
        "application_id": str(payment.application_id),
        "application_status": app.status if app else None,
        "application_payment_status": app.payment_status if app else None,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
    }


@router.get("/by-vs/{institution_id}/{variable_symbol}")
async def get_payment_by_vs(
    institution_id: str,
    variable_symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """Public lookup so the return page can poll for final status."""
    pay_result = await db.execute(
        select(EventPayment).where(and_(
            EventPayment.institution_id == institution_id,
            EventPayment.variable_symbol == variable_symbol,
        )).order_by(EventPayment.created_at.desc()).limit(1)
    )
    payment = pay_result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Platba nenalezena")

    app_res = await db.execute(select(EventApplication).where(EventApplication.id == payment.application_id))
    app = app_res.scalar_one_or_none()

    return {
        "payment_status": payment.status,
        "amount": payment.amount,
        "currency": payment.currency,
        "provider": payment.provider,
        "variable_symbol": payment.variable_symbol,
        "application_id": str(payment.application_id),
        "application_status": app.status if app else None,
        "application_payment_status": app.payment_status if app else None,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
    }
