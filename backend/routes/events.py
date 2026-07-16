"""
Events module API routes (Pilot feature).
Handles: Events CRUD, EventDates, Applications, Payments, Feature flags.
"""
import uuid
import random
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, List
from urllib.parse import quote as url_quote
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, text

# A10 — application statuses that occupy a real capacity seat (waitlist + rejected
# do NOT count against capacity).
OCCUPYING_STATUSES = ('pending', 'approved')


async def _resolve_application_status(db, event, event_date_uuid) -> str:
    """Atomically decide whether a new application gets a confirmed seat
    ('pending') or goes onto the WAITLIST ('waitlist').

    Uses a transaction-scoped PostgreSQL advisory lock keyed on the event/date so
    concurrent submissions can't overbook (race-safe). Capacity <= 0 / None means
    unlimited → always 'pending'.
    """
    if event_date_uuid:
        ed = (await db.execute(
            select(EventDate).where(EventDate.id == event_date_uuid)
        )).scalar_one_or_none()
        capacity = (ed.capacity_override if ed and ed.capacity_override is not None
                    else event.capacity)
    else:
        capacity = event.capacity

    if not capacity or capacity <= 0:
        return 'pending'

    lock_basis = str(event_date_uuid) if event_date_uuid else str(event.id)
    lock_key = int(hashlib.sha256(lock_basis.encode()).hexdigest()[:15], 16)
    await db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": lock_key})

    if event_date_uuid:
        cond = and_(
            EventApplication.event_date_id == event_date_uuid,
            EventApplication.status.in_(OCCUPYING_STATUSES),
        )
    else:
        cond = and_(
            EventApplication.event_id == event.id,
            EventApplication.event_date_id.is_(None),
            EventApplication.status.in_(OCCUPYING_STATUSES),
        )
    occupied = (await db.execute(
        select(func.count(EventApplication.id)).where(cond)
    )).scalar() or 0

    return 'waitlist' if occupied >= capacity else 'pending'

from database.supabase import get_db
from database.models import (
    Event, EventDate, EventApplication, EventPayment,
    InstitutionPaymentSettings, FeatureFlag, Institution
)
from core.security import get_current_user
from services.feature_flags import is_feature_enabled
from services.plan_service import require_feature
from services.payment_gateways.factory import _detect_mode
from services.contact_service import upsert_contact_from_event_application
from services.email_service import trigger_event_application_confirmation
import re as _re

router = APIRouter(prefix="/events", tags=["Events"])
logger = logging.getLogger(__name__)

FEATURE_KEY = "events_module"


# ============ Guards ============

async def require_events_module(db: AsyncSession, institution_id: str):
    """Raise 404 if events module is not enabled for institution."""
    enabled = await is_feature_enabled(db, FEATURE_KEY, institution_id)
    if not enabled:
        raise HTTPException(status_code=404, detail="Not found")


# ============ Pydantic Schemas ============

class FormFieldSchema(BaseModel):
    id: str = ""
    type: str = "text"
    label: str = ""
    required: bool = False
    options: Optional[list] = None
    order: int = 0


class EventCreate(BaseModel):
    name: str
    type: str = "event"
    description: Optional[str] = None
    capacity: int = 30
    price: float = 0.0
    currency: str = "CZK"
    is_active: bool = True
    image_url: Optional[str] = None
    form_fields: List[dict] = []
    allowed_payment_methods: Optional[List[str]] = None


class EventUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None
    image_url: Optional[str] = None
    form_fields: Optional[List[dict]] = None
    allowed_payment_methods: Optional[List[str]] = None


class EventDateCreate(BaseModel):
    start_datetime: str
    end_datetime: str
    capacity_override: Optional[int] = None


class ApplicationCreate(BaseModel):
    event_id: str
    event_date_id: Optional[str] = None
    applicant_data: dict = {}
    applicant_email: Optional[str] = None
    applicant_name: Optional[str] = None
    note: Optional[str] = None
    marketing_consent: bool = False
    payment_method: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None


class PaymentSettingsUpdate(BaseModel):
    payment_mode: Optional[str] = None
    allowed_methods: Optional[List[str]] = None
    confirm_disable: bool = False
    provider: Optional[str] = None
    iban: Optional[str] = None
    account_number: Optional[str] = None
    bank_code: Optional[str] = None
    account_name: Optional[str] = None
    gateway_api_key: Optional[str] = None
    gateway_secret: Optional[str] = None


# ============ Helpers ============

def _to_dict(obj) -> dict:
    """Convert SQLAlchemy model to dict."""
    result = {}
    for c in obj.__table__.columns:
        value = getattr(obj, c.name)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, datetime):
            value = value.isoformat()
        result[c.name] = value
    return result


def _generate_variable_symbol() -> str:
    """Generate a random 10-digit variable symbol (no uniqueness guarantee).

    Prefer `_generate_unique_variable_symbol` which checks for collisions.
    """
    return str(random.randint(1000000000, 9999999999))


async def _generate_unique_variable_symbol(db, institution_id, max_attempts: int = 12) -> str:
    """Generate a 10-digit VS that is unique within the institution.

    VS is matched per-tenant (institution_id + variable_symbol) by the payment
    lookups/reconciliation, so a duplicate inside the same institution could
    mis-link a manual/QR bank transfer to the wrong application. We retry until
    we find a free VS among existing EventApplications of this institution.
    """
    for _ in range(max_attempts):
        vs = _generate_variable_symbol()
        existing = await db.execute(
            select(EventApplication.id).where(and_(
                EventApplication.institution_id == institution_id,
                EventApplication.variable_symbol == vs,
            )).limit(1)
        )
        if existing.scalar_one_or_none() is None:
            return vs
    # Astronomically unlikely fallback (institution would need ~billions of rows).
    logger.warning(f"VS uniqueness fallback after {max_attempts} attempts for institution {institution_id}")
    return _generate_variable_symbol()


def _generate_qr_payload(
    account_number: str,
    bank_code: str,
    amount: float,
    currency: str,
    variable_symbol: str,
    message: str = "",
) -> str:
    """Generate SPD QR payment string."""
    # Format: CZ IBAN from account_number/bank_code
    # Or use raw account for SPD
    acc = f"{account_number}/{bank_code}" if bank_code else account_number
    parts = [
        "SPD*1.0",
        f"ACC:CZ{acc}",
        f"AM:{amount:.2f}",
        f"CC:{currency}",
        f"X-VS:{variable_symbol}",
    ]
    if message:
        parts.append(f"MSG:{message[:60]}")
    return "*".join(parts)


# ============ Feature Flag Check ============

VALID_PAYMENT_METHODS = ("qr", "gateway", "cash")

PAYMENT_METHOD_LABELS = {
    "qr": "QR platba / bankovní převod",
    "gateway": "Platební brána Comgate",
    "cash": "Platba na místě",
    "free": "Zdarma",
}


async def _get_payment_settings(db: AsyncSession, inst_uuid):
    return (await db.execute(
        select(InstitutionPaymentSettings).where(
            InstitutionPaymentSettings.institution_id == inst_uuid
        )
    )).scalar_one_or_none()


def _derive_institution_methods(settings) -> list:
    """Institution's globally-allowed payment methods (legacy payment_mode fallback)."""
    if settings and settings.allowed_methods:
        return [m for m in settings.allowed_methods if m in VALID_PAYMENT_METHODS]
    if settings:
        pm = settings.payment_mode or "qr"
        if pm == "both":
            return ["qr", "gateway"]
        if pm == "gateway":
            return ["gateway"]
        return ["qr"]
    return []


def _method_is_configured(settings, method: str) -> bool:
    """Whether a method has the technical config it requires to be enabled."""
    if method == "qr":
        return bool(settings and (settings.account_number or "").strip())
    if method == "gateway":
        return bool(
            settings
            and (settings.provider or "").strip().lower() == "comgate"
            and (settings.gateway_api_key or "").strip()
            and (settings.gateway_secret or "").strip()
        )
    if method == "cash":
        return True
    return False


def _event_methods(event, inst_methods: list) -> list:
    """Event's offered methods, always intersected with what the institution allows."""
    raw = event.allowed_payment_methods
    if not raw:
        return list(inst_methods)  # legacy paid event → inherit institution methods
    return [m for m in raw if m in inst_methods]


@router.get("/check-access")
async def check_events_access(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Check if current user has access to events module."""
    enabled = await is_feature_enabled(db, FEATURE_KEY, current_user["institution_id"])
    return {"enabled": enabled}


# ============ Events CRUD ============

@router.get("")
async def list_events(
    include_archived: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _guard=Depends(require_feature("events_basic")),
):
    """List all events for institution."""
    await require_events_module(db, current_user["institution_id"])
    inst_uuid = uuid.UUID(current_user["institution_id"])

    query = select(Event).where(Event.institution_id == inst_uuid)
    if not include_archived:
        query = query.where(Event.is_archived == False)
    query = query.order_by(Event.created_at.desc())

    result = await db.execute(query)
    events = result.scalars().all()

    out = []
    for ev in events:
        ev_dict = _to_dict(ev)
        # Count dates and applications
        dates_count = await db.execute(
            select(func.count(EventDate.id)).where(EventDate.event_id == ev.id)
        )
        apps_count = await db.execute(
            select(func.count(EventApplication.id)).where(EventApplication.event_id == ev.id)
        )
        ev_dict["dates_count"] = dates_count.scalar() or 0
        ev_dict["applications_count"] = apps_count.scalar() or 0
        out.append(ev_dict)

    return out


async def _institution_has_payment_method(db: AsyncSession, inst_uuid) -> bool:
    """True if the institution has at least one usable payment method configured
    (bank account for QR/transfer, or an active payment gateway)."""
    ps = (await db.execute(
        select(InstitutionPaymentSettings).where(InstitutionPaymentSettings.institution_id == inst_uuid)
    )).scalar_one_or_none()
    if not ps:
        return False
    if ps.account_number:
        return True
    if getattr(ps, "comgate_enabled", False) or getattr(ps, "provider", None):
        return True
    return False



@router.post("")
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _guard=Depends(require_feature("events_basic")),
):
    """Create a new event."""
    await require_events_module(db, current_user["institution_id"])

    inst_uuid = uuid.UUID(current_user["institution_id"])
    methods = None
    if (data.price or 0) > 0:
        settings = await _get_payment_settings(db, inst_uuid)
        inst_methods = [m for m in _derive_institution_methods(settings) if _method_is_configured(settings, m)]
        if not inst_methods:
            raise HTTPException(
                status_code=400,
                detail="Pro placenou akci nejprve nastavte alespoň jednu platební metodu (číslo účtu, platební brána nebo platba na místě).",
            )
        methods = data.allowed_payment_methods if data.allowed_payment_methods else list(inst_methods)
        invalid = [m for m in methods if m not in inst_methods]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Metody nejsou institucí povoleny: {', '.join(invalid)}",
            )
        if not methods:
            raise HTTPException(status_code=400, detail="Vyberte alespoň jednu platební metodu.")

    event = Event(
        institution_id=inst_uuid,
        name=data.name,
        type=data.type,
        description=data.description,
        capacity=data.capacity,
        price=data.price,
        currency=data.currency,
        is_active=data.is_active,
        image_url=data.image_url,
        form_fields=data.form_fields,
        allowed_payment_methods=methods,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return _to_dict(event)


@router.get("/{event_id}")
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get single event with dates."""
    await require_events_module(db, current_user["institution_id"])
    inst_uuid = uuid.UUID(current_user["institution_id"])

    result = await db.execute(
        select(Event).where(and_(
            Event.id == uuid.UUID(event_id),
            Event.institution_id == inst_uuid,
        ))
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Událost nenalezena")

    ev_dict = _to_dict(event)

    # Get dates
    dates_result = await db.execute(
        select(EventDate).where(EventDate.event_id == event.id).order_by(EventDate.start_datetime)
    )
    ev_dict["dates"] = [_to_dict(d) for d in dates_result.scalars().all()]

    # Get applications count
    apps_count = await db.execute(
        select(func.count(EventApplication.id)).where(EventApplication.event_id == event.id)
    )
    ev_dict["applications_count"] = apps_count.scalar() or 0

    return ev_dict


@router.put("/{event_id}")
async def update_event(
    event_id: str,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update an event."""
    await require_events_module(db, current_user["institution_id"])
    inst_uuid = uuid.UUID(current_user["institution_id"])

    result = await db.execute(
        select(Event).where(and_(
            Event.id == uuid.UUID(event_id),
            Event.institution_id == inst_uuid,
        ))
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Událost nenalezena")

    update_data = data.model_dump(exclude_unset=True)

    # Guard: switching a PAID event to FREE while payments already exist must not
    # silently wipe payment history. Block and report the affected count.
    new_price = update_data.get("price")
    if new_price is not None and (new_price or 0) <= 0 and (event.price or 0) > 0:
        paid_count = (await db.execute(
            select(func.count(EventApplication.id)).where(and_(
                EventApplication.event_id == event.id,
                EventApplication.payment_status.in_(["pending", "paid"]),
            ))
        )).scalar() or 0
        if paid_count > 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Akci nelze změnit na bezplatnou: existuje {paid_count} přihlášek se zahájenou "
                    f"nebo dokončenou platbou. Vyřešte je (např. refundaci) individuálně."
                ),
            )

    # Payment-method validation for the resulting (post-update) state.
    resulting_price = new_price if new_price is not None else event.price
    if resulting_price is not None and (resulting_price or 0) > 0:
        settings = await _get_payment_settings(db, inst_uuid)
        inst_methods = [m for m in _derive_institution_methods(settings) if _method_is_configured(settings, m)]
        if not inst_methods:
            raise HTTPException(
                status_code=400,
                detail="Pro placenou akci nejprve nastavte alespoň jednu platební metodu (číslo účtu, platební brána nebo platba na místě).",
            )
        methods = update_data.get("allowed_payment_methods")
        if methods is None:
            methods = event.allowed_payment_methods or list(inst_methods)
        invalid = [m for m in methods if m not in inst_methods]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Metody nejsou institucí povoleny: {', '.join(invalid)}")
        if not methods:
            raise HTTPException(status_code=400, detail="Vyberte alespoň jednu platební metodu.")
        update_data["allowed_payment_methods"] = methods
    elif resulting_price is not None and (resulting_price or 0) <= 0:
        update_data["allowed_payment_methods"] = None  # free event → no methods

    for key, value in update_data.items():
        setattr(event, key, value)
    event.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(event)
    return _to_dict(event)


@router.delete("/{event_id}")
async def delete_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete an event."""
    await require_events_module(db, current_user["institution_id"])
    inst_uuid = uuid.UUID(current_user["institution_id"])

    result = await db.execute(
        select(Event).where(and_(
            Event.id == uuid.UUID(event_id),
            Event.institution_id == inst_uuid,
        ))
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Událost nenalezena")

    await db.delete(event)
    await db.commit()
    return {"message": "Událost smazána"}


# ============ Event Dates ============

@router.post("/{event_id}/dates")
async def add_event_date(
    event_id: str,
    data: EventDateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Add a date/time to an event."""
    await require_events_module(db, current_user["institution_id"])

    event_date = EventDate(
        event_id=uuid.UUID(event_id),
        start_datetime=datetime.fromisoformat(data.start_datetime),
        end_datetime=datetime.fromisoformat(data.end_datetime),
        capacity_override=data.capacity_override,
    )
    db.add(event_date)
    await db.commit()
    await db.refresh(event_date)
    return _to_dict(event_date)


@router.delete("/{event_id}/dates/{date_id}")
async def remove_event_date(
    event_id: str,
    date_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Remove a date from an event."""
    await require_events_module(db, current_user["institution_id"])

    result = await db.execute(
        select(EventDate).where(and_(
            EventDate.id == uuid.UUID(date_id),
            EventDate.event_id == uuid.UUID(event_id),
        ))
    )
    ed = result.scalar_one_or_none()
    if not ed:
        raise HTTPException(status_code=404, detail="Termín nenalezen")

    await db.delete(ed)
    await db.commit()
    return {"message": "Termín odstraněn"}


# ============ Applications ============

@router.get("/{event_id}/applications")
async def list_applications(
    event_id: str,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List applications for an event."""
    await require_events_module(db, current_user["institution_id"])

    query = select(EventApplication).where(
        EventApplication.event_id == uuid.UUID(event_id)
    )
    if status:
        query = query.where(EventApplication.status == status)
    query = query.order_by(EventApplication.created_at.desc())

    result = await db.execute(query)
    apps = result.scalars().all()
    return [_to_dict(a) for a in apps]


@router.get("/applications/all")
async def list_all_applications(
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all applications across all events for the institution."""
    await require_events_module(db, current_user["institution_id"])
    inst_uuid = uuid.UUID(current_user["institution_id"])

    query = select(EventApplication, Event.name.label("event_name")).join(
        Event, EventApplication.event_id == Event.id
    ).where(EventApplication.institution_id == inst_uuid)

    if status:
        query = query.where(EventApplication.status == status)
    if payment_status:
        query = query.where(EventApplication.payment_status == payment_status)

    query = query.order_by(EventApplication.created_at.desc())
    result = await db.execute(query)

    out = []
    for app, event_name in result.all():
        d = _to_dict(app)
        d["event_name"] = event_name
        out.append(d)
    return out


@router.put("/applications/{application_id}/status")
async def update_application_status(
    application_id: str,
    data: ApplicationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update application status (admin)."""
    await require_events_module(db, current_user["institution_id"])

    result = await db.execute(
        select(EventApplication).where(and_(
            EventApplication.id == uuid.UUID(application_id),
            EventApplication.institution_id == uuid.UUID(current_user["institution_id"]),
        ))
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Přihláška nenalezena")

    if data.status:
        app.status = data.status

    if data.payment_status:
        # Manually marking a payment as PAID is restricted (admin/spravce/pokladni) and audited.
        marking_paid = data.payment_status == "paid" and app.payment_status != "paid"
        if marking_paid and current_user.get("role") not in ("admin", "spravce", "pokladni"):
            raise HTTPException(status_code=403, detail="Nemáte oprávnění označit platbu jako zaplacenou.")
        app.payment_status = data.payment_status
        if marking_paid:
            now = datetime.now(timezone.utc)
            app.paid_marked_by_email = current_user.get("email") or ""
            app.paid_marked_at = now
            from routes.audit import log_action
            await log_action(
                db,
                institution_id=current_user["institution_id"],
                user_id=current_user["user_id"],
                user_email=current_user.get("email", ""),
                action="mark_paid",
                entity_type="event_application",
                entity_id=str(app.id),
                details={"payment_method": app.payment_method, "amount": app.total_amount},
            )
    app.updated_at = datetime.now(timezone.utc)

    await db.commit()
    return _to_dict(app)


# ============ Exports ============

@router.get("/{event_id}/export/xlsx")
async def export_applications_xlsx(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _guard=Depends(require_feature("data_export")),
):
    """Export applications as styled XLSX."""
    await require_events_module(db, current_user["institution_id"])
    inst_uuid = uuid.UUID(current_user["institution_id"])

    result = await db.execute(
        select(Event).where(and_(Event.id == uuid.UUID(event_id), Event.institution_id == inst_uuid))
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Událost nenalezena")

    apps_result = await db.execute(
        select(EventApplication).where(EventApplication.event_id == event.id).order_by(EventApplication.created_at.desc())
    )
    applications = [_to_dict(a) for a in apps_result.scalars().all()]

    from services.export_service import generate_xlsx
    buffer = generate_xlsx(_to_dict(event), applications)

    filename = f"prihlasky_{event.name[:30]}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{url_quote(filename)}"},
    )


@router.get("/{event_id}/export/csv")
async def export_applications_csv(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _guard=Depends(require_feature("data_export")),
):
    """Export applications as CSV."""
    await require_events_module(db, current_user["institution_id"])
    inst_uuid = uuid.UUID(current_user["institution_id"])

    result = await db.execute(
        select(Event).where(and_(Event.id == uuid.UUID(event_id), Event.institution_id == inst_uuid))
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Událost nenalezena")

    apps_result = await db.execute(
        select(EventApplication).where(EventApplication.event_id == event.id).order_by(EventApplication.created_at.desc())
    )
    applications = [_to_dict(a) for a in apps_result.scalars().all()]

    from services.export_service import generate_csv
    buffer = generate_csv(_to_dict(event), applications)

    filename = f"prihlasky_{event.name[:30]}_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        buffer,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{url_quote(filename)}"},
    )


@router.get("/applications/{application_id}/pdf")
async def export_application_pdf(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Generate PDF confirmation for a single application."""
    await require_events_module(db, current_user["institution_id"])
    inst_uuid = uuid.UUID(current_user["institution_id"])

    app_result = await db.execute(
        select(EventApplication).where(and_(
            EventApplication.id == uuid.UUID(application_id),
            EventApplication.institution_id == inst_uuid,
        ))
    )
    application = app_result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Přihláška nenalezena")

    event_result = await db.execute(select(Event).where(Event.id == application.event_id))
    event = event_result.scalar_one_or_none()

    event_date = None
    if application.event_date_id:
        ed_result = await db.execute(select(EventDate).where(EventDate.id == application.event_date_id))
        event_date = ed_result.scalar_one_or_none()

    pay_result = await db.execute(
        select(InstitutionPaymentSettings).where(InstitutionPaymentSettings.institution_id == inst_uuid)
    )
    pay_settings = pay_result.scalar_one_or_none()

    from database.models import Institution
    inst_result = await db.execute(select(Institution).where(Institution.id == inst_uuid))
    institution = inst_result.scalar_one_or_none()

    from services.export_service import generate_pdf_confirmation
    buffer = generate_pdf_confirmation(
        _to_dict(application),
        _to_dict(event) if event else {},
        _to_dict(event_date) if event_date else None,
        {"name": institution.name if institution else "Instituce"},
        _to_dict(pay_settings) if pay_settings else None,
    )

    filename = f"potvrzeni_{application.applicant_name or 'prihlaska'}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{url_quote(filename)}"},
    )


# ============ Public Endpoints ============

@router.get("/public/{institution_id}")
async def get_public_events(
    institution_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get active events for public display (no auth required)."""
    enabled = await is_feature_enabled(db, FEATURE_KEY, institution_id)
    if not enabled:
        raise HTTPException(status_code=404, detail="Not found")

    inst_uuid = uuid.UUID(institution_id)
    result = await db.execute(
        select(Event).where(and_(
            Event.institution_id == inst_uuid,
            Event.is_active == True,
            Event.is_archived == False,
        )).order_by(Event.created_at.desc())
    )
    events = result.scalars().all()

    out = []
    for ev in events:
        ev_dict = {
            "id": str(ev.id),
            "name": ev.name,
            "type": ev.type,
            "description": ev.description,
            "capacity": ev.capacity,
            "price": ev.price,
            "currency": ev.currency,
            "image_url": ev.image_url,
            "form_fields": ev.form_fields or [],
        }
        # Get future dates
        dates_result = await db.execute(
            select(EventDate).where(and_(
                EventDate.event_id == ev.id,
                EventDate.start_datetime > datetime.now(timezone.utc),
            )).order_by(EventDate.start_datetime)
        )
        ev_dict["dates"] = [_to_dict(d) for d in dates_result.scalars().all()]

        # Applications count per date
        apps_count = await db.execute(
            select(func.count(EventApplication.id)).where(and_(
                EventApplication.event_id == ev.id,
                EventApplication.status != 'rejected',
            ))
        )
        ev_dict["applications_count"] = apps_count.scalar() or 0
        out.append(ev_dict)

    return out


@router.get("/public/{institution_id}/{event_id}")
async def get_public_event_detail(
    institution_id: str,
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get single public event with dates."""
    enabled = await is_feature_enabled(db, FEATURE_KEY, institution_id)
    if not enabled:
        raise HTTPException(status_code=404, detail="Not found")

    result = await db.execute(
        select(Event).where(and_(
            Event.id == uuid.UUID(event_id),
            Event.institution_id == uuid.UUID(institution_id),
            Event.is_active == True,
        ))
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Událost nenalezena")

    ev_dict = {
        "id": str(event.id),
        "name": event.name,
        "type": event.type,
        "description": event.description,
        "capacity": event.capacity,
        "price": event.price,
        "currency": event.currency,
        "image_url": event.image_url,
        "form_fields": event.form_fields or [],
    }

    dates_result = await db.execute(
        select(EventDate).where(EventDate.event_id == event.id).order_by(EventDate.start_datetime)
    )
    dates = dates_result.scalars().all()
    dates_out = []
    for d in dates:
        dd = _to_dict(d)
        # Count seat-occupying applications for this date (waitlist/rejected excluded)
        cnt = await db.execute(
            select(func.count(EventApplication.id)).where(and_(
                EventApplication.event_date_id == d.id,
                EventApplication.status.in_(OCCUPYING_STATUSES),
            ))
        )
        dd["applications_count"] = cnt.scalar() or 0
        wl = await db.execute(
            select(func.count(EventApplication.id)).where(and_(
                EventApplication.event_date_id == d.id,
                EventApplication.status == 'waitlist',
            ))
        )
        dd["waitlist_count"] = wl.scalar() or 0
        dd["capacity"] = d.capacity_override or event.capacity
        dd["spots_left"] = max(0, dd["capacity"] - dd["applications_count"])
        dd["is_full"] = dd["capacity"] > 0 and dd["applications_count"] >= dd["capacity"]
        dates_out.append(dd)

    ev_dict["dates"] = dates_out

    # Payment methods offered for this event (intersected with institution + config).
    settings = await _get_payment_settings(db, uuid.UUID(institution_id))
    inst_methods = [m for m in _derive_institution_methods(settings) if _method_is_configured(settings, m)]
    is_free = (event.price or 0) <= 0
    methods = [] if is_free else _event_methods(event, inst_methods)
    ev_dict["is_free"] = is_free
    ev_dict["payment_methods"] = methods
    ev_dict["payment_info"] = ({
        "account_number": settings.account_number if settings else None,
        "bank_code": settings.bank_code if settings else None,
        "account_name": settings.account_name if settings else None,
    } if "qr" in methods else {})
    return ev_dict


@router.post("/public/{institution_id}/apply")
async def submit_application(
    institution_id: str,
    data: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Submit a public application for an event."""
    enabled = await is_feature_enabled(db, FEATURE_KEY, institution_id)
    if not enabled:
        raise HTTPException(status_code=404, detail="Not found")

    inst_uuid = uuid.UUID(institution_id)

    # Verify event exists and is active
    result = await db.execute(
        select(Event).where(and_(
            Event.id == uuid.UUID(data.event_id),
            Event.institution_id == inst_uuid,
            Event.is_active == True,
        ))
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Událost nenalezena")

    event_date_uuid = uuid.UUID(data.event_date_id) if data.event_date_id else None

    # A10 — race-safe capacity check. When full → onto the waitlist, not rejected.
    app_status = await _resolve_application_status(db, event, event_date_uuid)
    is_waitlisted = app_status == 'waitlist'

    # Generate variable symbol (unique within the institution to avoid
    # mis-linking manual/QR bank transfers to the wrong application).
    vs = await _generate_unique_variable_symbol(db, inst_uuid)

    # Free event → no payment is ever required for this application.
    is_free = (event.price or 0) <= 0

    # Resolve the chosen payment method for a PAID event (enforced server-side).
    pay_settings = await _get_payment_settings(db, inst_uuid)
    chosen_method = "free"
    qr_payload = None
    if not is_free:
        inst_methods = [m for m in _derive_institution_methods(pay_settings) if _method_is_configured(pay_settings, m)]
        offered = _event_methods(event, inst_methods)
        if not offered:
            raise HTTPException(
                status_code=400,
                detail="Pro tuto akci nejsou dostupné žádné platební metody. Kontaktujte pořadatele.",
            )
        req_method = (data.payment_method or "").strip().lower()
        if req_method:
            if req_method not in offered:
                raise HTTPException(status_code=400, detail="Zvolený způsob platby není u této akce povolen.")
            chosen_method = req_method
        elif len(offered) == 1:
            chosen_method = offered[0]
        else:
            raise HTTPException(status_code=400, detail="Vyberte prosím způsob platby.")

    application = EventApplication(
        institution_id=inst_uuid,
        event_id=event.id,
        event_date_id=event_date_uuid,
        applicant_data=data.applicant_data,
        applicant_email=data.applicant_email,
        applicant_name=data.applicant_name,
        note=data.note,
        marketing_consent=bool(data.marketing_consent),
        total_amount=0 if is_free else event.price,
        variable_symbol=None if is_free else vs,
        status=app_status,
        payment_status="not_required" if is_free else "unpaid",
        payment_method=chosen_method,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    # Phase 76 — auto-seed contact directory (best-effort)
    try:
        await upsert_contact_from_event_application(db, application, event)
        await db.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Contact auto-seed failed (application {application.id}): {e}")

    # Create a QR payment ONLY for the QR method (never for gateway/cash; skip waitlisted).
    if not is_waitlisted and not is_free and chosen_method == "qr" and pay_settings and pay_settings.account_number:
        qr_payload = _generate_qr_payload(
            account_number=pay_settings.account_number,
            bank_code=pay_settings.bank_code or "",
            amount=event.price,
            currency=event.currency or "CZK",
            variable_symbol=vs,
            message=f"Prihlaska {event.name[:40]}",
        )

        payment = EventPayment(
            application_id=application.id,
            institution_id=inst_uuid,
            provider="qr",
            amount=event.price,
            currency=event.currency or "CZK",
            variable_symbol=vs,
            qr_payload=qr_payload,
        )
        db.add(payment)
        application.payment_status = "pending"
        await db.commit()

    resp = _to_dict(application)
    resp["qr_payload"] = qr_payload
    resp["payment_method"] = chosen_method

    # Confirmation email (best-effort). Sent only AFTER the application (and any
    # payment) are committed; a Resend failure must never roll back the saved
    # registration. No sensitive data or API keys are ever logged.
    email = (application.applicant_email or "").strip()
    email_valid = bool(email) and _re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)
    if email_valid:
        try:
            inst_res = await db.execute(select(Institution).where(Institution.id == inst_uuid))
            institution = inst_res.scalar_one_or_none()
            inst_name = institution.name if institution else ""
            reply_to = getattr(institution, "email", None) if institution else None

            date_label = None
            if event_date_uuid:
                ed_res = await db.execute(select(EventDate).where(EventDate.id == event_date_uuid))
                ed = ed_res.scalar_one_or_none()
                if ed and ed.start_datetime:
                    date_label = ed.start_datetime.strftime("%d.%m.%Y %H:%M")

            payment_relevant = bool(
                not is_waitlisted and chosen_method == "qr" and pay_settings and pay_settings.account_number
            )
            await trigger_event_application_confirmation(
                to_email=email,
                data={
                    "event_name": event.name,
                    "applicant_name": application.applicant_name or "",
                    "institution_name": inst_name,
                    "date_label": date_label,
                    "is_waitlist": is_waitlisted,
                    "status": application.status,
                    "is_free": is_free,
                    "price": event.price or 0,
                    "currency": event.currency or "CZK",
                    "variable_symbol": None if is_free else vs,
                    "payment_method": chosen_method,
                    "payment_relevant": payment_relevant,
                    "account_number": pay_settings.account_number if pay_settings else None,
                    "bank_code": pay_settings.bank_code if pay_settings else None,
                    "account_name": pay_settings.account_name if pay_settings else None,
                },
                reply_to=reply_to,
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"Event confirmation email failed (application {application.id}): {type(e).__name__}")

    resp["payment_settings"] = {
        "payment_method": chosen_method,
        "account_number": pay_settings.account_number if pay_settings else None,
        "bank_code": pay_settings.bank_code if pay_settings else None,
        "account_name": pay_settings.account_name if pay_settings else None,
        "provider": pay_settings.provider if pay_settings else None,
        "gateway_enabled": chosen_method == "gateway",
    } if pay_settings else {"payment_method": chosen_method}
    resp["pdf_url"] = f"/api/events/public/{institution_id}/application/{str(application.id)}/pdf"
    resp["waitlisted"] = is_waitlisted

    return resp


@router.get("/public/{institution_id}/application/{application_id}/pdf")
async def public_application_pdf(
    institution_id: str,
    application_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Public PDF download for application confirmation (no auth)."""
    enabled = await is_feature_enabled(db, FEATURE_KEY, institution_id)
    if not enabled:
        raise HTTPException(status_code=404, detail="Not found")

    inst_uuid = uuid.UUID(institution_id)
    app_result = await db.execute(
        select(EventApplication).where(and_(
            EventApplication.id == uuid.UUID(application_id),
            EventApplication.institution_id == inst_uuid,
        ))
    )
    application = app_result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Přihláška nenalezena")

    event_result = await db.execute(select(Event).where(Event.id == application.event_id))
    event = event_result.scalar_one_or_none()

    event_date = None
    if application.event_date_id:
        ed_result = await db.execute(select(EventDate).where(EventDate.id == application.event_date_id))
        event_date = ed_result.scalar_one_or_none()

    pay_result = await db.execute(
        select(InstitutionPaymentSettings).where(InstitutionPaymentSettings.institution_id == inst_uuid)
    )
    pay_settings = pay_result.scalar_one_or_none()

    from database.models import Institution
    inst_result = await db.execute(select(Institution).where(Institution.id == inst_uuid))
    institution = inst_result.scalar_one_or_none()

    from services.export_service import generate_pdf_confirmation
    buffer = generate_pdf_confirmation(
        _to_dict(application),
        _to_dict(event) if event else {},
        _to_dict(event_date) if event_date else None,
        {"name": institution.name if institution else "Instituce"},
        _to_dict(pay_settings) if pay_settings else None,
    )

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=potvrzeni.pdf"},
    )


def _mask_merchant(value: Optional[str]) -> Optional[str]:
    """Mask Comgate Merchant ID — preserve TEST_ prefix and last 4 chars."""
    if not value:
        return None
    v = value.strip()
    if not v:
        return None
    if v.upper().startswith("TEST_"):
        rest = v[5:]
        tail = rest[-4:] if len(rest) >= 4 else rest
        return f"TEST_••••{tail}"
    if len(v) <= 4:
        return "••••" + v
    return "••••" + v[-4:]


# Sentinel string that the frontend may send to explicitly clear a stored key.
CLEAR_SENTINEL = "__CLEAR__"


def _enrich_payment_settings(d: dict, settings: Optional[InstitutionPaymentSettings]) -> dict:
    """Add public mode/masked indicators, allowed methods + config flags; strip raw secrets."""
    mode = _detect_mode(settings).value.upper() if settings else "MOCK"
    masked = _mask_merchant(getattr(settings, "gateway_api_key", None)) if settings else None
    secret_set = bool((getattr(settings, "gateway_secret", None) or "").strip()) if settings else False
    d.pop("gateway_api_key", None)
    d.pop("gateway_secret", None)
    d["gateway_mode"] = mode
    d["gateway_api_key_masked"] = masked
    d["gateway_secret_set"] = secret_set
    d["allowed_methods"] = _derive_institution_methods(settings)
    d["methods_configured"] = {m: _method_is_configured(settings, m) for m in VALID_PAYMENT_METHODS}
    return d


# ============ Payment Settings ============

@router.get("/settings/payment")
async def get_payment_settings(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _guard=Depends(require_feature("events_payments")),
):
    """Get payment settings for institution."""
    await require_events_module(db, current_user["institution_id"])
    inst_uuid = uuid.UUID(current_user["institution_id"])

    result = await db.execute(
        select(InstitutionPaymentSettings).where(
            InstitutionPaymentSettings.institution_id == inst_uuid
        )
    )
    settings = result.scalar_one_or_none()
    if not settings:
        return {
            "payment_mode": "qr",
            "account_number": None,
            "bank_code": None,
            "gateway_mode": "MOCK",
            "gateway_api_key_masked": None,
            "gateway_secret_set": False,
            "allowed_methods": [],
            "methods_configured": {m: (m == "cash") for m in VALID_PAYMENT_METHODS},
        }

    d = _to_dict(settings)
    return _enrich_payment_settings(d, settings)


@router.put("/settings/payment")
async def update_payment_settings(
    data: PaymentSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _guard=Depends(require_feature("events_payments")),
):
    """Update payment settings for institution.

    Empty string for `gateway_api_key`/`gateway_secret` is treated as
    "no change" (preserves existing stored credentials). To explicitly clear
    a stored key, send the literal "__CLEAR__" sentinel.
    """
    await require_events_module(db, current_user["institution_id"])
    inst_uuid = uuid.UUID(current_user["institution_id"])

    result = await db.execute(
        select(InstitutionPaymentSettings).where(
            InstitutionPaymentSettings.institution_id == inst_uuid
        )
    )
    settings = result.scalar_one_or_none()

    if not settings:
        settings = InstitutionPaymentSettings(institution_id=inst_uuid)
        db.add(settings)

    # Snapshot the currently-allowed methods BEFORE mutating anything.
    old_methods = _derive_institution_methods(settings)

    update_data = data.model_dump(exclude_unset=True)
    requested_methods = update_data.pop("allowed_methods", None)
    confirm_disable = update_data.pop("confirm_disable", False)

    # Apply account/gateway fields first so config checks see the new state.
    for key, value in update_data.items():
        if key in ("gateway_api_key", "gateway_secret"):
            if value is None:
                continue
            if isinstance(value, str):
                if value == CLEAR_SENTINEL:
                    setattr(settings, key, None)
                    continue
                if value.strip() == "":
                    continue
        setattr(settings, key, value)

    # ── Two-level allowed methods ────────────────────────────────────
    if requested_methods is not None:
        new_methods = []
        for m in requested_methods:
            if m in VALID_PAYMENT_METHODS and m not in new_methods:
                new_methods.append(m)
        # Each enabled method must be technically configured.
        for m in new_methods:
            if not _method_is_configured(settings, m):
                msgs = {
                    "qr": "QR platbu lze povolit pouze s vyplněným číslem účtu.",
                    "gateway": "Platební bránu Comgate lze povolit pouze s platnou konfigurací brány (poskytovatel + přihlašovací údaje).",
                }
                raise HTTPException(status_code=400, detail=msgs.get(m, f"Metoda {m} není správně nakonfigurována."))

        removed = [m for m in old_methods if m not in new_methods]
        if removed:
            now = datetime.now(timezone.utc)
            paid_events = (await db.execute(
                select(Event).where(and_(
                    Event.institution_id == inst_uuid,
                    Event.price > 0,
                    Event.is_active == True,
                    Event.is_archived == False,
                ))
            )).scalars().all()

            affected, would_empty = [], []
            for ev in paid_events:
                ev_methods = ev.allowed_payment_methods or old_methods
                if not set(ev_methods) & set(removed):
                    continue
                future_cnt = (await db.execute(
                    select(func.count(EventDate.id)).where(and_(
                        EventDate.event_id == ev.id, EventDate.start_datetime >= now
                    ))
                )).scalar() or 0
                any_cnt = (await db.execute(
                    select(func.count(EventDate.id)).where(EventDate.event_id == ev.id)
                )).scalar() or 0
                if not (future_cnt > 0 or any_cnt == 0):
                    continue  # only past-dated events are unaffected
                remaining = [m for m in ev_methods if m not in removed]
                entry = {"id": str(ev.id), "name": ev.name, "methods": ev_methods}
                affected.append((ev, remaining))
                if not remaining:
                    would_empty.append(entry)

            if would_empty:
                raise HTTPException(status_code=409, detail={
                    "code": "would_empty",
                    "message": "Některým placeným akcím by po této změně nezůstala žádná platební metoda. Nejprve prosím upravte tyto akce.",
                    "events": would_empty,
                })
            if affected and not confirm_disable:
                raise HTTPException(status_code=409, detail={
                    "code": "needs_confirm",
                    "message": "Tuto metodu používají aktivní budoucí akce. Potvrďte změnu — metoda z nich bude odebrána.",
                    "events": [{"id": str(ev.id), "name": ev.name, "methods": ev.allowed_payment_methods or old_methods} for ev, _ in affected],
                })
            # Confirmed → strip the removed method(s) from each affected event.
            for ev, remaining in affected:
                ev.allowed_payment_methods = remaining
                ev.updated_at = now

        settings.allowed_methods = new_methods
        # Keep legacy payment_mode roughly in sync (cash ignored for legacy field).
        if "qr" in new_methods and "gateway" in new_methods:
            settings.payment_mode = "both"
        elif "gateway" in new_methods:
            settings.payment_mode = "gateway"
        else:
            settings.payment_mode = "qr"

    settings.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(settings)

    d = _to_dict(settings)
    return _enrich_payment_settings(d, settings)


# ============ Feature Flag Admin ============

@router.get("/admin/feature-flags")
async def get_feature_flags(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get all feature flags (super admin only)."""
    if current_user.get("role") not in ("admin", "spravce"):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění")

    result = await db.execute(select(FeatureFlag).order_by(FeatureFlag.key))
    flags = result.scalars().all()
    return [_to_dict(f) for f in flags]
