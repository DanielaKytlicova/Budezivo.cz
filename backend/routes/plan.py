"""
Plan management routes for Budeživo.cz
Handles PRO plan upgrades and feature gating.
"""
import logging
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import InstitutionRepositorySupabase, UserRepositorySupabase
from sqlalchemy import text

router = APIRouter(prefix="/plan", tags=["Plan Management"])
logger = logging.getLogger(__name__)


# ============ Pydantic Models ============

class PlanStatusResponse(BaseModel):
    plan: str
    is_pro: bool
    plan_updated_at: Optional[str] = None
    features: dict


class UpgradePlanRequest(BaseModel):
    confirm: bool = True


class DowngradePlanRequest(BaseModel):
    confirm: bool = True
    admin_key: Optional[str] = None  # Optional admin override key


# ============ Feature Definitions ============

FREE_FEATURES = {
    "csv_export": False,
    "bulk_email": False,
    "advanced_statistics": False,
    "sms_notifications": False,
    "custom_email_templates": False,
    "programs_limit": 3,
    "monthly_bookings_limit": 50
}

PRO_FEATURES = {
    "csv_export": True,
    "bulk_email": True,
    "advanced_statistics": True,
    "sms_notifications": True,
    "custom_email_templates": True,
    "programs_limit": -1,  # Unlimited
    "monthly_bookings_limit": -1  # Unlimited
}


def get_features_for_plan(plan: str) -> dict:
    """Get feature set for a given plan."""
    if plan == "pro":
        return PRO_FEATURES
    return FREE_FEATURES


# ============ Routes ============

@router.get("/status", response_model=PlanStatusResponse)
async def get_plan_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current plan status and available features.
    """
    institution_repo = InstitutionRepositorySupabase(db)
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    
    if not institution:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")
    
    plan = institution.get("plan", "free")
    plan_updated_at = institution.get("plan_updated_at")
    
    # Handle plan_updated_at - it might be a datetime object or already a string
    plan_updated_at_str = None
    if plan_updated_at:
        if isinstance(plan_updated_at, str):
            plan_updated_at_str = plan_updated_at
        else:
            plan_updated_at_str = plan_updated_at.isoformat()
    
    return PlanStatusResponse(
        plan=plan,
        is_pro=plan == "pro",
        plan_updated_at=plan_updated_at_str,
        features=get_features_for_plan(plan)
    )


@router.put("/upgrade")
async def upgrade_to_pro(
    request: UpgradePlanRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upgrade institution to PRO plan.
    Only admins/spravce can perform this action.
    """
    # Check if user is admin
    user_repo = UserRepositorySupabase(db)
    user = await user_repo.find_by_id(current_user["user_id"])
    
    if user.get("role") not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Pouze administrátoři mohou upgradovat plán")
    
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Je vyžadováno potvrzení")
    
    institution_repo = InstitutionRepositorySupabase(db)
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    
    if not institution:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")
    
    current_plan = institution.get("plan", "free")
    if current_plan == "pro":
        return {
            "message": "Instituce již má aktivní PRO verzi",
            "plan": "pro",
            "upgraded": False
        }
    
    # Upgrade to PRO
    now = datetime.now(timezone.utc)
    await institution_repo.update(current_user["institution_id"], {
        "plan": "pro",
        "plan_updated_at": now,
        "programs_limit": -1,
        "bookings_monthly_limit": -1
    })
    
    logger.info(f"Institution {current_user['institution_id']} upgraded to PRO by user {current_user['email']}")
    
    return {
        "message": "PRO verze byla úspěšně aktivována",
        "plan": "pro",
        "upgraded": True,
        "upgraded_at": now.isoformat(),
        "features": PRO_FEATURES
    }


@router.put("/downgrade")
async def downgrade_to_free(
    request: DowngradePlanRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Downgrade institution to FREE plan.
    This is a hidden admin/dev feature.
    Only admins can perform this action.
    """
    # Check if user is admin
    user_repo = UserRepositorySupabase(db)
    user = await user_repo.find_by_id(current_user["user_id"])
    
    if user.get("role") not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Pouze administrátoři mohou změnit plán")
    
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Je vyžadováno potvrzení")
    
    institution_repo = InstitutionRepositorySupabase(db)
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    
    if not institution:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")
    
    current_plan = institution.get("plan", "free")
    if current_plan == "free":
        return {
            "message": "Instituce již má FREE verzi",
            "plan": "free",
            "downgraded": False
        }
    
    # Downgrade to FREE
    now = datetime.now(timezone.utc)
    await institution_repo.update(current_user["institution_id"], {
        "plan": "free",
        "plan_updated_at": now,
        "programs_limit": 3,
        "bookings_monthly_limit": 50
    })
    
    logger.info(f"Institution {current_user['institution_id']} downgraded to FREE by user {current_user['email']}")
    
    return {
        "message": "Plán byl změněn na FREE verzi",
        "plan": "free",
        "downgraded": True,
        "downgraded_at": now.isoformat(),
        "features": FREE_FEATURES
    }


@router.get("/check-feature/{feature_name}")
async def check_feature_access(
    feature_name: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if current institution has access to a specific feature.
    """
    institution_repo = InstitutionRepositorySupabase(db)
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    
    if not institution:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")
    
    plan = institution.get("plan", "free")
    features = get_features_for_plan(plan)
    
    if feature_name not in features:
        raise HTTPException(status_code=400, detail="Neznámá funkce")
    
    has_access = features[feature_name]
    if isinstance(has_access, int):
        has_access = has_access != 0  # -1 (unlimited) or positive = has access
    
    return {
        "feature": feature_name,
        "has_access": has_access,
        "plan": plan,
        "message": None if has_access else "Tato funkce je dostupná pouze v PRO verzi"
    }



@router.post("/setup-columns")
async def setup_plan_columns(
    db: AsyncSession = Depends(get_db)
):
    """
    Add plan_updated_at column to institutions table.
    Also adds terms columns to reservations table.
    Public endpoint for initial setup.
    """
    results = []
    
    try:
        # Add plan_updated_at to institutions
        try:
            await db.execute(text("""
                ALTER TABLE institutions 
                ADD COLUMN IF NOT EXISTS plan_updated_at TIMESTAMPTZ
            """))
            await db.commit()
            results.append("plan_updated_at added to institutions")
        except Exception as e:
            await db.rollback()
            results.append(f"plan_updated_at: {str(e)}")
        
        # Add terms columns to reservations
        try:
            await db.execute(text("""
                ALTER TABLE reservations 
                ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN DEFAULT FALSE
            """))
            await db.commit()
            results.append("terms_accepted added to reservations")
        except Exception as e:
            await db.rollback()
            results.append(f"terms_accepted: {str(e)}")
        
        try:
            await db.execute(text("""
                ALTER TABLE reservations 
                ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ
            """))
            await db.commit()
            results.append("terms_accepted_at added to reservations")
        except Exception as e:
            await db.rollback()
            results.append(f"terms_accepted_at: {str(e)}")
        
        try:
            await db.execute(text("""
                ALTER TABLE reservations 
                ADD COLUMN IF NOT EXISTS terms_accepted_text_version TEXT DEFAULT 'v1'
            """))
            await db.commit()
            results.append("terms_accepted_text_version added to reservations")
        except Exception as e:
            await db.rollback()
            results.append(f"terms_accepted_text_version: {str(e)}")
        
        return {"message": "Migrace dokončena", "results": results}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Chyba: {str(e)}")