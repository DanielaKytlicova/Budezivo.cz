"""
Events module API routes (Pilot feature).
Handles: Events CRUD, EventDates, Applications, Payments, Feature flags.
"""
import uuid
import random
import logging
from datetime import datetime, timezone
from typing import Optional, List
from urllib.parse import quote as url_quote
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete

from database.supabase import get_db
from database.models import (
    Event, EventDate, EventApplication, EventPayment,
    InstitutionPaymentSettings, FeatureFlag
)
from core.security import get_current_user
from services.feature_flags import is_feature_enabled
from services.plan_service import require_feature

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


class ApplicationStatusUpdate(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None


class PaymentSettingsUpdate(BaseModel):
    payment_mode: str = "qr"
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
    """Generate a unique 10-digit variable symbol."""
    return str(random.randint(1000000000, 9999999999))


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


@router.post("")
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _guard=Depends(require_feature("events_basic")),
):
    """Create a new event."""
    await require_events_module(db, current_user["institution_id"])

    event = Event(
        institution_id=uuid.UUID(current_user["institution_id"]),
        name=data.name,
        type=data.type,
        description=data.description,
        capacity=data.capacity,
        price=data.price,
        currency=data.currency,
        is_active=data.is_active,
        image_url=data.image_url,
        form_fields=data.form_fields,
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
        select(EventApplication).where(
            EventApplication.id == uuid.UUID(application_id)
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Přihláška nenalezena")

    if data.status:
        app.status = data.status
    if data.payment_status:
        app.payment_status = data.payment_status
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
        # Count approved applications for this date
        cnt = await db.execute(
            select(func.count(EventApplication.id)).where(and_(
                EventApplication.event_date_id == d.id,
                EventApplication.status != 'rejected',
            ))
        )
        dd["applications_count"] = cnt.scalar() or 0
        dd["capacity"] = d.capacity_override or event.capacity
        dd["spots_left"] = dd["capacity"] - dd["applications_count"]
        dates_out.append(dd)

    ev_dict["dates"] = dates_out
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

    # Generate variable symbol
    vs = _generate_variable_symbol()

    application = EventApplication(
        institution_id=inst_uuid,
        event_id=event.id,
        event_date_id=uuid.UUID(data.event_date_id) if data.event_date_id else None,
        applicant_data=data.applicant_data,
        applicant_email=data.applicant_email,
        applicant_name=data.applicant_name,
        note=data.note,
        total_amount=event.price,
        variable_symbol=vs,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    # Get payment settings
    ps_result = await db.execute(
        select(InstitutionPaymentSettings).where(
            InstitutionPaymentSettings.institution_id == inst_uuid
        )
    )
    pay_settings = ps_result.scalar_one_or_none()

    # Create QR payment if applicable
    qr_payload = None
    if pay_settings and pay_settings.account_number and event.price > 0:
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
    resp["payment_settings"] = {
        "payment_mode": pay_settings.payment_mode if pay_settings else "qr",
        "account_number": pay_settings.account_number if pay_settings else None,
        "bank_code": pay_settings.bank_code if pay_settings else None,
        "account_name": pay_settings.account_name if pay_settings else None,
    } if pay_settings else None
    resp["pdf_url"] = f"/api/events/public/{institution_id}/application/{str(application.id)}/pdf"

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
        return {"payment_mode": "qr", "account_number": None, "bank_code": None}

    d = _to_dict(settings)
    # Don't expose secrets
    d.pop("gateway_api_key", None)
    d.pop("gateway_secret", None)
    return d


@router.put("/settings/payment")
async def update_payment_settings(
    data: PaymentSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _guard=Depends(require_feature("events_payments")),
):
    """Update payment settings for institution."""
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

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)
    settings.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(settings)

    d = _to_dict(settings)
    d.pop("gateway_api_key", None)
    d.pop("gateway_secret", None)
    return d


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
