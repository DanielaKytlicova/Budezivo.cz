"""Contact directory service (Phase 76 — M1).

Auto-populates the `contacts` table from new reservations and event
applications. Deduplicates by (institution_id, lower(email)) so a teacher
who books 30 programs across 3 years stays a single contact with 30 links.

Why a service module (and not inline in the route)?
    * Two places (bookings.py, events.py) need the exact same logic.
    * Tests can exercise it without hitting HTTP.
    * Backend adds (M3 mailing) will reach into this layer to query/segment.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Contact, ContactLink,
    Reservation, EventApplication, Event, Program,
)


# ── source-type translation ────────────────────────────────────────────────
# `Event.type` (free-form on the model) → contact `source_type` enum used by
# the Contacts UI filters. Anything we don't recognise falls through as
# "jednorazova_akce" so the contact is still captured.
_EVENT_TYPE_MAP = {
    'event': 'jednorazova_akce',
    'workshop': 'workshop',
    'kurz': 'kurz',
    'course': 'kurz',
    'tabor': 'primestsky_tabor',
    'primestsky_tabor': 'primestsky_tabor',
    'baby_herna': 'baby_herna',
    'babyherna': 'baby_herna',
}


def _classify_event_source(event: Event) -> str:
    return _EVENT_TYPE_MAP.get((event.type or '').lower(), 'jednorazova_akce')


def _split_name(full_name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Best-effort split of a Czech full name into (first, last)."""
    if not full_name:
        return None, None
    parts = full_name.strip().split()
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    # Treat the last token as surname, everything before as first name.
    return ' '.join(parts[:-1]), parts[-1]


async def upsert_contact_from_reservation(
    db: AsyncSession,
    reservation: Reservation,
    program: Optional[Program],
) -> Contact:
    """Create or update the contact for a school-program reservation.

    Idempotent — calling twice for the same reservation does not add a
    duplicate ContactLink (we look up by reservation_id).
    """
    return await _upsert(
        db,
        institution_id=reservation.institution_id,
        email=reservation.contact_email,
        full_name=reservation.contact_name,
        phone=reservation.contact_phone,
        contact_type='pedagog',  # school reservations are made by teachers
        primary_source='skolni_rezervace',
        school_name=reservation.school_name,
        school_type=_school_type_from_group(reservation.group_type),
        marketing_consent=reservation.marketing_consent,
        # link
        link_filter={'reservation_id': reservation.id},
        link_data={
            'reservation_id': reservation.id,
            'program_id': reservation.program_id,
            'source_type': 'skolni_rezervace',
            'role': 'objednavajici',
            'status': reservation.status,
            'label': program.name_cs if program and program.name_cs else 'Školní program',
        },
    )


async def upsert_contact_from_event_application(
    db: AsyncSession,
    application: EventApplication,
    event: Event,
) -> Contact:
    """Create or update the contact for an event application."""
    src = _classify_event_source(event)
    # Public-event apps are usually parents / general public — heuristic only.
    contact_type = 'rodic' if src in ('primestsky_tabor', 'baby_herna') else 'verejnost'
    return await _upsert(
        db,
        institution_id=application.institution_id,
        email=application.applicant_email,
        full_name=application.applicant_name,
        phone=None,
        contact_type=contact_type,
        primary_source=src,
        school_name=None,
        school_type=None,
        marketing_consent=application.marketing_consent,
        link_filter={'application_id': application.id},
        link_data={
            'application_id': application.id,
            'event_id': event.id,
            'source_type': src,
            'role': 'ucastnik',
            'status': application.status,
            'label': event.name or 'Akce',
        },
    )


# ── Dict-friendly variants ────────────────────────────────────────────────
# The legacy bookings/events routers operate on raw dicts (Supabase REST style)
# rather than ORM objects. These helpers accept dicts so the call sites stay
# trivial:  await seed_contact_from_booking_dict(db, booking, program_dict)

async def seed_contact_from_booking_dict(
    db: AsyncSession,
    booking: dict,
    program: Optional[dict] = None,
) -> Optional[Contact]:
    """Seed contact from a booking dict (used by public/authenticated booking routes)."""
    inst_raw = booking.get('institution_id')
    if not inst_raw:
        return None
    try:
        inst_uuid = uuid.UUID(str(inst_raw))
    except (ValueError, TypeError):
        return None
    res_id = booking.get('id')
    try:
        res_uuid = uuid.UUID(str(res_id)) if res_id else None
    except (ValueError, TypeError):
        res_uuid = None
    prog_id = booking.get('program_id')
    try:
        prog_uuid = uuid.UUID(str(prog_id)) if prog_id else None
    except (ValueError, TypeError):
        prog_uuid = None
    return await _upsert(
        db,
        institution_id=inst_uuid,
        email=booking.get('contact_email'),
        full_name=booking.get('contact_name'),
        phone=booking.get('contact_phone'),
        contact_type='pedagog',
        primary_source='skolni_rezervace',
        school_name=booking.get('school_name'),
        school_type=_school_type_from_group(booking.get('group_type')),
        marketing_consent=booking.get('marketing_consent'),
        link_filter={'reservation_id': res_uuid} if res_uuid else {},
        link_data={
            'reservation_id': res_uuid,
            'program_id': prog_uuid,
            'source_type': 'skolni_rezervace',
            'role': 'objednavajici',
            'status': booking.get('status', 'pending'),
            'label': (program or {}).get('name_cs') or 'Školní program',
        },
    )


async def seed_contact_from_application_dict(
    db: AsyncSession,
    application: dict,
    event: dict,
) -> Optional[Contact]:
    """Seed contact from an event-application dict."""
    inst_raw = application.get('institution_id')
    if not inst_raw:
        return None
    try:
        inst_uuid = uuid.UUID(str(inst_raw))
    except (ValueError, TypeError):
        return None
    app_id = application.get('id')
    try:
        app_uuid = uuid.UUID(str(app_id)) if app_id else None
    except (ValueError, TypeError):
        app_uuid = None
    ev_id = event.get('id') if event else None
    try:
        ev_uuid = uuid.UUID(str(ev_id)) if ev_id else None
    except (ValueError, TypeError):
        ev_uuid = None

    src = _EVENT_TYPE_MAP.get(((event or {}).get('type') or '').lower(), 'jednorazova_akce')
    contact_type = 'rodic' if src in ('primestsky_tabor', 'baby_herna') else 'verejnost'

    return await _upsert(
        db,
        institution_id=inst_uuid,
        email=application.get('applicant_email'),
        full_name=application.get('applicant_name'),
        phone=None,
        contact_type=contact_type,
        primary_source=src,
        school_name=None,
        school_type=None,
        marketing_consent=application.get('marketing_consent'),
        link_filter={'application_id': app_uuid} if app_uuid else {},
        link_data={
            'application_id': app_uuid,
            'event_id': ev_uuid,
            'source_type': src,
            'role': 'ucastnik',
            'status': application.get('status', 'prihlasen'),
            'label': (event or {}).get('name') or 'Akce',
        },
    )


def _school_type_from_group(group_type: Optional[str]) -> Optional[str]:
    if not group_type:
        return None
    g = group_type.lower()
    if g.startswith('ms'): return 'MS'
    if g.startswith('zs1'): return 'ZS'
    if g.startswith('zs2'): return 'ZS'
    if g.startswith('zs'): return 'ZS'
    if g.startswith('ss') or g.startswith('gym'): return 'SS'
    if g.startswith('vos'): return 'VOS'
    if g.startswith('vs') or g.startswith('univer'): return 'VS'
    return None


async def _upsert(
    db: AsyncSession,
    *,
    institution_id: uuid.UUID,
    email: Optional[str],
    full_name: Optional[str],
    phone: Optional[str],
    contact_type: str,
    primary_source: str,
    school_name: Optional[str],
    school_type: Optional[str],
    marketing_consent: Optional[bool],
    link_filter: dict,
    link_data: dict,
) -> Optional[Contact]:
    """Internal: lookup-or-create contact + idempotent link insert.

    Returns None when there is no usable email — we don't store a contact
    without a primary identifier. The caller doesn't care; failure is silent
    so a missing email never blocks the original reservation/application.
    """
    if not email:
        return None
    email_norm = email.strip().lower()
    if not email_norm:
        return None

    # 1) Find existing contact for this institution
    res = await db.execute(
        select(Contact).where(and_(
            Contact.institution_id == institution_id,
            func.lower(Contact.email) == email_norm,
        ))
    )
    contact = res.scalar_one_or_none()

    first, last = _split_name(full_name)
    now = datetime.now(timezone.utc)

    if contact is None:
        contact = Contact(
            institution_id=institution_id,
            email=email_norm,
            first_name=first,
            last_name=last,
            phone=phone,
            type=contact_type,
            primary_source=primary_source,
            school_name=school_name,
            school_type=school_type,
            marketing_consent=marketing_consent,
            marketing_consent_at=now if marketing_consent else None,
            last_activity_at=now,
        )
        db.add(contact)
        await db.flush()  # need contact.id for the link
    else:
        # Update fields only if missing — never overwrite human-edited values
        if not contact.first_name and first:
            contact.first_name = first
        if not contact.last_name and last:
            contact.last_name = last
        if not contact.phone and phone:
            contact.phone = phone
        if not contact.school_name and school_name:
            contact.school_name = school_name
        if not contact.school_type and school_type:
            contact.school_type = school_type
        # Marketing consent is "sticky positive" — once true, never silently flipped.
        # An explicit False from a new opt-in only takes effect if currently NULL.
        if marketing_consent is True and contact.marketing_consent is not True:
            contact.marketing_consent = True
            contact.marketing_consent_at = now
        elif marketing_consent is False and contact.marketing_consent is None:
            contact.marketing_consent = False
        contact.last_activity_at = now

    # 2) Idempotent link
    link_q = select(ContactLink).where(ContactLink.contact_id == contact.id)
    for k, v in link_filter.items():
        link_q = link_q.where(getattr(ContactLink, k) == v)
    existing_link = (await db.execute(link_q)).scalar_one_or_none()

    if existing_link is None:
        link = ContactLink(
            contact_id=contact.id,
            institution_id=institution_id,
            **link_data,
        )
        db.add(link)
    else:
        # Update status if it advanced (pending → confirmed → completed)
        new_status = link_data.get('status')
        if new_status and existing_link.status != new_status:
            existing_link.status = new_status

    await db.flush()
    return contact


# ── Query helpers (used by routes/contacts.py) ────────────────────────────

async def list_contacts_for_institution(
    db: AsyncSession,
    institution_id: uuid.UUID,
    *,
    type_filter: Optional[str] = None,
    source_filter: Optional[str] = None,
    consent_filter: Optional[str] = None,  # 'yes' | 'no' | 'unknown' | None
    search: Optional[str] = None,
    limit: int = 500,
) -> list[Contact]:
    q = select(Contact).where(Contact.institution_id == institution_id)
    if type_filter and type_filter != 'all':
        q = q.where(Contact.type == type_filter)
    if source_filter and source_filter != 'all':
        q = q.where(Contact.primary_source == source_filter)
    if consent_filter == 'yes':
        q = q.where(Contact.marketing_consent.is_(True))
    elif consent_filter == 'no':
        q = q.where(Contact.marketing_consent.is_(False))
    elif consent_filter == 'unknown':
        q = q.where(Contact.marketing_consent.is_(None))
    if search:
        s = f"%{search.strip().lower()}%"
        q = q.where(or_(
            func.lower(Contact.email).like(s),
            func.lower(func.coalesce(Contact.first_name, '')).like(s),
            func.lower(func.coalesce(Contact.last_name, '')).like(s),
            func.lower(func.coalesce(Contact.phone, '')).like(s),
            func.lower(func.coalesce(Contact.school_name, '')).like(s),
        ))
    q = q.order_by(Contact.last_activity_at.desc().nullslast(), Contact.created_at.desc()).limit(limit)
    return list((await db.execute(q)).scalars().all())


async def list_links_for_contact(
    db: AsyncSession,
    contact_id: uuid.UUID,
) -> list[ContactLink]:
    res = await db.execute(
        select(ContactLink)
        .where(ContactLink.contact_id == contact_id)
        .order_by(ContactLink.linked_at.desc())
    )
    return list(res.scalars().all())
