"""
Mailing Campaign Service — relevance engine, recipient resolution, background sending.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    School, SchoolContact, Program, Institution,
    MailingCampaign, MailingCampaignProgram,
    MailingCampaignRecipient, MailingRecipientProgram,
)
from services.email_service import EmailService

logger = logging.getLogger(__name__)

# ---- Relevance mapping: program target_groups → school tags ----
TARGET_GROUP_TO_SCHOOL_TAGS = {
    "ms_3_6":    ["MŠ"],
    "zs1_7_12":  ["ZŠ"],
    "zs2_12_15": ["ZŠ"],
    "ss_14_18":  ["SŠ", "Gymnázium"],
    "gym_14_18": ["Gymnázium", "SŠ"],
    "adults":    [],
    "all":       [],  # matches everyone
}


def compute_relevance(program_target_groups: list, school_tags: list) -> list:
    """Return list of matched segments between a program and a school.
    Empty list = no match (unless program targets 'all').
    """
    if not program_target_groups:
        return []
    if "all" in program_target_groups:
        return ["all"]
    if not school_tags:
        return []

    matched = []
    school_tags_upper = [t.upper() for t in school_tags]
    for tg in program_target_groups:
        expected_tags = TARGET_GROUP_TO_SCHOOL_TAGS.get(tg, [])
        for et in expected_tags:
            if et.upper() in school_tags_upper and tg not in matched:
                matched.append(tg)
    return matched


async def resolve_recipients(
    db: AsyncSession,
    institution_id: str,
    program_ids: List[str],
    recipient_mode: str,
    manual_school_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Resolve recipients based on programs and mode.
    Returns {schools: [...], warnings: [...], stats: {...}}
    """
    # Fetch programs
    result = await db.execute(
        select(Program).where(
            and_(
                Program.institution_id == institution_id,
                Program.id.in_([uuid.UUID(pid) for pid in program_ids]),
            )
        )
    )
    programs = result.scalars().all()

    # Fetch all active schools with contacts
    result = await db.execute(
        select(School).where(
            and_(
                School.institution_id == institution_id,
                School.deleted_at.is_(None),
            )
        )
    )
    schools = result.scalars().all()

    # Fetch all active contacts
    result = await db.execute(
        select(SchoolContact).where(
            and_(
                SchoolContact.institution_id == institution_id,
                SchoolContact.status == 'active',
            )
        )
    )
    contacts = result.scalars().all()

    # Build contact map: school_id → [contacts]
    contact_map = {}
    for c in contacts:
        sid = str(c.school_id)
        if sid not in contact_map:
            contact_map[sid] = []
        contact_map[sid].append(c)

    warnings = []
    school_results = []
    no_tags_count = 0
    no_contacts_count = 0

    for school in schools:
        school_id = str(school.id)
        school_tags = school.tags or []
        school_contacts = contact_map.get(school_id, [])

        # Use school-level email as fallback
        if not school_contacts and school.email:
            school_contacts = [type('FakeContact', (), {
                'id': None, 'email': school.email,
                'name': school.contact_person or school.name,
            })()]

        if not school_contacts:
            no_contacts_count += 1
            continue

        # Determine relevance per program
        if recipient_mode == 'all':
            relevant_program_ids = [str(p.id) for p in programs]
            matched_segments = ["all"]
            is_relevant = True
        elif recipient_mode == 'manual':
            if manual_school_ids and school_id in manual_school_ids:
                relevant_program_ids = [str(p.id) for p in programs]
                matched_segments = ["manual"]
                is_relevant = True
            else:
                is_relevant = False
                relevant_program_ids = []
                matched_segments = []
        else:
            # relevant_only or relevant_plus_manual
            relevant_program_ids = []
            matched_segments = []
            for p in programs:
                tg = p.target_groups or []
                match = compute_relevance(tg, school_tags)
                if match:
                    relevant_program_ids.append(str(p.id))
                    matched_segments.extend(match)
            matched_segments = list(set(matched_segments))
            is_relevant = len(relevant_program_ids) > 0

            # For relevant_plus_manual, also include manually selected
            if not is_relevant and recipient_mode == 'relevant_plus_manual':
                if manual_school_ids and school_id in manual_school_ids:
                    relevant_program_ids = [str(p.id) for p in programs]
                    matched_segments = ["manual"]
                    is_relevant = True

        if not school_tags:
            no_tags_count += 1

        for contact in school_contacts:
            school_results.append({
                "school_id": school_id,
                "school_name": school.name,
                "school_city": school.city,
                "school_tags": school_tags,
                "contact_id": str(contact.id) if contact.id else None,
                "contact_name": getattr(contact, 'name', None) or school.name,
                "email": contact.email,
                "is_relevant": is_relevant,
                "relevant_program_ids": relevant_program_ids,
                "matched_segments": matched_segments,
            })

    if no_tags_count > 0:
        warnings.append(f"{no_tags_count} škol nemá vyplněné kategorie (tagy) a nebyly automaticky zahrnuty do relevantního výběru.")
    if no_contacts_count > 0:
        warnings.append(f"{no_contacts_count} škol nemá žádný kontaktní email.")

    relevant = [s for s in school_results if s["is_relevant"]]
    not_relevant = [s for s in school_results if not s["is_relevant"]]

    return {
        "recipients": relevant,
        "excluded": not_relevant,
        "warnings": warnings,
        "stats": {
            "total_schools": len(schools),
            "total_contacts": len(relevant),
            "schools_no_tags": no_tags_count,
            "schools_no_contacts": no_contacts_count,
            "excluded_count": len(not_relevant),
        },
    }


# ---- Default Czech templates by audience ----

DEFAULT_TEMPLATES = {
    "ms": {
        "subject": "Nová nabídka doprovodných programů pro mateřské školy",
        "greeting": "Vážené paní učitelky, vážení pedagogové,",
        "intro_text": "rádi bychom Vám představili aktuální nabídku doprovodných programů určených pro mateřské školy. Připravili jsme pro děti zážitkové a vzdělávací programy, které lze využít v průběhu nadcházejícího období.",
        "closing_text": "Budeme rádi, pokud Vás některý z programů zaujme. V případě zájmu si můžete vybrat vhodný termín přímo přes rezervační systém nebo nás kontaktovat pro bližší informace.",
    },
    "zs": {
        "subject": "Aktuální nabídka doprovodných programů pro základní školy",
        "greeting": "Vážené paní učitelky, vážení páni učitelé,",
        "intro_text": "zasíláme Vám přehled aktuální nabídky doprovodných programů pro základní školy. Programy jsou připraveny s ohledem na věkovou skupinu žáků a mohou vhodně doplnit výuku i školní výjezdy.",
        "closing_text": "Věříme, že Vás některý z programů zaujme. Termíny i podrobnosti najdete v odkazu u jednotlivých programů.",
    },
    "ss": {
        "subject": "Nabídka doprovodných programů pro střední školy",
        "greeting": "Vážené kolegyně, vážení kolegové,",
        "intro_text": "dovolujeme si Vám představit aktuální nabídku doprovodných programů vhodných pro studenty středních škol a gymnázií.",
        "closing_text": "Budeme rádi za Váš zájem. Podrobnosti a rezervaci naleznete u jednotlivých programů.",
    },
    "general": {
        "subject": "Nabídka doprovodných programů",
        "greeting": "Dobrý den,",
        "intro_text": "rádi bychom Vám představili aktuální nabídku našich doprovodných programů.",
        "closing_text": "Budeme rádi, pokud Vás některý z programů zaujme. V případě zájmu nás neváhejte kontaktovat.",
    },
}


def get_default_signature(institution_name: str) -> str:
    return f"S pozdravem\ntým {institution_name}"


async def send_campaign_emails(campaign_id: str):
    """Background job: send emails for a campaign. Called by scheduler."""
    from database.supabase import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Load campaign
            result = await db.execute(
                select(MailingCampaign).where(MailingCampaign.id == campaign_id)
            )
            campaign = result.scalar_one_or_none()
            if not campaign or campaign.status not in ('sending',):
                logger.warning(f"Campaign {campaign_id} not in sending state, skipping")
                return

            # Load institution for branding
            result = await db.execute(
                select(Institution).where(Institution.id == campaign.institution_id)
            )
            institution = result.scalar_one_or_none()
            inst_name = institution.name if institution else "Instituce"

            # Load recipients
            result = await db.execute(
                select(MailingCampaignRecipient).where(
                    and_(
                        MailingCampaignRecipient.campaign_id == campaign_id,
                        MailingCampaignRecipient.status == 'pending',
                    )
                )
            )
            recipients = result.scalars().all()

            # Load recipient→programs mapping
            recipient_ids = [r.id for r in recipients]
            result = await db.execute(
                select(MailingRecipientProgram).where(
                    MailingRecipientProgram.recipient_id.in_(recipient_ids)
                )
            ) if recipient_ids else None
            rp_rows = result.scalars().all() if result else []

            # Build map: recipient_id → [program snapshots]
            rp_map = {}
            for rp in rp_rows:
                rid = str(rp.recipient_id)
                if rid not in rp_map:
                    rp_map[rid] = []
                rp_map[rid].append({
                    "name": rp.program_name,
                    "target_groups": rp.program_target_groups or [],
                })

            # Also get full program snapshots from campaign
            programs_snapshot = campaign.programs_snapshot or []

            sent = 0
            failed = 0
            booking_base_url = f"https://www.budezivo.cz/booking/{campaign.institution_id}"

            for recipient in recipients:
                try:
                    # Get programs for this specific recipient
                    recipient_programs = rp_map.get(str(recipient.id), programs_snapshot)

                    # Build email HTML
                    html = _build_campaign_email_html(
                        greeting=campaign.greeting,
                        intro_text=campaign.intro_text,
                        programs=recipient_programs,
                        closing_text=campaign.closing_text,
                        signature=campaign.signature,
                        institution_name=inst_name,
                        booking_url=booking_base_url,
                        institution=institution,
                    )

                    result = await EmailService.send_email(
                        to_email=recipient.email,
                        subject=campaign.subject,
                        html_content=html,
                        add_gdpr_footer=True,
                    )

                    if result.get("status") == "sent":
                        recipient.status = "sent"
                        recipient.sent_at = datetime.now(timezone.utc)
                        recipient.email_provider_id = result.get("email_id")
                        sent += 1
                    else:
                        recipient.status = "failed"
                        recipient.failure_reason = result.get("error", "Unknown error")
                        failed += 1

                except Exception as e:
                    recipient.status = "failed"
                    recipient.failure_reason = str(e)[:500]
                    failed += 1
                    logger.error(f"Failed to send campaign email to {recipient.email}: {e}")

            # Update campaign stats
            campaign.sent_count = (campaign.sent_count or 0) + sent
            campaign.failed_count = (campaign.failed_count or 0) + failed
            campaign.status = "sent" if failed == 0 else ("partial" if sent > 0 else "failed")
            campaign.sent_at = datetime.now(timezone.utc)

            await db.commit()
            logger.info(f"Campaign {campaign_id} sending complete: {sent} sent, {failed} failed")

        except Exception as e:
            logger.error(f"Campaign {campaign_id} sending error: {e}")
            try:
                campaign.status = "failed"
                await db.commit()
            except Exception:
                pass


def _build_campaign_email_html(
    greeting: str,
    intro_text: str,
    programs: list,
    closing_text: str,
    signature: str,
    institution_name: str,
    booking_url: str,
    institution=None,
) -> str:
    """Build promotional mailing HTML."""
    primary_color = "#1E293B"
    if institution:
        primary_color = institution.primary_color or "#1E293B"

    # Build program cards
    program_cards = ""
    for p in programs:
        name = p.get("name", "") if isinstance(p, dict) else getattr(p, "program_name", "")
        desc = p.get("description", "") if isinstance(p, dict) else ""
        duration = p.get("duration", "") if isinstance(p, dict) else ""
        tg = p.get("target_groups", []) if isinstance(p, dict) else []
        tg_labels = _format_target_groups(tg)

        duration_html = f'<span style="color:#64748B;font-size:13px;">Délka: {duration} min</span>' if duration else ""
        desc_html = f'<p style="color:#475569;font-size:14px;margin:4px 0 8px 0;">{desc[:200]}</p>' if desc else ""

        program_cards += f"""
        <div style="border:1px solid #E2E8F0;border-radius:8px;padding:16px;margin:12px 0;background:#FAFBFC;">
            <h3 style="margin:0 0 4px 0;color:{primary_color};font-size:16px;">{name}</h3>
            {desc_html}
            <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
                {duration_html}
                <span style="color:#64748B;font-size:13px;">{tg_labels}</span>
            </div>
        </div>
        """

    signature_html = signature.replace("\n", "<br>") if signature else ""

    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
        <div style="background:{primary_color};padding:24px;border-radius:8px 8px 0 0;">
            <h1 style="color:white;margin:0;font-size:20px;">{institution_name}</h1>
        </div>
        <div style="padding:24px;">
            <p style="color:#334155;font-size:15px;line-height:1.6;">{greeting}</p>
            <p style="color:#475569;font-size:15px;line-height:1.6;">{intro_text}</p>

            <div style="margin:24px 0;">
                {program_cards}
            </div>

            <div style="text-align:center;margin:24px 0;">
                <a href="{booking_url}" style="display:inline-block;background:{primary_color};color:white;padding:12px 28px;border-radius:6px;text-decoration:none;font-size:15px;font-weight:500;">
                    Zobrazit termíny a rezervovat
                </a>
            </div>

            <p style="color:#475569;font-size:15px;line-height:1.6;">{closing_text}</p>

            <p style="color:#64748B;font-size:14px;line-height:1.6;margin-top:24px;">{signature_html}</p>
        </div>
    </div>
    """


def _format_target_groups(tg: list) -> str:
    labels = {
        "ms_3_6": "MŠ",
        "zs1_7_12": "1. stupeň ZŠ",
        "zs2_12_15": "2. stupeň ZŠ",
        "ss_14_18": "SŠ",
        "gym_14_18": "Gymnázium",
        "adults": "Dospělí",
        "all": "Všechny skupiny",
    }
    return ", ".join(labels.get(t, t) for t in tg) if tg else ""
