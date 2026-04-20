"""
Superadmin dashboard routes — platform owner/operator only.
Institution management, plan control, usage analytics, billing orders.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.supabase import get_db
from database.models import (
    Institution, User, Program, Reservation, Event, EventApplication,
    MailingCampaign, WaitlistEntry, BillingOrder, UsageMetric,
)
from database.supabase_repositories import InstitutionRepositorySupabase
from services.plan_service import PLAN_LIMITS, PLAN_LABELS
from services.billing_service import create_billing_order, confirm_billing_order
from services.usage_service import get_institution_usage

router = APIRouter(prefix="/superadmin", tags=["Superadmin"])
logger = logging.getLogger(__name__)

SUPERADMIN_EMAILS = ["demo@budezivo.cz", "admin@budezivo.cz"]


# ---- Guard ----

async def require_superadmin(current_user: dict = Depends(get_current_user)):
    """Only platform owner/operator can access superadmin routes."""
    if current_user.get("email") not in SUPERADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Přístup pouze pro superadmina platformy")
    return current_user


# ---- Pydantic models ----

class SuperadminPlanChange(BaseModel):
    plan: str
    plan_status: str = "active"
    activated_by: str = "admin"
    billing_note: Optional[str] = None
    expires_at: Optional[str] = None


class SuperadminBillingConfirm(BaseModel):
    order_id: str


class SuperadminDeleteInstitution(BaseModel):
    confirmation_name: str
    reason: Optional[str] = None


# ---- Institution list ----

@router.get("/institutions")
async def list_institutions(
    plan: Optional[str] = None,
    plan_status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query("name", regex="^(name|plan|created_at|last_activity)$"),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """List all institutions with plan/usage overview."""
    query = select(Institution).where(Institution.deleted_at.is_(None))

    if plan:
        query = query.where(Institution.plan == plan)
    if plan_status:
        query = query.where(Institution.plan_status == plan_status)

    result = await db.execute(query.order_by(Institution.name))
    institutions = result.scalars().all()

    items = []
    for inst in institutions:
        inst_id = inst.id

        # Count programs
        prog_result = await db.execute(
            select(func.count()).select_from(Program).where(
                and_(Program.institution_id == inst_id, Program.deleted_at.is_(None))
            )
        )
        prog_cnt = prog_result.scalar() or 0

        # Count reservations
        res_result = await db.execute(
            select(func.count()).select_from(Reservation).where(Reservation.institution_id == inst_id)
        )
        res_cnt = res_result.scalar() or 0

        # Count users
        user_result = await db.execute(
            select(func.count()).select_from(User).where(
                and_(User.institution_id == inst_id, User.deleted_at.is_(None))
            )
        )
        user_cnt = user_result.scalar() or 0

        # Last reservation date
        last_res_result = await db.execute(
            select(func.max(Reservation.created_at)).where(Reservation.institution_id == inst_id)
        )
        last_res_dt = last_res_result.scalar_one_or_none()

        item = {
            "id": str(inst.id),
            "name": inst.name,
            "email": inst.email,
            "plan": inst.plan,
            "plan_label": PLAN_LABELS.get(inst.plan, inst.plan),
            "plan_status": inst.plan_status,
            "plan_activated_by": inst.plan_activated_by,
            "plan_activated_at": inst.plan_activated_at.isoformat() if inst.plan_activated_at else None,
            "plan_expires_at": inst.plan_expires_at.isoformat() if inst.plan_expires_at else None,
            "billing_note": inst.billing_note,
            "programs_count": prog_cnt,
            "reservations_count": res_cnt,
            "users_count": user_cnt,
            "last_activity": last_res_dt.isoformat() if last_res_dt else (inst.created_at.isoformat() if inst.created_at else None),
            "created_at": inst.created_at.isoformat() if inst.created_at else None,
        }

        if search and search.lower() not in (inst.name or "").lower() and search.lower() not in (inst.email or "").lower():
            continue

        items.append(item)

    return {"institutions": items, "count": len(items)}


# ---- Institution detail ----

@router.get("/institutions/{institution_id}")
async def get_institution_detail(
    institution_id: str,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Detailed institution view with usage metrics."""
    result = await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")

    inst_id = uuid.UUID(institution_id)

    # Counts
    prog_count = (await db.execute(
        select(func.count()).select_from(Program).where(and_(Program.institution_id == inst_id, Program.deleted_at.is_(None)))
    )).scalar() or 0

    res_count = (await db.execute(
        select(func.count()).select_from(Reservation).where(Reservation.institution_id == inst_id)
    )).scalar() or 0

    user_count = (await db.execute(
        select(func.count()).select_from(User).where(and_(User.institution_id == inst_id, User.deleted_at.is_(None)))
    )).scalar() or 0

    # Event counts
    event_count = 0
    app_count = 0
    try:
        event_count = (await db.execute(
            select(func.count()).select_from(Event).where(Event.institution_id == inst_id)
        )).scalar() or 0
        app_count = (await db.execute(
            select(func.count()).select_from(EventApplication).where(
                EventApplication.event_id.in_(select(Event.id).where(Event.institution_id == inst_id))
            )
        )).scalar() or 0
    except Exception:
        pass

    # Mailing counts
    mailing_count = (await db.execute(
        select(func.count()).select_from(MailingCampaign).where(MailingCampaign.institution_id == inst_id)
    )).scalar() or 0

    # Waitlist counts
    waitlist_count = (await db.execute(
        select(func.count()).select_from(WaitlistEntry).where(WaitlistEntry.institution_id == inst_id)
    )).scalar() or 0

    # Usage metrics
    usage = await get_institution_usage(db, institution_id)

    # Billing orders
    billing_result = await db.execute(
        select(BillingOrder).where(BillingOrder.institution_id == inst_id)
        .order_by(desc(BillingOrder.created_at))
        .limit(10)
    )
    orders = billing_result.scalars().all()

    return {
        "id": str(inst.id),
        "name": inst.name,
        "email": inst.email,
        "website": inst.website,
        "plan": inst.plan,
        "plan_label": PLAN_LABELS.get(inst.plan, inst.plan),
        "plan_status": inst.plan_status,
        "plan_activated_by": inst.plan_activated_by,
        "plan_activated_at": inst.plan_activated_at.isoformat() if inst.plan_activated_at else None,
        "plan_expires_at": inst.plan_expires_at.isoformat() if inst.plan_expires_at else None,
        "plan_updated_at": inst.plan_updated_at.isoformat() if inst.plan_updated_at else None,
        "billing_provider": inst.billing_provider,
        "billing_external_id": inst.billing_external_id,
        "billing_note": inst.billing_note,
        "auto_renew": inst.auto_renew,
        "created_at": inst.created_at.isoformat() if inst.created_at else None,
        "stats": {
            "programs": prog_count,
            "reservations": res_count,
            "users": user_count,
            "events": event_count,
            "applications": app_count,
            "mailings": mailing_count,
            "waitlist_entries": waitlist_count,
        },
        "usage_metrics": usage,
        "billing_orders": [
            {
                "id": str(o.id),
                "requested_plan": o.requested_plan_type,
                "status": o.status,
                "provider": o.provider,
                "amount": o.amount,
                "currency": o.currency,
                "paid_at": o.paid_at.isoformat() if o.paid_at else None,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "note": o.note,
            }
            for o in orders
        ],
    }


# ---- Manual plan control ----

@router.put("/institutions/{institution_id}/plan")
async def change_institution_plan(
    institution_id: str,
    data: SuperadminPlanChange,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Manually change an institution's plan. Full control."""
    if data.plan not in ["free", "start", "pro", "pro_plus"]:
        raise HTTPException(status_code=400, detail="Neplatný plán")

    result = await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")

    limits = PLAN_LIMITS.get(data.plan, PLAN_LIMITS["free"])
    now = datetime.now(timezone.utc)

    update_data = {
        "plan": data.plan,
        "plan_status": data.plan_status,
        "plan_activated_by": data.activated_by,
        "plan_activated_at": now if data.plan_status == "active" else inst.plan_activated_at,
        "plan_updated_at": now,
        "plan_changed_by_superadmin_id": current_user["user_id"],
        "programs_limit": limits["programs_limit"],
        "bookings_monthly_limit": limits["bookings_monthly_limit"],
    }

    if data.billing_note is not None:
        update_data["billing_note"] = data.billing_note
    if data.expires_at:
        update_data["plan_expires_at"] = data.expires_at

    inst_repo = InstitutionRepositorySupabase(db)
    await inst_repo.update(institution_id, update_data)

    logger.info(f"Superadmin plan change: {institution_id} → {data.plan}/{data.plan_status} by {current_user['email']}")

    return {
        "message": f"Plán instituce změněn na {PLAN_LABELS.get(data.plan, data.plan)} ({data.plan_status})",
        "plan": data.plan,
        "plan_status": data.plan_status,
    }


# ---- Institution deletion (soft delete with safety) ----

@router.delete("/institutions/{institution_id}")
async def delete_institution(
    institution_id: str,
    data: SuperadminDeleteInstitution,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an institution. Requires exact name confirmation for safety.

    Security rules:
    - Superadmin cannot delete their own institution.
    - `confirmation_name` must match the institution's name EXACTLY (case-sensitive).
    - Sets `deleted_at` on institution and on all its users (prevents login).
    - Preserves data in DB for audit/recovery.
    """
    result = await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")
    if inst.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Instituce je již smazána")

    # Safety: superadmin cannot delete own institution
    if str(inst.id) == str(current_user.get("institution_id", "")):
        raise HTTPException(status_code=400, detail="Nelze smazat vlastní instituci")

    # Safety: confirmation name must match exactly
    if (data.confirmation_name or "").strip() != (inst.name or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Název instituce nesouhlasí. Pro potvrzení zadejte přesný název.",
        )

    now = datetime.now(timezone.utc)
    note_suffix = f"\n[DELETED by {current_user['email']} at {now.isoformat()}]"
    if data.reason:
        note_suffix += f" Důvod: {data.reason}"

    # Soft-delete institution
    inst.deleted_at = now
    inst.billing_note = (inst.billing_note or "") + note_suffix

    # Soft-delete all users of this institution (so they cannot log in)
    await db.execute(
        text("UPDATE users SET deleted_at = :now WHERE institution_id = CAST(:iid AS uuid) AND deleted_at IS NULL")
        .bindparams(now=now, iid=institution_id)
    )

    await db.commit()

    logger.warning(
        f"Superadmin DELETED institution {institution_id} ({inst.name}) by {current_user['email']}. Reason: {data.reason or 'n/a'}"
    )

    return {
        "message": f"Instituce „{inst.name}“ byla smazána.",
        "institution_id": str(inst.id),
        "deleted_at": now.isoformat(),
    }


# ---- Billing order management ----

@router.get("/billing-orders")
async def list_billing_orders(
    status: Optional[str] = None,
    institution_id: Optional[str] = None,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """List all billing orders across institutions."""
    query = select(BillingOrder).order_by(desc(BillingOrder.created_at))

    if status:
        query = query.where(BillingOrder.status == status)
    if institution_id:
        query = query.where(BillingOrder.institution_id == institution_id)

    result = await db.execute(query.limit(100))
    orders = result.scalars().all()

    # Enrich with institution names
    items = []
    for o in orders:
        inst_result = await db.execute(
            select(Institution.name).where(Institution.id == o.institution_id)
        )
        inst_name = inst_result.scalar_one_or_none() or "?"

        items.append({
            "id": str(o.id),
            "institution_id": str(o.institution_id),
            "institution_name": inst_name,
            "requested_plan": o.requested_plan_type,
            "requested_plan_label": PLAN_LABELS.get(o.requested_plan_type, o.requested_plan_type),
            "status": o.status,
            "provider": o.provider,
            "amount": o.amount,
            "currency": o.currency,
            "paid_at": o.paid_at.isoformat() if o.paid_at else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "note": o.note,
        })

    return {"orders": items, "count": len(items)}


@router.post("/billing-orders/{order_id}/confirm")
async def confirm_order(
    order_id: str,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Manually confirm a billing order and activate the plan."""
    result = await confirm_billing_order(db, order_id, confirmed_by="admin")
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/billing-orders/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending billing order."""
    result = await db.execute(
        select(BillingOrder).where(BillingOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Objednávka nenalezena")
    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Pouze pending objednávky lze zrušit")

    order.status = "cancelled"
    order.cancelled_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Objednávka zrušena", "order_id": str(order.id)}


# ---- Platform overview ----

@router.get("/overview")
async def platform_overview(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated platform metrics for superadmin dashboard."""
    total_institutions = (await db.execute(
        select(func.count()).select_from(Institution).where(Institution.deleted_at.is_(None))
    )).scalar() or 0

    # Plan distribution
    plan_dist = {}
    for plan_key in ["free", "start", "pro", "pro_plus"]:
        cnt = (await db.execute(
            select(func.count()).select_from(Institution).where(
                and_(Institution.plan == plan_key, Institution.deleted_at.is_(None))
            )
        )).scalar() or 0
        plan_dist[plan_key] = cnt

    total_programs = (await db.execute(
        select(func.count()).select_from(Program).where(Program.deleted_at.is_(None))
    )).scalar() or 0

    total_reservations = (await db.execute(
        select(func.count()).select_from(Reservation)
    )).scalar() or 0

    total_users = (await db.execute(
        select(func.count()).select_from(User).where(User.deleted_at.is_(None))
    )).scalar() or 0

    pending_orders = (await db.execute(
        select(func.count()).select_from(BillingOrder).where(BillingOrder.status == "pending")
    )).scalar() or 0

    return {
        "total_institutions": total_institutions,
        "plan_distribution": plan_dist,
        "total_programs": total_programs,
        "total_reservations": total_reservations,
        "total_users": total_users,
        "pending_billing_orders": pending_orders,
    }


# ---- Platform-wide usage analytics ----

@router.get("/usage-analytics")
async def platform_usage_analytics(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Platform-wide feature usage analytics aggregated across all institutions.

    Returns:
    - `by_feature`: total usage + institutions using each feature + adoption rate
    - `by_plan`: feature usage grouped by institution's plan
    - `top_institutions`: most active institutions by total usage
    """
    from services.plan_service import FEATURE_LABELS, PLAN_FEATURES, FEATURE_MIN_PLAN

    # Total active institutions (denominator for adoption rate)
    total_inst_result = await db.execute(
        select(func.count()).select_from(Institution).where(Institution.deleted_at.is_(None))
    )
    total_inst = total_inst_result.scalar() or 1

    # by_feature: sum usage + distinct institutions per feature
    feat_result = await db.execute(
        select(
            UsageMetric.feature_key,
            func.sum(UsageMetric.usage_count).label("total_usage"),
            func.count(func.distinct(UsageMetric.institution_id)).label("inst_count"),
        ).group_by(UsageMetric.feature_key)
    )
    by_feature = []
    for row in feat_result.all():
        key = row.feature_key
        by_feature.append({
            "feature_key": key,
            "feature_label": FEATURE_LABELS.get(key, key),
            "min_plan": FEATURE_MIN_PLAN.get(key),
            "min_plan_label": PLAN_LABELS.get(FEATURE_MIN_PLAN.get(key, ""), ""),
            "total_usage": int(row.total_usage or 0),
            "institutions_using": int(row.inst_count or 0),
            "adoption_rate": round(100.0 * (row.inst_count or 0) / total_inst, 1),
        })
    by_feature.sort(key=lambda x: x["total_usage"], reverse=True)

    # by_plan: join usage metrics with institution plan
    plan_result = await db.execute(
        select(
            Institution.plan,
            func.sum(UsageMetric.usage_count).label("total_usage"),
            func.count(func.distinct(UsageMetric.institution_id)).label("inst_count"),
        )
        .select_from(UsageMetric)
        .join(Institution, UsageMetric.institution_id == Institution.id)
        .where(Institution.deleted_at.is_(None))
        .group_by(Institution.plan)
    )
    by_plan = []
    for row in plan_result.all():
        plan = row.plan or "free"
        by_plan.append({
            "plan": plan,
            "plan_label": PLAN_LABELS.get(plan, plan),
            "total_usage": int(row.total_usage or 0),
            "active_institutions": int(row.inst_count or 0),
        })

    # top_institutions by total usage
    top_result = await db.execute(
        select(
            Institution.id,
            Institution.name,
            Institution.plan,
            func.sum(UsageMetric.usage_count).label("total_usage"),
        )
        .select_from(UsageMetric)
        .join(Institution, UsageMetric.institution_id == Institution.id)
        .where(Institution.deleted_at.is_(None))
        .group_by(Institution.id, Institution.name, Institution.plan)
        .order_by(desc(func.sum(UsageMetric.usage_count)))
        .limit(10)
    )
    top_institutions = [
        {
            "institution_id": str(row.id),
            "institution_name": row.name,
            "plan": row.plan,
            "plan_label": PLAN_LABELS.get(row.plan, row.plan),
            "total_usage": int(row.total_usage or 0),
        }
        for row in top_result.all()
    ]

    return {
        "total_institutions": total_inst,
        "by_feature": by_feature,
        "by_plan": by_plan,
        "top_institutions": top_institutions,
    }


# ---- Manual trigger: plan expiration scheduler ----

@router.post("/run-expiration-job")
async def run_expiration_job(
    current_user: dict = Depends(require_superadmin),
):
    """Manually trigger the plan expiration/auto-renewal scheduler.
    Useful for testing or immediate processing."""
    try:
        from scheduler import process_plan_expiration
        await process_plan_expiration()
        return {"message": "Expirační úloha spuštěna"}
    except Exception as e:
        logger.error(f"Manual expiration job failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
