"""
Onboarding routes - checks and manages onboarding status for new institutions.
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from core.security import get_current_user
from database.supabase import get_db
from database.models import Institution, Program

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_onboarding_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get onboarding status for current institution."""
    institution_id = current_user["institution_id"]

    # Check onboarding_completed flag
    result = await db.execute(
        select(Institution.onboarding_completed).where(Institution.id == institution_id)
    )
    completed = result.scalar_one_or_none()
    if completed:
        return {"completed": True, "steps": {}}

    # Check progress: count active programs
    prog_result = await db.execute(
        select(func.count(Program.id)).where(
            Program.institution_id == institution_id,
            Program.status != "archived"
        )
    )
    program_count = prog_result.scalar() or 0

    return {
        "completed": False,
        "steps": {
            "has_programs": program_count > 0,
            "program_count": program_count,
        }
    }


@router.post("/complete")
async def complete_onboarding(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark onboarding as completed."""
    institution_id = current_user["institution_id"]
    await db.execute(
        update(Institution)
        .where(Institution.id == institution_id)
        .values(onboarding_completed=True)
    )
    await db.commit()
    return {"message": "Onboarding dokončen"}
