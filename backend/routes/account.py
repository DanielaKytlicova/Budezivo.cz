"""
Account management routes - deletion, deactivation.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import UserRepositorySupabase, InstitutionRepositorySupabase
from database.models import User

router = APIRouter(prefix="/account", tags=["Account"])
logger = logging.getLogger(__name__)


class DeleteAccountRequest(BaseModel):
    """Request model for account deletion."""
    confirmation: str  # Must be "DELETE" to confirm


class DeleteAccountResponse(BaseModel):
    """Response model for account deletion."""
    status: str
    message: str


@router.delete("/delete", response_model=DeleteAccountResponse)
async def delete_account(
    request: DeleteAccountRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (deactivate) user account.
    
    This performs a soft delete - the account is deactivated but data is preserved
    for audit purposes. The user will no longer be able to log in.
    
    For institutions: Only individual users can delete their accounts.
    Institution accounts can only be deleted by admin.
    """
    # Validate confirmation
    if request.confirmation != "DELETE":
        raise HTTPException(
            status_code=400, 
            detail="Pro smazání účtu musíte zadat 'DELETE' jako potvrzení."
        )
    
    user_repo = UserRepositorySupabase(db)
    
    # Get user details
    user = await user_repo.find_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="Uživatel nenalezen")
    
    # Check if user is admin of institution
    if user.get("role") == "admin":
        # Get all users in institution
        institution_users = await user_repo.find_by_institution(current_user["institution_id"])
        admin_count = sum(1 for u in institution_users if u.get("role") == "admin")
        
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Nelze smazat jediného administrátora instituce. Nejprve přeneste správu na jiného uživatele."
            )
    
    # Soft delete - set deleted_at timestamp and status to inactive
    try:
        from sqlalchemy import update
        import uuid
        
        result = await db.execute(
            update(User)
            .where(User.id == uuid.UUID(current_user["user_id"]))
            .values(
                status="deleted",
                deleted_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Uživatel nenalezen")
        
        logger.info(f"User account deactivated: {current_user['user_id']}")
        
        return DeleteAccountResponse(
            status="deleted",
            message="Váš účet byl úspěšně deaktivován. Již se nebudete moci přihlásit."
        )
        
    except Exception as e:
        logger.error(f"Failed to delete account: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Nepodařilo se smazat účet")


@router.get("/status")
async def get_account_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current account status and information."""
    user_repo = UserRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)
    
    user = await user_repo.find_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="Uživatel nenalezen")
    
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    
    # Get all users count for institution
    institution_users = await user_repo.find_by_institution(current_user["institution_id"])
    
    return {
        "user": {
            "id": user.get("id"),
            "email": user.get("email"),
            "name": user.get("name"),
            "role": user.get("role"),
            "status": user.get("status"),
            "created_at": user.get("created_at"),
        },
        "institution": {
            "id": institution.get("id") if institution else None,
            "name": institution.get("name") if institution else None,
            "plan": institution.get("plan") if institution else None,
        },
        "can_delete": user.get("role") != "admin" or len([u for u in institution_users if u.get("role") == "admin"]) > 1,
    }
