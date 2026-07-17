"""
Mailing Campaign routes — CRUD, preview, send.
"""
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.supabase import get_db
from database.models import (
    MailingCampaign, MailingCampaignProgram,
    MailingCampaignRecipient, MailingRecipientProgram,
    Program, Institution, SchoolContact,
)
from services.mailing_service import (
    resolve_recipients, DEFAULT_TEMPLATES, get_default_signature,
    send_campaign_emails,
)
from services.plan_service import require_feature
from services.usage_service import track_usage
from services.feature_flags import is_feature_enabled
from services.email_service import EmailService


CONTACTS_FEATURE_KEY = "contacts_module"


async def require_contacts_module(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Gate targeted-mailing endpoints behind the Contacts CRM whitelist."""
    inst_id = current_user.get("institution_id") or current_user.get("inst_id")
    if not inst_id:
        raise HTTPException(403, "User has no institution context")
    enabled = await is_feature_enabled(db, CONTACTS_FEATURE_KEY, str(inst_id))
    if not enabled:
        raise HTTPException(
            status_code=403,
            detail="Cílený mailing nad Kontakty není pro tuto instituci povolen.",
        )

router = APIRouter(prefix="/mailings", tags=["Mailings"], dependencies=[Depends(require_feature("mailing"))])
logger = logging.getLogger(__name__)

# Section 5 — only these roles may create/edit/schedule/send campaigns.
CAMPAIGN_ROLES = {"admin", "spravce", "edukator"}
_EMAIL_RE = __import__("re").compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _ensure_campaign_role(current_user: dict):
    if current_user.get("role") not in CAMPAIGN_ROLES:
        raise HTTPException(status_code=403, detail="Vaše role nemá oprávnění pracovat s e-mailovými kampaněmi.")


def _norm_email(e: str) -> str:
    return (e or "").strip().lower()


# ---- Pydantic models ----

class CampaignCreate(BaseModel):
    name: str
    type: str = "single_program"  # single_program | seasonal | custom
    recipient_mode: str = "relevant_only"
    program_ids: List[str] = []
    subject: str = ""
    greeting: str = ""
    intro_text: str = ""
    closing_text: str = ""
    signature: str = ""


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    recipient_mode: Optional[str] = None
    program_ids: Optional[List[str]] = None
    subject: Optional[str] = None
    greeting: Optional[str] = None
    intro_text: Optional[str] = None
    closing_text: Optional[str] = None
    signature: Optional[str] = None


class RecipientPreviewRequest(BaseModel):
    program_ids: List[str]
    recipient_mode: str = "relevant_only"
    manual_school_ids: Optional[List[str]] = None


class SendCampaignRequest(BaseModel):
    recipient_ids: Optional[List[str]] = None  # If None, use all resolved recipients
    manual_school_ids: Optional[List[str]] = None


# ---- Endpoints ----

@router.get("")
async def list_campaigns(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all campaigns for the institution."""
    query = select(MailingCampaign).where(
        MailingCampaign.institution_id == current_user["institution_id"]
    ).order_by(desc(MailingCampaign.created_at))

    if status:
        query = query.where(MailingCampaign.status == status)

    result = await db.execute(query)
    campaigns = result.scalars().all()

    items = []
    for c in campaigns:
        # Count programs
        prog_result = await db.execute(
            select(func.count()).where(MailingCampaignProgram.campaign_id == c.id)
        )
        prog_count = prog_result.scalar() or 0

        items.append({
            "id": str(c.id),
            "name": c.name,
            "type": c.type,
            "status": c.status,
            "recipient_mode": c.recipient_mode,
            "subject": c.subject,
            "total_recipients": c.total_recipients or 0,
            "sent_count": c.sent_count or 0,
            "failed_count": c.failed_count or 0,
            "skipped_count": c.skipped_count or 0,
            "programs_count": prog_count,
            "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
            "failure_reason": c.failure_reason,
            "sent_at": c.sent_at.isoformat() if c.sent_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return {"campaigns": items, "count": len(items)}


# ---- Static path endpoints MUST be before /{campaign_id} ----

@router.get("/delivery-health")
async def get_delivery_health(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate delivery failures per email across all campaigns."""
    institution_id = current_user["institution_id"]

    result = await db.execute(
        select(
            MailingCampaignRecipient.email,
            MailingCampaignRecipient.school_name,
            MailingCampaignRecipient.contact_name,
            MailingCampaignRecipient.contact_id,
            MailingCampaignRecipient.school_id,
            MailingCampaignRecipient.status,
            MailingCampaignRecipient.failure_reason,
            MailingCampaignRecipient.sent_at,
            MailingCampaign.name.label("campaign_name"),
        )
        .join(MailingCampaign, MailingCampaignRecipient.campaign_id == MailingCampaign.id)
        .where(MailingCampaign.institution_id == institution_id)
        .order_by(MailingCampaignRecipient.email)
    )
    rows = result.all()

    email_stats = {}
    for row in rows:
        email = row.email
        if email not in email_stats:
            email_stats[email] = {
                "email": email,
                "school_name": row.school_name,
                "contact_name": row.contact_name,
                "contact_id": str(row.contact_id) if row.contact_id else None,
                "school_id": str(row.school_id) if row.school_id else None,
                "total_sends": 0,
                "successful": 0,
                "failed": 0,
                "last_failure_reason": None,
                "last_sent_at": None,
                "campaigns": [],
            }
        stats = email_stats[email]
        stats["total_sends"] += 1
        if row.status == "sent":
            stats["successful"] += 1
            if row.sent_at:
                stats["last_sent_at"] = row.sent_at.isoformat()
        elif row.status == "failed":
            stats["failed"] += 1
            stats["last_failure_reason"] = row.failure_reason
        stats["campaigns"].append({
            "name": row.campaign_name,
            "status": row.status,
            "failure_reason": row.failure_reason,
        })

    problematic = []
    healthy = []
    for stats in email_stats.values():
        failure_rate = stats["failed"] / stats["total_sends"] if stats["total_sends"] > 0 else 0
        stats["failure_rate"] = round(failure_rate * 100, 1)
        if stats["failed"] >= 2:
            stats["recommendation"] = "invalid"
            stats["recommendation_label"] = "Neplatný kontakt — doporučeno smazat"
            problematic.append(stats)
        elif stats["failed"] >= 1:
            stats["recommendation"] = "warning"
            stats["recommendation_label"] = "Potenciální problém — sledujte"
            problematic.append(stats)
        else:
            stats["recommendation"] = "ok"
            healthy.append(stats)

    problematic.sort(key=lambda x: x["failed"], reverse=True)

    result = await db.execute(
        select(SchoolContact).where(
            and_(
                SchoolContact.institution_id == institution_id,
                SchoolContact.status == 'invalid',
            )
        )
    )
    already_invalid = result.scalars().all()

    return {
        "problematic_contacts": problematic,
        "healthy_count": len(healthy),
        "already_invalid_count": len(already_invalid),
        "already_invalid": [
            {"id": str(c.id), "email": c.email, "name": c.name, "school_id": str(c.school_id), "email_validation_error": c.email_validation_error}
            for c in already_invalid
        ],
        "summary": {
            "total_emails_tracked": len(email_stats),
            "problematic": len(problematic),
            "recommended_invalid": sum(1 for p in problematic if p["recommendation"] == "invalid"),
            "recommended_warning": sum(1 for p in problematic if p["recommendation"] == "warning"),
        },
    }


@router.post("/flag-invalid-contacts")
async def flag_invalid_contacts(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    contact_ids: Optional[List[str]] = None,
    auto: bool = False,
):
    """Flag contacts as invalid based on delivery failures."""
    institution_id = current_user["institution_id"]
    flagged = 0

    if auto:
        health = await get_delivery_health(current_user, db)
        to_flag = [p["contact_id"] for p in health["problematic_contacts"] if p["recommendation"] == "invalid" and p.get("contact_id")]
    elif contact_ids:
        to_flag = contact_ids
    else:
        return {"message": "Žádné kontakty k označení", "flagged": 0}

    for cid in to_flag:
        result = await db.execute(
            select(SchoolContact).where(and_(SchoolContact.id == cid, SchoolContact.institution_id == institution_id))
        )
        contact = result.scalar_one_or_none()
        if contact and contact.status != 'invalid':
            contact.status = 'invalid'
            contact.email_validation_error = 'Opakovaně neúspěšné doručení z propagačních kampaní'
            flagged += 1

    await db.commit()
    return {"message": f"Označeno {flagged} kontaktů jako neplatných", "flagged": flagged}


@router.delete("/remove-invalid-contacts")
async def remove_invalid_contacts(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    contact_ids: Optional[List[str]] = None,
):
    """Permanently delete invalid contacts."""
    institution_id = current_user["institution_id"]

    if contact_ids:
        conditions = and_(SchoolContact.id.in_([uuid.UUID(cid) for cid in contact_ids]), SchoolContact.institution_id == institution_id)
    else:
        conditions = and_(SchoolContact.status == 'invalid', SchoolContact.institution_id == institution_id)

    result = await db.execute(select(SchoolContact).where(conditions))
    contacts = result.scalars().all()
    deleted = 0
    for c in contacts:
        await db.delete(c)
        deleted += 1

    await db.commit()
    return {"message": f"Smazáno {deleted} neplatných kontaktů", "deleted": deleted}


@router.get("/templates/defaults")
async def get_all_default_templates(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all default email templates."""
    institution_id = current_user["institution_id"]
    result = await db.execute(select(Institution).where(Institution.id == institution_id))
    institution = result.scalar_one_or_none()
    inst_name = institution.name if institution else "Instituce"

    templates = {}
    for key, tpl in DEFAULT_TEMPLATES.items():
        templates[key] = {**tpl, "signature": get_default_signature(inst_name)}
    return {"templates": templates}


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get campaign detail with recipients and programs."""
    result = await db.execute(
        select(MailingCampaign).where(
            and_(
                MailingCampaign.id == campaign_id,
                MailingCampaign.institution_id == current_user["institution_id"],
            )
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampaň nenalezena")

    # Load programs
    result = await db.execute(
        select(MailingCampaignProgram).where(
            MailingCampaignProgram.campaign_id == campaign.id
        ).order_by(MailingCampaignProgram.display_order)
    )
    campaign_programs = result.scalars().all()

    program_ids = [str(cp.program_id) for cp in campaign_programs if cp.program_id]
    programs_data = []
    if program_ids:
        result = await db.execute(
            select(Program).where(Program.id.in_([uuid.UUID(pid) for pid in program_ids]))
        )
        progs = result.scalars().all()
        prog_map = {str(p.id): p for p in progs}
        for pid in program_ids:
            p = prog_map.get(pid)
            if p:
                programs_data.append({
                    "id": str(p.id),
                    "name": p.name_cs,
                    "description": p.description_cs,
                    "duration": p.duration,
                    "target_groups": p.target_groups or [],
                    "age_group": p.age_group,
                })

    # Load recipients
    result = await db.execute(
        select(MailingCampaignRecipient).where(
            MailingCampaignRecipient.campaign_id == campaign.id
        ).order_by(MailingCampaignRecipient.school_name)
    )
    recipients = result.scalars().all()

    # Load recipient programs
    recipient_ids = [r.id for r in recipients]
    rp_map = {}
    if recipient_ids:
        result = await db.execute(
            select(MailingRecipientProgram).where(
                MailingRecipientProgram.recipient_id.in_(recipient_ids)
            )
        )
        for rp in result.scalars().all():
            rid = str(rp.recipient_id)
            if rid not in rp_map:
                rp_map[rid] = []
            rp_map[rid].append({
                "program_name": rp.program_name,
                "program_target_groups": rp.program_target_groups or [],
            })

    recipients_data = []
    for r in recipients:
        recipients_data.append({
            "id": str(r.id),
            "school_name": r.school_name,
            "contact_name": r.contact_name,
            "email": r.email,
            "status": r.status,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "failure_reason": r.failure_reason,
            "matching_reason": r.matching_reason or {},
            "programs": rp_map.get(str(r.id), []),
        })

    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "type": campaign.type,
        "status": campaign.status,
        "recipient_mode": campaign.recipient_mode,
        "subject": campaign.subject,
        "greeting": campaign.greeting,
        "intro_text": campaign.intro_text,
        "closing_text": campaign.closing_text,
        "signature": campaign.signature,
        "content_snapshot": campaign.content_snapshot,
        "selection_snapshot": campaign.selection_snapshot,
        "programs_snapshot": campaign.programs_snapshot,
        "total_recipients": campaign.total_recipients or 0,
        "sent_count": campaign.sent_count or 0,
        "failed_count": campaign.failed_count or 0,
        "skipped_count": campaign.skipped_count or 0,
        "scheduled_at": campaign.scheduled_at.isoformat() if campaign.scheduled_at else None,
        "failure_reason": campaign.failure_reason,
        "sent_at": campaign.sent_at.isoformat() if campaign.sent_at else None,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "programs": programs_data,
        "recipients": recipients_data,
    }


@router.post("")
async def create_campaign(
    data: CampaignCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new campaign (draft)."""
    _ensure_campaign_role(current_user)
    institution_id = current_user["institution_id"]

    # Get institution for default signature
    result = await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    institution = result.scalar_one_or_none()
    inst_name = institution.name if institution else "Instituce"

    # Auto-fill defaults if empty
    signature = data.signature or get_default_signature(inst_name)
    subject = data.subject
    greeting = data.greeting
    intro_text = data.intro_text
    closing_text = data.closing_text

    # If fields are empty, use general template defaults
    if not subject:
        tpl = DEFAULT_TEMPLATES.get("general", {})
        subject = tpl.get("subject", "Nabídka programů")
    if not greeting:
        tpl = DEFAULT_TEMPLATES.get("general", {})
        greeting = tpl.get("greeting", "Dobrý den,")
    if not intro_text:
        tpl = DEFAULT_TEMPLATES.get("general", {})
        intro_text = tpl.get("intro_text", "")
    if not closing_text:
        tpl = DEFAULT_TEMPLATES.get("general", {})
        closing_text = tpl.get("closing_text", "")

    campaign = MailingCampaign(
        institution_id=institution_id,
        created_by=current_user["user_id"],
        name=data.name,
        type=data.type,
        status="draft",
        recipient_mode=data.recipient_mode,
        subject=subject,
        greeting=greeting,
        intro_text=intro_text,
        closing_text=closing_text,
        signature=signature,
    )
    db.add(campaign)
    await db.flush()

    # Add programs
    for i, pid in enumerate(data.program_ids):
        cp = MailingCampaignProgram(
            campaign_id=campaign.id,
            program_id=uuid.UUID(pid),
            display_order=i,
        )
        db.add(cp)

    await db.commit()

    return {"id": str(campaign.id), "status": "draft", "message": "Kampaň vytvořena jako koncept"}


@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a draft campaign."""
    _ensure_campaign_role(current_user)
    result = await db.execute(
        select(MailingCampaign).where(
            and_(
                MailingCampaign.id == campaign_id,
                MailingCampaign.institution_id == current_user["institution_id"],
            )
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampaň nenalezena")
    if campaign.status != "draft":
        raise HTTPException(status_code=400, detail="Pouze koncepty lze upravovat")

    # Update fields
    for field in ["name", "recipient_mode", "subject", "greeting", "intro_text", "closing_text", "signature"]:
        val = getattr(data, field, None)
        if val is not None:
            setattr(campaign, field, val)

    # Update programs if provided
    if data.program_ids is not None:
        # Remove old
        result = await db.execute(
            select(MailingCampaignProgram).where(
                MailingCampaignProgram.campaign_id == campaign.id
            )
        )
        for old in result.scalars().all():
            await db.delete(old)

        # Add new
        for i, pid in enumerate(data.program_ids):
            cp = MailingCampaignProgram(
                campaign_id=campaign.id,
                program_id=uuid.UUID(pid),
                display_order=i,
            )
            db.add(cp)

    await db.commit()
    return {"message": "Kampaň aktualizována"}


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a draft campaign."""
    _ensure_campaign_role(current_user)
    result = await db.execute(
        select(MailingCampaign).where(
            and_(
                MailingCampaign.id == campaign_id,
                MailingCampaign.institution_id == current_user["institution_id"],
            )
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampaň nenalezena")
    if campaign.status != "draft":
        raise HTTPException(status_code=400, detail="Pouze koncepty lze smazat")

    await db.delete(campaign)
    await db.commit()
    return {"message": "Kampaň smazána"}


@router.post("/preview-recipients")
async def preview_recipients(
    data: RecipientPreviewRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Preview which schools/contacts would receive the mailing."""
    result = await resolve_recipients(
        db=db,
        institution_id=current_user["institution_id"],
        program_ids=data.program_ids,
        recipient_mode=data.recipient_mode,
        manual_school_ids=data.manual_school_ids,
    )
    return result


@router.post("/default-texts")
async def get_default_texts(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audience: str = "general",
):
    """Get default Czech email texts by audience type."""
    institution_id = current_user["institution_id"]
    result = await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    institution = result.scalar_one_or_none()
    inst_name = institution.name if institution else "Instituce"

    tpl = DEFAULT_TEMPLATES.get(audience, DEFAULT_TEMPLATES["general"])
    return {
        "subject": tpl["subject"],
        "greeting": tpl["greeting"],
        "intro_text": tpl["intro_text"],
        "closing_text": tpl["closing_text"],
        "signature": get_default_signature(inst_name),
    }


@router.post("/{campaign_id}/send")
async def send_campaign(
    campaign_id: str,
    data: SendCampaignRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Finalize and send a campaign. Creates recipients and triggers background sending."""
    _ensure_campaign_role(current_user)
    institution_id = current_user["institution_id"]

    result = await db.execute(
        select(MailingCampaign).where(
            and_(
                MailingCampaign.id == campaign_id,
                MailingCampaign.institution_id == institution_id,
            )
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampaň nenalezena")
    if campaign.status not in ("draft",):
        raise HTTPException(status_code=400, detail="Kampaň již byla odeslána nebo se odesílá")

    # Load campaign programs
    result = await db.execute(
        select(MailingCampaignProgram).where(
            MailingCampaignProgram.campaign_id == campaign.id
        ).order_by(MailingCampaignProgram.display_order)
    )
    campaign_programs = result.scalars().all()
    program_ids = [str(cp.program_id) for cp in campaign_programs if cp.program_id]

    # Snapshot campaigns (created from Školy) already carry their recipients and
    # may have no programs → send to the existing snapshot instead.
    existing_recipients = (await db.execute(
        select(func.count()).select_from(MailingCampaignRecipient).where(
            MailingCampaignRecipient.campaign_id == campaign.id
        )
    )).scalar() or 0

    if not program_ids:
        if existing_recipients == 0:
            raise HTTPException(status_code=400, detail="Kampaň neobsahuje žádné programy ani příjemce")
        campaign.content_snapshot = {
            "subject": campaign.subject, "greeting": campaign.greeting,
            "intro_text": campaign.intro_text, "closing_text": campaign.closing_text,
            "signature": campaign.signature,
        }
        campaign.status = "processing"
        campaign.send_started_at = datetime.now(timezone.utc)
        await db.commit()
        background_tasks.add_task(send_campaign_emails, str(campaign.id))
        await track_usage(db, institution_id, "mailing", {"recipients": existing_recipients})
        return {
            "message": f"Odesílání kampaně zahájeno pro {existing_recipients} příjemců",
            "campaign_id": str(campaign.id),
            "total_recipients": existing_recipients,
        }

    # Resolve + snapshot + create recipient rows (shared with scheduling)
    count = await _finalize_program_recipients(
        db, campaign, institution_id, program_ids, data.manual_school_ids
    )
    campaign.status = "processing"
    campaign.send_started_at = datetime.now(timezone.utc)
    await db.commit()

    # Trigger background sending
    background_tasks.add_task(send_campaign_emails, str(campaign.id))

    # Track usage
    await track_usage(db, institution_id, "mailing", {"recipients": count})

    return {
        "message": f"Odesílání kampaně zahájeno pro {count} příjemců",
        "campaign_id": str(campaign.id),
        "total_recipients": count,
    }


async def _finalize_program_recipients(db, campaign, institution_id, program_ids, manual_school_ids):
    """Resolve program-based recipients, write content/programs snapshots and
    create recipient rows. Returns the recipient count. Does NOT change status."""
    resolved = await resolve_recipients(
        db=db,
        institution_id=institution_id,
        program_ids=program_ids,
        recipient_mode=campaign.recipient_mode,
        manual_school_ids=manual_school_ids,
    )
    recipients = resolved["recipients"]
    if not recipients:
        raise HTTPException(status_code=400, detail="Žádní příjemci k odeslání")

    result = await db.execute(
        select(Program).where(Program.id.in_([uuid.UUID(pid) for pid in program_ids]))
    )
    programs = result.scalars().all()
    programs_map = {str(p.id): p for p in programs}

    programs_snapshot = []
    for pid in program_ids:
        p = programs_map.get(pid)
        if p:
            programs_snapshot.append({
                "id": str(p.id),
                "name": p.name_cs,
                "description": (p.description_cs or "")[:300],
                "duration": p.duration,
                "target_groups": p.target_groups or [],
            })

    campaign.content_snapshot = {
        "subject": campaign.subject,
        "greeting": campaign.greeting,
        "intro_text": campaign.intro_text,
        "closing_text": campaign.closing_text,
        "signature": campaign.signature,
    }
    campaign.selection_snapshot = {
        "recipient_mode": campaign.recipient_mode,
        "program_ids": program_ids,
        "stats": resolved["stats"],
        "warnings": resolved["warnings"],
    }
    campaign.programs_snapshot = programs_snapshot
    campaign.total_recipients = len(recipients)

    for r in recipients:
        recipient = MailingCampaignRecipient(
            campaign_id=campaign.id,
            school_id=uuid.UUID(r["school_id"]) if r.get("school_id") else None,
            contact_id=uuid.UUID(r["contact_id"]) if r.get("contact_id") else None,
            email=r["email"],
            school_name=r.get("school_name"),
            contact_name=r.get("contact_name"),
            status="pending",
            matching_reason={
                "selection_mode": campaign.recipient_mode,
                "matched_segments": r.get("matched_segments", []),
                "manual_override": "manual" in r.get("matched_segments", []),
            },
        )
        db.add(recipient)
        await db.flush()
        relevant_pids = r.get("relevant_program_ids", program_ids)
        for rpid in relevant_pids:
            p = programs_map.get(rpid)
            if p:
                db.add(MailingRecipientProgram(
                    recipient_id=recipient.id,
                    program_id=uuid.UUID(rpid),
                    program_name=p.name_cs,
                    program_target_groups=p.target_groups or [],
                ))
    return len(recipients)


# ─────────────────────────────────────────────────────────────────────────
# Section 7 — Plánované odeslání kampaně
# ─────────────────────────────────────────────────────────────────────────

class ScheduleRequest(BaseModel):
    scheduled_at: str  # ISO 8601 (UTC)
    manual_school_ids: Optional[List[str]] = None


class TestEmailRequest(BaseModel):
    email: str


def _parse_utc(value: str) -> datetime:
    from datetime import datetime as _dt
    v = (value or "").strip().replace("Z", "+00:00")
    dt = _dt.fromisoformat(v)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.post("/{campaign_id}/schedule")
async def schedule_campaign(
    campaign_id: str,
    data: ScheduleRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Schedule a draft campaign for a future send. Finalizes recipients now
    (snapshot) and stores scheduled_at in UTC."""
    _ensure_campaign_role(current_user)
    institution_id = current_user["institution_id"]

    campaign = (await db.execute(
        select(MailingCampaign).where(and_(
            MailingCampaign.id == campaign_id,
            MailingCampaign.institution_id == institution_id,
        ))
    )).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampaň nenalezena")
    if campaign.status != "draft":
        raise HTTPException(status_code=400, detail="Naplánovat lze pouze koncept")

    try:
        when = _parse_utc(data.scheduled_at)
    except Exception:
        raise HTTPException(status_code=400, detail="Neplatný formát data a času")
    if when <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Nelze naplánovat odeslání do minulosti")

    # Finalize recipients (snapshot). Reuse existing recipients if present.
    existing = (await db.execute(
        select(func.count()).select_from(MailingCampaignRecipient).where(
            MailingCampaignRecipient.campaign_id == campaign.id
        )
    )).scalar() or 0
    if existing == 0:
        cps = (await db.execute(
            select(MailingCampaignProgram).where(MailingCampaignProgram.campaign_id == campaign.id)
        )).scalars().all()
        program_ids = [str(cp.program_id) for cp in cps if cp.program_id]
        if not program_ids:
            raise HTTPException(status_code=400, detail="Kampaň neobsahuje žádné programy ani příjemce")
        existing = await _finalize_program_recipients(db, campaign, institution_id, program_ids, data.manual_school_ids)
    else:
        campaign.content_snapshot = {
            "subject": campaign.subject, "greeting": campaign.greeting,
            "intro_text": campaign.intro_text, "closing_text": campaign.closing_text,
            "signature": campaign.signature,
        }
        campaign.total_recipients = existing

    campaign.status = "scheduled"
    campaign.scheduled_at = when
    campaign.scheduled_by = current_user["user_id"]
    campaign.failure_reason = None
    await db.commit()
    return {"id": str(campaign.id), "status": "scheduled", "scheduled_at": when.isoformat(), "total_recipients": existing}


@router.post("/{campaign_id}/cancel-schedule")
async def cancel_schedule(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a scheduled send and return the campaign to draft."""
    _ensure_campaign_role(current_user)
    campaign = (await db.execute(
        select(MailingCampaign).where(and_(
            MailingCampaign.id == campaign_id,
            MailingCampaign.institution_id == current_user["institution_id"],
        ))
    )).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampaň nenalezena")
    if campaign.status != "scheduled":
        raise HTTPException(status_code=400, detail="Zrušit lze pouze naplánované odeslání")
    campaign.status = "draft"
    campaign.scheduled_at = None
    await db.commit()
    return {"id": str(campaign.id), "status": "draft"}


@router.post("/{campaign_id}/test-email")
async def send_test_email(
    campaign_id: str,
    data: TestEmailRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a single test email of the campaign content to the given address."""
    _ensure_campaign_role(current_user)
    email = (data.email or "").strip()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Neplatná e-mailová adresa")

    campaign = (await db.execute(
        select(MailingCampaign).where(and_(
            MailingCampaign.id == campaign_id,
            MailingCampaign.institution_id == current_user["institution_id"],
        ))
    )).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampaň nenalezena")

    institution = (await db.execute(
        select(Institution).where(Institution.id == campaign.institution_id)
    )).scalar_one_or_none()
    from services.mailing_service import _build_campaign_email_html
    html_body = _build_campaign_email_html(
        greeting=campaign.greeting, intro_text=campaign.intro_text,
        programs=campaign.programs_snapshot or [], closing_text=campaign.closing_text,
        signature=campaign.signature, institution_name=institution.name if institution else "Instituce",
        booking_url=f"https://www.budezivo.cz/booking/{campaign.institution_id}", institution=institution,
    )
    result = await EmailService.send_email(
        to_email=email, subject=f"[TEST] {campaign.subject}",
        html_content=html_body, add_gdpr_footer=True,
    )
    if result.get("status") != "sent":
        raise HTTPException(status_code=502, detail=result.get("error", "Odeslání testu se nezdařilo"))
    return {"message": f"Testovací e-mail odeslán na {email}"}


# ─────────────────────────────────────────────────────────────────────────
# Section 4 — Školy → bezpečné vytvoření KONCEPTU kampaně (žádné přímé odeslání)
# ─────────────────────────────────────────────────────────────────────────

class SchoolSelectionItem(BaseModel):
    school_id: str
    # If provided (non-empty) → only these contacts; otherwise all eligible
    # contacts of the school are included.
    contact_ids: Optional[List[str]] = None


class FromSchoolsRequest(BaseModel):
    selections: List[SchoolSelectionItem]
    name: Optional[str] = None


async def _evaluate_school_selection(db: AsyncSession, institution_id: str, selections: List[SchoolSelectionItem]):
    """Evaluate the selected schools/contacts and split them into eligible vs
    excluded buckets. Returns (stats, eligible_recipients).

    Note: school_contacts currently tracks only active/invalid + bounce flag.
    Consent / unsubscribe / complaint are not yet stored per school-contact
    (they arrive with the webhook phase) → reported as 0 here.
    """
    from database.models import School

    school_ids = []
    for s in selections:
        try:
            school_ids.append(uuid.UUID(s.school_id))
        except (ValueError, TypeError):
            continue
    contacts_filter = {str(s.school_id): set(s.contact_ids or []) for s in selections}

    schools = {}
    if school_ids:
        rows = (await db.execute(
            select(School).where(and_(
                School.id.in_(school_ids),
                School.institution_id == institution_id,
            ))
        )).scalars().all()
        schools = {str(s.id): s for s in rows}

    all_contacts = {}
    if school_ids:
        rows = (await db.execute(
            select(SchoolContact).where(and_(
                SchoolContact.school_id.in_(school_ids),
                SchoolContact.institution_id == institution_id,
            ))
        )).scalars().all()
        for c in rows:
            all_contacts.setdefault(str(c.school_id), []).append(c)

    stats = {
        "schools": len([sid for sid in contacts_filter if sid in schools]),
        "contacts_found": 0,
        "eligible": 0,
        "duplicates": 0,
        "invalid": 0,
        "bounced_or_complained": 0,
        "unsubscribed": 0,
        "no_marketing_consent": 0,
    }
    eligible = []
    seen_emails = set()

    for sid, wanted in contacts_filter.items():
        school = schools.get(sid)
        if not school:
            continue
        for c in all_contacts.get(sid, []):
            if wanted and str(c.id) not in wanted:
                continue
            stats["contacts_found"] += 1
            email = _norm_email(c.email)
            if not email or not _EMAIL_RE.match(email):
                stats["invalid"] += 1
                continue
            if c.status == "invalid" or c.email_validation_error:
                stats["invalid"] += 1
                continue
            if c.last_email_bounced:
                stats["bounced_or_complained"] += 1
                continue
            if email in seen_emails:
                stats["duplicates"] += 1
                continue
            seen_emails.add(email)
            stats["eligible"] += 1
            eligible.append({
                "email": c.email,
                "contact_id": str(c.id),
                "contact_name": c.name,
                "school_id": sid,
                "school_name": school.name,
            })

    return stats, eligible


@router.post("/from-schools/preview")
async def preview_from_schools(
    data: FromSchoolsRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Show the eligibility summary for the selected schools/contacts BEFORE a
    draft is created. Nothing is sent or persisted."""
    _ensure_campaign_role(current_user)
    stats, eligible = await _evaluate_school_selection(
        db, current_user["institution_id"], data.selections
    )
    return {"stats": stats, "eligible_preview": eligible[:200], "eligible_count": len(eligible)}


@router.post("/from-schools")
async def create_draft_from_schools(
    data: FromSchoolsRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a DRAFT campaign from selected schools/contacts and snapshot the
    eligible recipients. Never sends. Returns the campaign_id so the frontend
    can open the draft editor."""
    _ensure_campaign_role(current_user)
    institution_id = current_user["institution_id"]

    stats, eligible = await _evaluate_school_selection(db, institution_id, data.selections)
    if not eligible:
        raise HTTPException(status_code=400, detail="Mezi vybranými školami nejsou žádné způsobilé kontakty.")

    institution = (await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )).scalar_one_or_none()
    inst_name = institution.name if institution else "Instituce"

    tpl = DEFAULT_TEMPLATES.get("general", {})
    campaign = MailingCampaign(
        institution_id=institution_id,
        created_by=current_user["user_id"],
        name=data.name or f"Kampaň pro školy ({stats['schools']})",
        type="custom",
        status="draft",
        recipient_mode="manual",
        subject=tpl.get("subject", "Nabídka programů"),
        greeting=tpl.get("greeting", "Dobrý den,"),
        intro_text=tpl.get("intro_text", ""),
        closing_text=tpl.get("closing_text", ""),
        signature=get_default_signature(inst_name),
        selection_snapshot={"source": "schools", "stats": stats},
    )
    db.add(campaign)
    await db.flush()

    for r in eligible:
        db.add(MailingCampaignRecipient(
            campaign_id=campaign.id,
            school_id=uuid.UUID(r["school_id"]) if r.get("school_id") else None,
            contact_id=uuid.UUID(r["contact_id"]) if r.get("contact_id") else None,
            email=r["email"],
            school_name=r.get("school_name"),
            contact_name=r.get("contact_name"),
            status="pending",
            matching_reason={"selection_mode": "schools_manual"},
        ))

    campaign.total_recipients = len(eligible)
    await db.commit()

    return {
        "id": str(campaign.id),
        "status": "draft",
        "stats": stats,
        "message": f"Koncept vytvořen s {len(eligible)} příjemci",
    }



# ─────────────────────────────────────────────────────────────────────────
# Phase 78 — M3/M4: Cílený mailing nad tabulkou `contacts`
# ─────────────────────────────────────────────────────────────────────────

import csv
import io
from fastapi.responses import StreamingResponse
from database.models import Contact, ContactLink


class ContactPreviewRequest(BaseModel):
    """Targeting filters for the new contacts-based recipient preview.

    All filters are optional; combining them is AND. Examples:
      - contact_type=['pedagog'], require_consent=True → schools only, opted in
      - event_id=<uuid> → everyone who applied to a specific event
      - source_type=['workshop','kurz'] → past workshop / course attendees
    """
    contact_types: Optional[List[str]] = None       # skola | pedagog | rodic | verejnost | …
    source_types: Optional[List[str]] = None        # primary_source filter
    school_types: Optional[List[str]] = None        # MS | ZS | SS | VOS | VS
    event_id: Optional[str] = None                  # contacts who linked to a specific event
    program_id: Optional[str] = None                # contacts who linked to a specific program
    require_consent: bool = True                    # exclude contacts without explicit consent
    contact_ids: Optional[List[str]] = None         # explicit manual list (overrides filters when set)


@router.post("/preview-contacts")
async def preview_contacts(
    data: ContactPreviewRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _guard=Depends(require_contacts_module),
):
    """Return the deduplicated list of contacts that would receive a campaign.

    Used by the Cílení kampaně UI to show the user *exactly* who is in the
    pool before they click Send. Always strips duplicate emails and surfaces
    a per-contact `consent` state so the UI can render warnings.
    """
    inst_id = current_user["institution_id"]
    q = select(Contact).where(Contact.institution_id == inst_id)

    if data.contact_ids:
        try:
            ids = [uuid.UUID(x) for x in data.contact_ids]
        except ValueError:
            raise HTTPException(400, "Invalid contact_ids")
        q = q.where(Contact.id.in_(ids))
    else:
        if data.contact_types:
            q = q.where(Contact.type.in_(data.contact_types))
        if data.source_types:
            q = q.where(Contact.primary_source.in_(data.source_types))
        if data.school_types:
            q = q.where(Contact.school_type.in_(data.school_types))
        if data.event_id or data.program_id:
            link_q = select(ContactLink.contact_id).where(ContactLink.institution_id == inst_id)
            if data.event_id:
                try:
                    link_q = link_q.where(ContactLink.event_id == uuid.UUID(data.event_id))
                except ValueError:
                    raise HTTPException(400, "Invalid event_id")
            if data.program_id:
                try:
                    link_q = link_q.where(ContactLink.program_id == uuid.UUID(data.program_id))
                except ValueError:
                    raise HTTPException(400, "Invalid program_id")
            q = q.where(Contact.id.in_(link_q))
        if data.require_consent:
            q = q.where(Contact.marketing_consent.is_(True))

    contacts = list((await db.execute(q.order_by(Contact.last_activity_at.desc().nullslast()))).scalars().all())

    # Dedup by email (defensive — DB unique index already enforces it)
    seen, deduped = set(), []
    for c in contacts:
        key = (c.email or '').lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(c)

    return {
        "total": len(deduped),
        "with_consent": sum(1 for c in deduped if c.marketing_consent is True),
        "without_consent": sum(1 for c in deduped if c.marketing_consent is False),
        "unknown_consent": sum(1 for c in deduped if c.marketing_consent is None),
        "recipients": [
            {
                "id": str(c.id),
                "email": c.email,
                "name": f"{c.first_name or ''} {c.last_name or ''}".strip() or None,
                "type": c.type,
                "primary_source": c.primary_source,
                "school_name": c.school_name,
                "marketing_consent": c.marketing_consent,
            }
            for c in deduped
        ],
    }


@router.get("/{campaign_id}/recipients/export.csv")
async def export_recipients_csv(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the campaign's recipient list as CSV (proof-of-delivery)."""
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(400, "Invalid campaign_id")

    inst_id = current_user["institution_id"]
    campaign = (await db.execute(
        select(MailingCampaign).where(
            MailingCampaign.id == cid,
            MailingCampaign.institution_id == inst_id,
        )
    )).scalar_one_or_none()
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    recipients = list((await db.execute(
        select(MailingCampaignRecipient)
        .where(MailingCampaignRecipient.campaign_id == cid)
        .order_by(MailingCampaignRecipient.school_name.nullslast(), MailingCampaignRecipient.email)
    )).scalars().all())

    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow([
        'E-mail', 'Jméno', 'Škola', 'Stav', 'Odesláno', 'Důvod chyby', 'ID poskytovatele',
    ])
    for r in recipients:
        w.writerow([
            r.email,
            r.contact_name or '',
            r.school_name or '',
            r.status,
            r.sent_at.isoformat() if r.sent_at else '',
            r.failure_reason or '',
            r.email_provider_id or '',
        ])

    buf.seek(0)
    filename = f"prijemci-{(campaign.name or 'kampan')[:40].replace(' ', '_')}.csv"
    return StreamingResponse(
        iter([buf.getvalue().encode('utf-8-sig')]),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.post("/{campaign_id}/repeat")
async def repeat_as_draft(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clone an existing campaign into a fresh `draft` so the user can adjust
    and resend without losing the original record."""
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(400, "Invalid campaign_id")

    inst_id = current_user["institution_id"]
    src = (await db.execute(
        select(MailingCampaign).where(
            MailingCampaign.id == cid,
            MailingCampaign.institution_id == inst_id,
        )
    )).scalar_one_or_none()
    if not src:
        raise HTTPException(404, "Campaign not found")

    src_programs = list((await db.execute(
        select(MailingCampaignProgram).where(MailingCampaignProgram.campaign_id == cid)
    )).scalars().all())

    clone = MailingCampaign(
        institution_id=inst_id,
        created_by=current_user.get("id"),
        name=f"{src.name} (kopie)",
        type=src.type,
        status='draft',
        recipient_mode=src.recipient_mode,
        subject=src.subject,
        greeting=src.greeting,
        intro_text=src.intro_text,
        closing_text=src.closing_text,
        signature=src.signature,
        content_snapshot={},
        selection_snapshot=src.selection_snapshot or {},
        programs_snapshot=[],
    )
    db.add(clone)
    await db.flush()

    for p in src_programs:
        db.add(MailingCampaignProgram(
            campaign_id=clone.id,
            program_id=p.program_id,
            display_order=p.display_order,
        ))

    await db.commit()
    return {"id": str(clone.id), "name": clone.name, "status": clone.status}
