"""Contacts API (Phase 76 — M1).

Endpoints:
    GET    /api/contacts                  → list with filters
    GET    /api/contacts/{id}             → detail with link history
    PATCH  /api/contacts/{id}             → update note/type/marketing_consent
    POST   /api/contacts                  → manual add
    DELETE /api/contacts/{id}             → soft-aware delete
    GET    /api/contacts/export.csv       → download as CSV
    GET    /api/contacts/stats            → summary numbers for the header strip
"""
from __future__ import annotations

import csv
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.models import Contact, ContactLink
from database.supabase import get_db
from services.contact_service import (
    list_contacts_for_institution,
    list_links_for_contact,
)


router = APIRouter(prefix="/contacts", tags=["Contacts"])
logger = logging.getLogger(__name__)


# ── Pydantic schemas ──────────────────────────────────────────────────────

class ContactLinkOut(BaseModel):
    id: uuid.UUID
    source_type: str
    role: Optional[str] = None
    status: Optional[str] = None
    label: Optional[str] = None
    program_id: Optional[uuid.UUID] = None
    event_id: Optional[uuid.UUID] = None
    reservation_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    linked_at: datetime


class ContactOut(BaseModel):
    id: uuid.UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    type: str
    primary_source: Optional[str] = None
    school_name: Optional[str] = None
    school_type: Optional[str] = None
    marketing_consent: Optional[bool] = None
    marketing_consent_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: datetime
    last_activity_at: Optional[datetime] = None


class ContactDetail(ContactOut):
    links: list[ContactLinkOut] = []


class ContactCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    type: str = 'jine'
    school_name: Optional[str] = None
    school_type: Optional[str] = None
    marketing_consent: Optional[bool] = None
    note: Optional[str] = None


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    type: Optional[str] = None
    school_name: Optional[str] = None
    school_type: Optional[str] = None
    marketing_consent: Optional[bool] = None
    note: Optional[str] = None


class ContactStats(BaseModel):
    total: int
    with_consent: int
    without_consent: int
    unknown_consent: int
    schools: int
    public: int


def _to_out(c: Contact) -> ContactOut:
    return ContactOut(
        id=c.id,
        first_name=c.first_name,
        last_name=c.last_name,
        email=c.email,
        phone=c.phone,
        type=c.type or 'jine',
        primary_source=c.primary_source,
        school_name=c.school_name,
        school_type=c.school_type,
        marketing_consent=c.marketing_consent,
        marketing_consent_at=c.marketing_consent_at,
        note=c.note,
        created_at=c.created_at,
        last_activity_at=c.last_activity_at,
    )


def _to_link_out(link: ContactLink) -> ContactLinkOut:
    return ContactLinkOut(
        id=link.id,
        source_type=link.source_type,
        role=link.role,
        status=link.status,
        label=link.label,
        program_id=link.program_id,
        event_id=link.event_id,
        reservation_id=link.reservation_id,
        application_id=link.application_id,
        linked_at=link.linked_at,
    )


def _institution_id_from_user(user: dict) -> uuid.UUID:
    raw = user.get('institution_id') or user.get('inst_id')
    if not raw:
        raise HTTPException(403, "User has no institution context")
    return uuid.UUID(str(raw))


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[ContactOut])
async def list_contacts(
    type: Optional[str] = Query(None, alias="type"),
    source: Optional[str] = None,
    consent: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    inst = _institution_id_from_user(current_user)
    contacts = await list_contacts_for_institution(
        db, inst,
        type_filter=type, source_filter=source, consent_filter=consent,
        search=search, limit=limit,
    )
    return [_to_out(c) for c in contacts]


@router.get("/stats", response_model=ContactStats)
async def contacts_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    inst = _institution_id_from_user(current_user)
    base = select(func.count(Contact.id)).where(Contact.institution_id == inst)
    total = (await db.execute(base)).scalar() or 0
    with_c = (await db.execute(base.where(Contact.marketing_consent.is_(True)))).scalar() or 0
    without_c = (await db.execute(base.where(Contact.marketing_consent.is_(False)))).scalar() or 0
    unknown_c = (await db.execute(base.where(Contact.marketing_consent.is_(None)))).scalar() or 0
    schools = (await db.execute(base.where(Contact.type.in_(['pedagog', 'skola'])))).scalar() or 0
    public = (await db.execute(base.where(Contact.type.in_(['rodic', 'verejnost'])))).scalar() or 0
    return ContactStats(
        total=total, with_consent=with_c, without_consent=without_c,
        unknown_consent=unknown_c, schools=schools, public=public,
    )


@router.get("/export.csv")
async def export_csv(
    type: Optional[str] = Query(None, alias="type"),
    source: Optional[str] = None,
    consent: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    inst = _institution_id_from_user(current_user)
    contacts = await list_contacts_for_institution(
        db, inst, type_filter=type, source_filter=source,
        consent_filter=consent, search=search, limit=10000,
    )
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow(['Jméno', 'Příjmení', 'Email', 'Telefon', 'Typ', 'Zdroj',
                'Marketing souhlas', 'Škola', 'Typ školy',
                'Vytvořeno', 'Poslední aktivita', 'Poznámka'])
    for c in contacts:
        consent_str = 'Ano' if c.marketing_consent is True else (
            'Ne' if c.marketing_consent is False else 'Neznámé')
        w.writerow([
            c.first_name or '', c.last_name or '', c.email,
            c.phone or '', c.type or '', c.primary_source or '',
            consent_str, c.school_name or '', c.school_type or '',
            c.created_at.isoformat() if c.created_at else '',
            c.last_activity_at.isoformat() if c.last_activity_at else '',
            c.note or '',
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue().encode('utf-8-sig')]),  # BOM for Excel CZ
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="kontakty.csv"'},
    )


@router.get("/{contact_id}", response_model=ContactDetail)
async def get_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    inst = _institution_id_from_user(current_user)
    res = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.institution_id == inst)
    )
    contact = res.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "Contact not found")
    links = await list_links_for_contact(db, contact.id)
    out = ContactDetail(**_to_out(contact).model_dump(), links=[_to_link_out(link) for link in links])
    return out


@router.post("", response_model=ContactOut, status_code=201)
async def create_contact(
    payload: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    inst = _institution_id_from_user(current_user)
    email_norm = payload.email.strip().lower()
    # Dedup
    exists = (await db.execute(
        select(Contact).where(
            Contact.institution_id == inst,
            func.lower(Contact.email) == email_norm,
        )
    )).scalar_one_or_none()
    if exists:
        raise HTTPException(409, "Contact with this email already exists in this institution")
    now = datetime.now(timezone.utc)
    c = Contact(
        institution_id=inst,
        first_name=payload.first_name, last_name=payload.last_name,
        email=email_norm, phone=payload.phone,
        type=payload.type, primary_source='rucne',
        school_name=payload.school_name, school_type=payload.school_type,
        marketing_consent=payload.marketing_consent,
        marketing_consent_at=now if payload.marketing_consent else None,
        note=payload.note,
        last_activity_at=now,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _to_out(c)


@router.patch("/{contact_id}", response_model=ContactOut)
async def update_contact(
    contact_id: uuid.UUID,
    payload: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    inst = _institution_id_from_user(current_user)
    c = (await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.institution_id == inst)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Contact not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == 'marketing_consent' and v is True and c.marketing_consent is not True:
            c.marketing_consent_at = datetime.now(timezone.utc)
        setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return _to_out(c)


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    inst = _institution_id_from_user(current_user)
    c = (await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.institution_id == inst)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Contact not found")
    await db.delete(c)
    await db.commit()
