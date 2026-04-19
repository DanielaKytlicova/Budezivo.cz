"""
Plan management routes for Budeživo.cz
4-tier subscription system: free, start, pro, pro_plus
Hard-locked feature gating with payment/admin activation only.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import InstitutionRepositorySupabase, UserRepositorySupabase
from services.plan_service import (
    PLAN_ORDER, PLAN_LIMITS, PLAN_FEATURES, PLAN_LABELS,
    FEATURE_LABELS, FEATURE_MIN_PLAN,
    has_feature_access, get_plan_features, get_plan_limits,
)

router = APIRouter(prefix="/plan", tags=["Plan Management"])
logger = logging.getLogger(__name__)


# ---- Pydantic models ----

class PlanStatusResponse(BaseModel):
    plan: str
    plan_status: str
    plan_label: str
    is_pro: bool
    plan_activated_by: Optional[str] = None
    plan_updated_at: Optional[str] = None
    plan_expires_at: Optional[str] = None
    features: dict
    limits: dict


class RequestPlanChange(BaseModel):
    target_plan: str  # start, pro, pro_plus


class AdminPlanChange(BaseModel):
    institution_id: str
    target_plan: str
    target_status: str = "active"
    activated_by: str = "admin"


# ---- Routes ----

@router.get("/status")
async def get_plan_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current plan status, features, and limits."""
    inst_repo = InstitutionRepositorySupabase(db)
    inst = await inst_repo.find_by_id(current_user["institution_id"])
    if not inst:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")

    plan = inst.get("plan", "free")
    plan_status = inst.get("plan_status", "active")
    plan_updated = inst.get("plan_updated_at")
    plan_expires = inst.get("plan_expires_at")
    plan_activated_by = inst.get("plan_activated_by")

    features = get_plan_features(plan, plan_status)
    limits = get_plan_limits(plan, plan_status)

    return {
        "plan": plan,
        "plan_status": plan_status,
        "plan_label": PLAN_LABELS.get(plan, plan),
        "is_pro": plan in ("pro", "pro_plus") and plan_status == "active",
        "plan_activated_by": plan_activated_by,
        "plan_updated_at": plan_updated.isoformat() if plan_updated and hasattr(plan_updated, 'isoformat') else plan_updated,
        "plan_expires_at": plan_expires.isoformat() if plan_expires and hasattr(plan_expires, 'isoformat') else plan_expires,
        "features": features,
        "limits": limits,
    }


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
        "min_plan_label": PLAN_LABELS.get(min_plan, min_plan) if min_plan else None,
        "message": None if access else f"Tato funkce je dostupná od plánu {PLAN_LABELS.get(min_plan, 'Start')}",
    }


@router.get("/plans")
async def get_available_plans():
    """Get all available plans with their features and pricing."""
    plans = []
    for plan_key in PLAN_ORDER:
        features_set = PLAN_FEATURES.get(plan_key, set())
        feature_list = []
        for fk, label in FEATURE_LABELS.items():
            if fk in features_set:
                feature_list.append({"key": fk, "label": label})

        plans.append({
            "key": plan_key,
            "label": PLAN_LABELS[plan_key],
            "limits": PLAN_LIMITS[plan_key],
            "features": feature_list,
            "feature_keys": list(features_set),
        })
    return {"plans": plans}


@router.post("/request")
async def request_plan_change(
    data: RequestPlanChange,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request a plan upgrade. Creates pending state — requires payment or admin confirmation.
    
    This does NOT activate the plan directly. It sets plan_status=pending.
    """
    if data.target_plan not in PLAN_ORDER or data.target_plan == "free":
        raise HTTPException(status_code=400, detail="Neplatný cílový plán")

    # Only admin/spravce can request
    user_repo = UserRepositorySupabase(db)
    user = await user_repo.find_by_id(current_user["user_id"])
    if user.get("role") not in ("admin", "spravce"):
        raise HTTPException(status_code=403, detail="Pouze správci mohou změnit plán")

    inst_repo = InstitutionRepositorySupabase(db)
    inst = await inst_repo.find_by_id(current_user["institution_id"])
    if not inst:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")

    now = datetime.now(timezone.utc)

    # Set pending state
    await inst_repo.update(current_user["institution_id"], {
        "plan": data.target_plan,
        "plan_status": "pending",
        "plan_updated_at": now,
    })

    logger.info(f"Plan change requested: {current_user['institution_id']} → {data.target_plan} (pending)")

    return {
        "message": f"Žádost o plán {PLAN_LABELS.get(data.target_plan, data.target_plan)} přijata. Čeká na potvrzení platby.",
        "plan": data.target_plan,
        "plan_status": "pending",
    }


@router.post("/confirm-payment")
async def confirm_payment(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm payment and activate the pending plan.
    In MVP this is called after manual payment confirmation.
    Future: will be called by Stripe webhook.
    """
    inst_repo = InstitutionRepositorySupabase(db)
    inst = await inst_repo.find_by_id(current_user["institution_id"])
    if not inst:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")

    plan_status = inst.get("plan_status", "active")
    if plan_status != "pending":
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

    logger.info(f"Plan activated via payment: {current_user['institution_id']} → {plan}")

    return {
        "message": f"Plán {PLAN_LABELS.get(plan, plan)} byl aktivován",
        "plan": plan,
        "plan_status": "active",
    }


@router.put("/admin-change")
async def admin_change_plan(
    data: AdminPlanChange,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to manually change any institution's plan.
    Only superadmin (budezivo team) can use this.
    """
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

    return {
        "message": f"Plán instituce změněn na {PLAN_LABELS.get(data.target_plan, data.target_plan)}",
        "plan": data.target_plan,
        "plan_status": data.target_status,
    }


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


# ---- Legacy compatibility: /upgrade redirects to /request ----

@router.put("/upgrade")
async def legacy_upgrade(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """DEPRECATED: Redirect to plan request flow. No direct activation."""
    raise HTTPException(
        status_code=400,
        detail="Přímá aktivace není dostupná. Použijte stránku Plány pro výběr a objednání plánu."
    )


# ---- DB migration endpoint ----

@router.post("/setup-columns")
async def setup_plan_columns(
    db: AsyncSession = Depends(get_db),
):
    """Add new plan columns to institutions table."""
    results = []
    cols = [
        ("plan_status", "TEXT NOT NULL DEFAULT 'active'"),
        ("plan_activated_by", "TEXT"),
        ("plan_expires_at", "TIMESTAMPTZ"),
    ]
    for col_name, col_type in cols:
        try:
            await db.execute(text(f"ALTER TABLE institutions ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            await db.commit()
            results.append(f"{col_name}: added")
        except Exception as e:
            await db.rollback()
            results.append(f"{col_name}: {e}")

    # Migrate existing PRO → PRO+
    try:
        r = await db.execute(text("""
            UPDATE institutions 
            SET plan = 'pro_plus', plan_status = 'active', plan_activated_by = 'migration'
            WHERE plan = 'pro'
            RETURNING id
        """))
        migrated = len(r.fetchall())
        await db.commit()
        results.append(f"Migrated {migrated} PRO institutions to PRO+")
    except Exception as e:
        await db.rollback()
        results.append(f"Migration: {e}")

    return {"message": "Setup dokončen", "results": results}
