"""
Plan management routes for Budeživo.cz
4-tier subscription system: free → start → pro → pro_plus (hierarchical).
Hard-locked feature gating with payment/admin activation only.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import InstitutionRepositorySupabase, UserRepositorySupabase
from services.plan_service import (
    PLAN_ORDER, PLAN_LIMITS, PLAN_FEATURES, PLAN_LABELS,
    FEATURE_LABELS, FEATURE_MIN_PLAN,
    has_feature_access, get_plan_features_full, get_plan_limits,
    get_plan_hierarchy, compute_plan_diff,
)
from services.billing_service import create_billing_order

router = APIRouter(prefix="/plan", tags=["Plan Management"])
logger = logging.getLogger(__name__)


# ---- Pydantic models ----

class RequestPlanChange(BaseModel):
    target_plan: str

class AdminPlanChange(BaseModel):
    institution_id: str
    target_plan: str
    target_status: str = "active"
    activated_by: str = "admin"


# ---- Static routes (before /{dynamic}) ----

@router.get("/status")
async def get_plan_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Current plan status, features, and limits."""
    inst_repo = InstitutionRepositorySupabase(db)
    inst = await inst_repo.find_by_id(current_user["institution_id"])
    if not inst:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")

    plan = inst.get("plan", "free")
    plan_status = inst.get("plan_status", "active")
    plan_updated = inst.get("plan_updated_at")
    plan_expires = inst.get("plan_expires_at")
    plan_activated_by = inst.get("plan_activated_by")
    plan_activated_at = inst.get("plan_activated_at")

    return {
        "plan": plan,
        "plan_status": plan_status,
        "plan_label": PLAN_LABELS.get(plan, plan),
        "is_pro": plan in ("pro", "pro_plus") and plan_status == "active",
        "plan_activated_by": plan_activated_by,
        "plan_activated_at": plan_activated_at.isoformat() if plan_activated_at and hasattr(plan_activated_at, 'isoformat') else plan_activated_at,
        "plan_updated_at": plan_updated.isoformat() if plan_updated and hasattr(plan_updated, 'isoformat') else plan_updated,
        "plan_expires_at": plan_expires.isoformat() if plan_expires and hasattr(plan_expires, 'isoformat') else plan_expires,
        "features": get_plan_features_full(plan, plan_status),
        "limits": get_plan_limits(plan, plan_status),
    }


@router.get("/plans")
async def get_available_plans():
    """All plans with hierarchical features (no duplication)."""
    return {"plans": get_plan_hierarchy()}


@router.get("/diff")
async def get_plan_diff(
    from_plan: str,
    to_plan: str,
):
    """Compute gained/lost features between two plans (for switch modal)."""
    if from_plan not in PLAN_ORDER or to_plan not in PLAN_ORDER:
        raise HTTPException(status_code=400, detail="Neplatný plán")
    return compute_plan_diff(from_plan, to_plan)


@router.get("/check-feature/{feature_key}")
async def check_feature(
    feature_key: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if current institution has access to a specific feature."""
    inst_repo = InstitutionRepositorySupabase(db)
    inst = await inst_repo.find_by_id(current_user["institution_id"])
    if not inst:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")

    plan = inst.get("plan", "free")
    plan_status = inst.get("plan_status", "active")
    access = has_feature_access(plan, plan_status, feature_key)
    min_plan = FEATURE_MIN_PLAN.get(feature_key)

    return {
        "feature": feature_key,
        "has_access": access,
        "plan": plan,
        "plan_status": plan_status,
        "min_plan": min_plan,
        "min_plan_label": PLAN_LABELS.get(min_plan) if min_plan else None,
        "message": None if access else f"Tato funkce je dostupná od plánu {PLAN_LABELS.get(min_plan, 'Start')}",
    }


# ---- Mutation routes ----

@router.post("/request")
async def request_plan_change(
    data: RequestPlanChange,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request a plan change. Creates billing order + sets pending state."""
    if data.target_plan not in PLAN_ORDER or data.target_plan == "free":
        raise HTTPException(status_code=400, detail="Neplatný cílový plán")

    user_repo = UserRepositorySupabase(db)
    user = await user_repo.find_by_id(current_user["user_id"])
    if user.get("role") not in ("admin", "spravce"):
        raise HTTPException(status_code=403, detail="Pouze správci mohou změnit plán")

    inst_repo = InstitutionRepositorySupabase(db)
    now = datetime.now(timezone.utc)

    # Create billing order
    prices = {"start": 49000, "pro": 99000, "pro_plus": 199000}
    order_result = await create_billing_order(
        db=db,
        institution_id=current_user["institution_id"],
        requested_plan=data.target_plan,
        provider="manual",
        amount=prices.get(data.target_plan, 0),
        currency="CZK",
        created_by=current_user["user_id"],
    )

    await inst_repo.update(current_user["institution_id"], {
        "requested_plan_type": data.target_plan,
        "plan_status": "pending",
        "plan_updated_at": now,
        "plan_changed_by_user_id": current_user["user_id"],
    })

    logger.info(f"Plan change requested: {current_user['institution_id']} → {data.target_plan} (pending, order={order_result['order_id']})")

    return {
        "message": f"Žádost o plán {PLAN_LABELS.get(data.target_plan, data.target_plan)} přijata. Čeká na potvrzení platby.",
        "plan": data.target_plan,
        "plan_status": "pending",
        "order_id": order_result["order_id"],
    }


@router.post("/confirm-payment")
async def confirm_payment(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm payment and activate the pending plan."""
    inst_repo = InstitutionRepositorySupabase(db)
    inst = await inst_repo.find_by_id(current_user["institution_id"])
    if not inst:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")

    if inst.get("plan_status") != "pending":
        raise HTTPException(status_code=400, detail="Žádný plán nečeká na potvrzení")

    plan = inst.get("plan", "free")
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    now = datetime.now(timezone.utc)

    await inst_repo.update(current_user["institution_id"], {
        "plan_status": "active",
        "plan_activated_by": "payment",
        "plan_updated_at": now,
        "programs_limit": limits["programs_limit"],
        "bookings_monthly_limit": limits["bookings_monthly_limit"],
    })

    return {"message": f"Plán {PLAN_LABELS.get(plan, plan)} byl aktivován", "plan": plan, "plan_status": "active"}


@router.put("/admin-change")
async def admin_change_plan(
    data: AdminPlanChange,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to manually change any institution's plan."""
    user_repo = UserRepositorySupabase(db)
    user = await user_repo.find_by_id(current_user["user_id"])
    if user.get("role") not in ("admin", "spravce"):
        raise HTTPException(status_code=403, detail="Nedostatečná oprávnění")

    if data.target_plan not in PLAN_ORDER:
        raise HTTPException(status_code=400, detail="Neplatný plán")

    inst_repo = InstitutionRepositorySupabase(db)
    inst = await inst_repo.find_by_id(data.institution_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")

    limits = PLAN_LIMITS.get(data.target_plan, PLAN_LIMITS["free"])
    now = datetime.now(timezone.utc)

    await inst_repo.update(data.institution_id, {
        "plan": data.target_plan,
        "plan_status": data.target_status,
        "plan_activated_by": data.activated_by,
        "plan_updated_at": now,
        "programs_limit": limits["programs_limit"],
        "bookings_monthly_limit": limits["bookings_monthly_limit"],
    })

    logger.info(f"Admin plan change: {data.institution_id} → {data.target_plan}/{data.target_status} by {current_user['email']}")
    return {"message": f"Plán změněn na {PLAN_LABELS.get(data.target_plan)}", "plan": data.target_plan, "plan_status": data.target_status}


@router.put("/downgrade")
async def downgrade_to_free(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Downgrade to free plan."""
    user_repo = UserRepositorySupabase(db)
    user = await user_repo.find_by_id(current_user["user_id"])
    if user.get("role") not in ("admin", "spravce"):
        raise HTTPException(status_code=403, detail="Pouze správci mohou změnit plán")

    inst_repo = InstitutionRepositorySupabase(db)
    limits = PLAN_LIMITS["free"]
    now = datetime.now(timezone.utc)

    await inst_repo.update(current_user["institution_id"], {
        "plan": "free",
        "plan_status": "active",
        "plan_activated_by": None,
        "plan_updated_at": now,
        "programs_limit": limits["programs_limit"],
        "bookings_monthly_limit": limits["bookings_monthly_limit"],
    })

    return {"message": "Plán změněn na Free", "plan": "free", "plan_status": "active"}


@router.put("/upgrade")
async def legacy_upgrade(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """BLOCKED: No direct activation."""
    raise HTTPException(status_code=400, detail="Přímá aktivace není dostupná. Použijte stránku Plány pro objednání.")


# NOTE: The one-off `POST /plan/setup-columns` migration endpoint was REMOVED
# (security audit P0). It executed unauthenticated DDL (`ALTER TABLE institutions`)
# and a mass `UPDATE institutions SET plan='pro_plus'`, letting any anonymous caller
# alter the DB schema and bulk-upgrade every tenant's plan. The migration is already
# applied; schema changes must go through Alembic, not a live HTTP endpoint.
