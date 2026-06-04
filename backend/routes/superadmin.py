"""
Superadmin dashboard routes — platform owner/operator only.
Institution management, plan control, usage analytics, billing orders.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.supabase import get_db
from database.models import (
    Institution, User, Program, Reservation, Event, EventApplication,
    MailingCampaign, WaitlistEntry, BillingOrder, UsageMetric, AuditLog,
    FeatureFlag, InstitutionJoinRequest,
)
from database.supabase_repositories import InstitutionRepositorySupabase
from services.plan_service import PLAN_LIMITS, PLAN_LABELS
from services.billing_service import create_billing_order, confirm_billing_order
from services.usage_service import get_institution_usage

router = APIRouter(prefix="/superadmin", tags=["Superadmin"])
logger = logging.getLogger(__name__)

SUPERADMIN_EMAILS = ["demo@budezivo.cz", "admin@budezivo.cz"]


# ---- Audit helper ----

async def _log_superadmin(
    db: AsyncSession,
    *,
    current_user: dict,
    target_institution_id: Optional[str],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
):
    """Write a single audit entry for a superadmin mutating action.

    institution_id on the row = the TARGET institution (so institution detail pages
    can surface "who did what to us"). If no target institution (platform-level
    action such as running the expiration job), falls back to the superadmin's
    own institution to satisfy the NOT NULL constraint.
    """
    try:
        iid = target_institution_id or current_user.get("institution_id")
        if not iid:
            return
        entry = AuditLog(
            institution_id=iid,
            user_id=current_user["user_id"],
            user_email=current_user.get("email", ""),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details={**(details or {}), "superadmin": True},
        )
        db.add(entry)
        await db.flush()
    except Exception as e:
        logger.warning(f"Superadmin audit write failed: {e}")


# ---- Guard ----

async def require_superadmin(current_user: dict = Depends(get_current_user)):
    """Only platform owner/operator can access superadmin routes.

    Impersonation tokens are explicitly blocked — a superadmin who is currently
    impersonating another user cannot make superadmin changes. They must stop
    impersonation first (see `/impersonate/stop`).
    """
    if current_user.get("impersonated_by_email"):
        raise HTTPException(
            status_code=403,
            detail="Superadmin akce nelze provést během impersonace. Ukončete impersonaci a zkuste znovu.",
        )
    if current_user.get("email") not in SUPERADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Přístup pouze pro superadmina platformy")
    return current_user


# ── Cross-institution join requests (Phase 83) ─────────────────────


@router.get("/join-requests")
async def superadmin_list_all_join_requests(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_superadmin),
):
    """Cross-institution view of every join request in the system."""
    conds = []
    if status:
        conds.append(InstitutionJoinRequest.status == status)
    q = select(
        InstitutionJoinRequest, Institution.name.label("inst_name"),
    ).join(Institution, Institution.id == InstitutionJoinRequest.institution_id)
    if conds:
        q = q.where(and_(*conds))
    q = q.order_by(InstitutionJoinRequest.created_at.desc()).limit(500)
    rows = (await db.execute(q)).all()
    return [
        {
            "id": str(r.InstitutionJoinRequest.id),
            "institution_id": str(r.InstitutionJoinRequest.institution_id),
            "institution_name": r.inst_name,
            "user_id": str(r.InstitutionJoinRequest.user_id) if r.InstitutionJoinRequest.user_id else None,
            "email": r.InstitutionJoinRequest.email,
            "name": r.InstitutionJoinRequest.name,
            "message": r.InstitutionJoinRequest.message,
            "status": r.InstitutionJoinRequest.status,
            "assigned_role": r.InstitutionJoinRequest.assigned_role,
            "created_at": r.InstitutionJoinRequest.created_at.isoformat() if r.InstitutionJoinRequest.created_at else None,
            "reviewed_by": str(r.InstitutionJoinRequest.reviewed_by) if r.InstitutionJoinRequest.reviewed_by else None,
            "reviewed_at": r.InstitutionJoinRequest.reviewed_at.isoformat() if r.InstitutionJoinRequest.reviewed_at else None,
            "review_note": r.InstitutionJoinRequest.review_note,
        }
        for r in rows
    ]


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

    # Owner: first admin by creation time (the person who registered the institution)
    owner_res = await db.execute(
        select(User).where(and_(
            User.institution_id == inst_id,
            User.deleted_at.is_(None),
            User.role == 'admin',
        )).order_by(User.created_at.asc()).limit(1)
    )
    owner = owner_res.scalar_one_or_none()
    # Fallback: first user of any role if no admin exists
    if not owner:
        fallback = await db.execute(
            select(User).where(and_(
                User.institution_id == inst_id,
                User.deleted_at.is_(None),
            )).order_by(User.created_at.asc()).limit(1)
        )
        owner = fallback.scalar_one_or_none()

    # All users (for sub-panel, viewer-only)
    users_res = await db.execute(
        select(User).where(and_(
            User.institution_id == inst_id,
            User.deleted_at.is_(None),
        )).order_by(User.created_at.asc())
    )
    users_list = users_res.scalars().all()

    def _user_dict(u: User):
        if not u:
            return None
        full = (u.name or "").strip()
        first, last = "", ""
        if full:
            parts = full.split(" ", 1)
            first = parts[0]
            last = parts[1] if len(parts) > 1 else ""
        return {
            "id": str(u.id),
            "name": u.name,
            "first_name": first,
            "last_name": last,
            "email": u.email,
            "role": u.role,
            "status": u.status,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }

    # Billing orders
    billing_result = await db.execute(
        select(BillingOrder).where(BillingOrder.institution_id == inst_id)
        .order_by(desc(BillingOrder.created_at))
        .limit(10)
    )
    orders = billing_result.scalars().all()

    # Recent superadmin audit log for THIS institution (top 20)
    audit_res = await db.execute(
        select(AuditLog).where(and_(
            AuditLog.institution_id == inst_id,
            AuditLog.details["superadmin"].as_boolean() == True,  # noqa: E712
        )).order_by(desc(AuditLog.created_at)).limit(20)
    )
    audit_entries = audit_res.scalars().all()

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
        "owner": _user_dict(owner),
        "users": [_user_dict(u) for u in users_list],
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
        "audit_log": [
            {
                "id": str(a.id),
                "user_email": a.user_email,
                "action": a.action,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "details": a.details,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in audit_entries
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

    await _log_superadmin(
        db,
        current_user=current_user,
        target_institution_id=institution_id,
        action="plan_change",
        entity_type="institution",
        entity_id=institution_id,
        details={
            "institution_name": inst.name,
            "from_plan": inst.plan,
            "from_status": inst.plan_status,
            "to_plan": data.plan,
            "to_status": data.plan_status,
            "activated_by": data.activated_by,
            "billing_note": data.billing_note,
            "expires_at": data.expires_at.isoformat() if data.expires_at else None,
        },
    )
    await db.commit()

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

    await _log_superadmin(
        db,
        current_user=current_user,
        target_institution_id=institution_id,
        action="institution_delete",
        entity_type="institution",
        entity_id=institution_id,
        details={
            "institution_name": inst.name,
            "reason": data.reason,
            "confirmed_name": data.confirmation_name,
        },
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
    # Load order to get target institution BEFORE confirm (order state may change)
    pre = await db.execute(select(BillingOrder).where(BillingOrder.id == order_id))
    order = pre.scalar_one_or_none()
    target_iid = str(order.institution_id) if order else None
    requested_plan = order.requested_plan_type if order else None

    result = await confirm_billing_order(db, order_id, confirmed_by="admin")
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])

    await _log_superadmin(
        db,
        current_user=current_user,
        target_institution_id=target_iid,
        action="billing_confirm",
        entity_type="billing_order",
        entity_id=order_id,
        details={"requested_plan": requested_plan},
    )
    await db.commit()
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

    await _log_superadmin(
        db,
        current_user=current_user,
        target_institution_id=str(order.institution_id),
        action="billing_cancel",
        entity_type="billing_order",
        entity_id=order_id,
        details={"requested_plan": order.requested_plan_type},
    )

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
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger the plan expiration/auto-renewal scheduler.
    Useful for testing or immediate processing."""
    try:
        from scheduler import process_plan_expiration
        await process_plan_expiration()
        await _log_superadmin(
            db,
            current_user=current_user,
            target_institution_id=None,
            action="run_expiration_job",
            entity_type="system",
            details={"trigger": "manual"},
        )
        await db.commit()
        return {"message": "Expirační úloha spuštěna"}
    except Exception as e:
        logger.error(f"Manual expiration job failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---- Audit log ----

@router.get("/audit-log")
async def get_superadmin_audit_log(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
    institution_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """Platform-wide audit log of superadmin actions (optionally filtered by target institution).

    Superadmin entries are those with `details.superadmin = true` OR `user_email`
    in the SUPERADMIN_EMAILS list. Joins institution name for context.
    """
    # Base query: superadmin-flagged actions only (details.superadmin == true).
    # We intentionally do NOT include entries where user_email happens to be in
    # SUPERADMIN_EMAILS — those may be regular admin operations by the same
    # person acting inside their own institution.
    base_filter = AuditLog.details["superadmin"].as_boolean() == True  # noqa: E712

    q = select(AuditLog, Institution.name).join(
        Institution, AuditLog.institution_id == Institution.id, isouter=True
    ).where(base_filter)
    count_q = select(func.count(AuditLog.id)).where(base_filter)

    if institution_id:
        q = q.where(AuditLog.institution_id == institution_id)
        count_q = count_q.where(AuditLog.institution_id == institution_id)

    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(desc(AuditLog.created_at)).offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(q)).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [
            {
                "id": str(log.id),
                "user_email": log.user_email,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "details": log.details,
                "institution_id": str(log.institution_id),
                "institution_name": inst_name,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log, inst_name in rows
        ],
    }


# ---- Feature flags management ----

class FeatureFlagUpdate(BaseModel):
    enabled: Optional[bool] = None
    add_institution_ids: Optional[list[str]] = None
    remove_institution_ids: Optional[list[str]] = None


@router.get("/feature-flags")
async def list_feature_flags(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FeatureFlag).order_by(FeatureFlag.key))
    return [
        {
            "key": f.key,
            "enabled": f.enabled,
            "description": f.description,
            "allowed_institution_ids": f.allowed_institution_ids or [],
            "updated_at": f.updated_at.isoformat() if f.updated_at else None,
        }
        for f in result.scalars().all()
    ]


@router.put("/feature-flags/{key}")
async def update_feature_flag(
    key: str,
    data: FeatureFlagUpdate,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Enable/disable a pilot feature flag globally or per-institution."""
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail=f"Feature flag '{key}' neexistuje")

    before = {"enabled": flag.enabled, "allowed": list(flag.allowed_institution_ids or [])}

    if data.enabled is not None:
        flag.enabled = data.enabled

    current_set = set(flag.allowed_institution_ids or [])
    for iid in (data.add_institution_ids or []):
        current_set.add(iid)
    for iid in (data.remove_institution_ids or []):
        current_set.discard(iid)
    flag.allowed_institution_ids = sorted(current_set)
    flag.updated_at = datetime.now(timezone.utc)

    await _log_superadmin(
        db,
        current_user=current_user,
        target_institution_id=None,
        action="feature_flag_update",
        entity_type="feature_flag",
        entity_id=key,
        details={"key": key, "before": before, "after": {"enabled": flag.enabled, "allowed": list(flag.allowed_institution_ids)}},
    )
    await db.commit()
    return {
        "key": flag.key,
        "enabled": flag.enabled,
        "allowed_institution_ids": flag.allowed_institution_ids,
    }


# ---- Password reset (force-reset any user; superadmin-only) ----

class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str


@router.post("/reset-password")
async def reset_user_password(
    data: ResetPasswordRequest,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Force-reset any user's password. Also creates the user if the email is
    in SUPERADMIN_EMAILS and the account doesn't exist yet — useful for
    bootstrapping the secondary superadmin.
    """
    from core.security import hash_password
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Heslo musí mít alespoň 8 znaků")
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    created = False
    if not user:
        if data.email not in SUPERADMIN_EMAILS:
            raise HTTPException(status_code=404, detail="Uživatel nenalezen")
        # Bootstrap missing superadmin: place them in Budeživo Platform institution
        plat_res = await db.execute(
            select(Institution).where(Institution.name == PLATFORM_INSTITUTION_NAME)
        )
        platform = plat_res.scalar_one_or_none()
        if not platform:
            raise HTTPException(status_code=400, detail="Platform instituce ještě neexistuje — spusťte /setup/move-to-platform")
        user = User(
            id=uuid.uuid4(),
            institution_id=platform.id,
            email=data.email,
            password_hash=hash_password(data.new_password),
            name=data.email.split("@")[0],
            role="admin",
            status="active",
        )
        db.add(user)
        created = True
    else:
        user.password_hash = hash_password(data.new_password)

    await _log_superadmin(
        db,
        current_user=current_user,
        target_institution_id=str(user.institution_id),
        action="password_reset" if not created else "superadmin_bootstrap",
        entity_type="user",
        entity_id=str(user.id),
        details={"target_email": user.email, "created": created},
    )
    await db.commit()
    return {
        "message": (
            f"Superadmin {data.email} vytvořen v Platform instituci."
            if created else f"Heslo pro {data.email} bylo změněno."
        ),
        "email": data.email,
        "created": created,
    }



# ---- One-off: move superadmin users into a dedicated Platform institution ----

PLATFORM_INSTITUTION_NAME = "Budeživo Platform"


@router.post("/setup/move-to-platform")
async def move_superadmins_to_platform_institution(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Create a dedicated `Budeživo Platform` institution and move all users in
    SUPERADMIN_EMAILS there, so that normal customer institutions (incl.
    `Test Muzeum`) become deletable without the superadmin losing their login.

    Idempotent — calling again returns summary without duplicating rows.
    """
    # Find or create Platform institution
    result = await db.execute(
        select(Institution).where(Institution.name == PLATFORM_INSTITUTION_NAME)
    )
    platform = result.scalar_one_or_none()

    created = False
    if not platform:
        platform = Institution(
            id=uuid.uuid4(),
            name=PLATFORM_INSTITUTION_NAME,
            type="other",
            email="platform@budezivo.cz",
            plan="pro_plus",
            plan_status="active",
            plan_activated_by="system",
            billing_note="Interní instituce pro superadmin účty.",
        )
        db.add(platform)
        await db.flush()
        created = True

    # Move all superadmin users there
    moved = []
    users_res = await db.execute(
        select(User).where(User.email.in_(SUPERADMIN_EMAILS))
    )
    for user in users_res.scalars().all():
        if str(user.institution_id) == str(platform.id):
            continue
        old_iid = str(user.institution_id)
        user.institution_id = platform.id
        user.role = "admin"
        user.status = "active"
        user.deleted_at = None  # resurrect if previously soft-deleted
        moved.append({"email": user.email, "from": old_iid, "to": str(platform.id)})

    await _log_superadmin(
        db,
        current_user=current_user,
        target_institution_id=str(platform.id),
        action="setup_move_to_platform",
        entity_type="system",
        details={
            "platform_created": created,
            "platform_id": str(platform.id),
            "moved_users": moved,
        },
    )

    await db.commit()

    return {
        "message": (
            "Superadmin účty přesunuty do platformní instituce. "
            "Odhlaste se a přihlaste znovu pro obnovení session."
            if moved else
            "Superadmin účty již byly v platformní instituci."
        ),
        "platform_institution_id": str(platform.id),
        "platform_created_now": created,
        "moved_users": moved,
    }


# ---- Impersonation (Support debugging) ----

IMPERSONATION_MINUTES = 30


class ImpersonationStartRequest(BaseModel):
    reason: Optional[str] = None


@router.post("/impersonate/start/{user_id}")
async def start_impersonation(
    user_id: str,
    body: ImpersonationStartRequest,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Issue a short-lived JWT acting AS the target user, with a back-pointer
    (`impersonated_by_*`) so that every subsequent request carries both identities.

    Blocked: cannot impersonate another superadmin. Lifetime 30 minutes.
    """
    from core.security import create_jwt_token, COOKIE_NAME

    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target or target.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Uživatel nenalezen")
    if target.email in SUPERADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Nelze impersonovat jiného superadmina")
    if target.status != "active":
        raise HTTPException(status_code=400, detail="Uživatel není aktivní")

    token = create_jwt_token(
        user_id=str(target.id),
        institution_id=str(target.institution_id),
        email=target.email,
        role=target.role,
        impersonated_by_user_id=current_user["user_id"],
        impersonated_by_email=current_user["email"],
        expires_minutes=IMPERSONATION_MINUTES,
    )

    await _log_superadmin(
        db,
        current_user=current_user,
        target_institution_id=str(target.institution_id),
        action="impersonation_start",
        entity_type="user",
        entity_id=str(target.id),
        details={
            "target_email": target.email,
            "target_role": target.role,
            "reason": body.reason,
            "expires_in_minutes": IMPERSONATION_MINUTES,
        },
    )
    await db.commit()

    response = JSONResponse(content={
        "message": f"Impersonace zahájena jako {target.email}",
        "token": token,
        "target_user_id": str(target.id),
        "target_email": target.email,
        "expires_in_minutes": IMPERSONATION_MINUTES,
    })
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=IMPERSONATION_MINUTES * 60,
        path="/api",
    )
    return response


@router.post("/impersonate/stop")
async def stop_impersonation(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """End the current impersonation session and restore the original superadmin
    identity. Requires an active impersonation token."""
    from core.security import create_jwt_token, COOKIE_NAME

    original_uid = current_user.get("impersonated_by_user_id")
    original_email = current_user.get("impersonated_by_email")
    if not original_uid or not original_email:
        raise HTTPException(status_code=400, detail="Žádná aktivní impersonace")

    # Reload the original superadmin user (email still in SUPERADMIN_EMAILS)
    orig_res = await db.execute(select(User).where(User.id == original_uid))
    orig_user = orig_res.scalar_one_or_none()
    if not orig_user or orig_user.email not in SUPERADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Původní superadmin účet je nedostupný")

    token = create_jwt_token(
        user_id=str(orig_user.id),
        institution_id=str(orig_user.institution_id),
        email=orig_user.email,
        role=orig_user.role,
    )

    # Audit (log against superadmin's own institution since impersonation ended)
    synthetic_current = {
        "user_id": str(orig_user.id),
        "email": orig_user.email,
        "institution_id": str(orig_user.institution_id),
    }
    await _log_superadmin(
        db,
        current_user=synthetic_current,
        target_institution_id=str(current_user.get("institution_id")),
        action="impersonation_end",
        entity_type="user",
        entity_id=current_user["user_id"],
        details={
            "impersonated_email": current_user.get("email"),
        },
    )
    await db.commit()

    response = JSONResponse(content={
        "message": "Impersonace ukončena",
        "restored_email": orig_user.email,
        "token": token,
    })
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 60,
        path="/api",
    )
    return response
