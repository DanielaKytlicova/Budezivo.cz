"""
Team Invitation routes for Budeživo.cz
Handles sending invitations and accepting them via secure tokens.
"""
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from core.security import hash_password, get_current_user
from database.supabase import get_db
from database.supabase_repositories import UserRepositorySupabase, InstitutionRepositorySupabase
from database.models import TeamInvitation, User
from services.email_service import EmailService

router = APIRouter(prefix="/invitations", tags=["Team Invitations"])
logger = logging.getLogger(__name__)

# Valid roles for team members
VALID_ROLES = ["spravce", "edukator", "lektor", "pokladni", "produkcni", "ucetni", "admin", "staff", "viewer"]


# ============ Pydantic Schemas ============

class InviteRequest(BaseModel):
    """Schema for creating a team invitation."""
    email: EmailStr
    name: Optional[str] = None
    role: str = "edukator"


class AcceptInviteRequest(BaseModel):
    """Schema for accepting an invitation."""
    token: str
    password: str
    name: Optional[str] = None


class TestInviteEmailRequest(BaseModel):
    """Schema for testing invitation email."""
    email: EmailStr


# ============ Helper Functions ============

def generate_invitation_token() -> str:
    """Generate a secure random token for invitations."""
    return secrets.token_urlsafe(32)


# ============ Admin Routes ============

@router.post("/send")
async def send_invitation(
    invite_data: InviteRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a team invitation email.
    Only admins/spravce can invite new team members.
    """
    user_repo = UserRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)
    
    # Check if current user is admin
    user = await user_repo.find_by_id(current_user["user_id"])
    if user.get("role") not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Pouze administrátoři mohou zvát členy týmu")
    
    # Check if email already exists as a user
    existing_user = await user_repo.find_by_email(invite_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Uživatel s tímto emailem již existuje")
    
    # Validate role
    if invite_data.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Neplatná role")
    
    # Get institution info
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    if not institution:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")
    
    # Check for existing pending invitation
    existing_invite = await db.execute(
        select(TeamInvitation).where(
            TeamInvitation.email == invite_data.email,
            TeamInvitation.institution_id == current_user["institution_id"],
            TeamInvitation.accepted == False,
            TeamInvitation.expires_at > datetime.now(timezone.utc)
        )
    )
    existing = existing_invite.scalar_one_or_none()
    
    if existing:
        # Update existing invitation with new token
        token = generate_invitation_token()
        existing.token = token
        existing.expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
        existing.role = invite_data.role
        existing.name = invite_data.name
        await db.commit()
    else:
        # Create new invitation
        token = generate_invitation_token()
        invitation = TeamInvitation(
            email=invite_data.email,
            institution_id=current_user["institution_id"],
            invited_by_user_id=current_user["user_id"],
            token=token,
            role=invite_data.role,
            name=invite_data.name,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48)
        )
        db.add(invitation)
        await db.commit()
    
    # Send invitation email in background
    async def send_invite_email():
        try:
            invite_link = f"https://www.budezivo.cz/accept-invite?token={token}"
            
            await EmailService.send_transactional_email(
                template_name="team_invitation",
                to_email=invite_data.email,
                data={
                    "invitee_name": invite_data.name or invite_data.email.split('@')[0],
                    "inviter_name": user.get("name") or user.get("email", "").split('@')[0],
                    "institution_name": institution.get("name", ""),
                    "role_name": get_role_display_name(invite_data.role),
                    "invite_link": invite_link,
                    "expires_hours": 48,
                },
            )
            logger.info(f"Invitation email sent to {invite_data.email}")
        except Exception as e:
            logger.error(f"Failed to send invitation email: {str(e)}")
    
    background_tasks.add_task(send_invite_email)
    
    logger.info(f"Team invitation created for {invite_data.email} by {current_user['email']}")
    
    return {
        "message": "Pozvánka byla odeslána",
        "email": invite_data.email,
        "expires_in_hours": 48
    }


@router.get("/pending")
async def get_pending_invitations(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all pending invitations for the institution."""
    result = await db.execute(
        select(TeamInvitation).where(
            TeamInvitation.institution_id == current_user["institution_id"],
            TeamInvitation.accepted == False,
            TeamInvitation.expires_at > datetime.now(timezone.utc)
        ).order_by(TeamInvitation.created_at.desc())
    )
    invitations = result.scalars().all()
    
    return [
        {
            "id": str(inv.id),
            "email": inv.email,
            "name": inv.name,
            "role": inv.role,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
        for inv in invitations
    ]


@router.delete("/{invitation_id}")
async def cancel_invitation(
    invitation_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a pending invitation."""
    result = await db.execute(
        select(TeamInvitation).where(
            TeamInvitation.id == invitation_id,
            TeamInvitation.institution_id == current_user["institution_id"]
        )
    )
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Pozvánka nenalezena")
    
    await db.delete(invitation)
    await db.commit()
    
    return {"message": "Pozvánka byla zrušena"}


# ============ Public Routes ============

@router.get("/verify/{token}")
async def verify_invitation(token: str, db: AsyncSession = Depends(get_db)):
    """
    Verify an invitation token and return invitation details.
    Public endpoint - no auth required.
    """
    result = await db.execute(
        select(TeamInvitation).where(TeamInvitation.token == token)
    )
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Pozvánka nebyla nalezena")
    
    if invitation.accepted:
        raise HTTPException(status_code=400, detail="Tato pozvánka již byla použita")
    
    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Platnost pozvánky vypršela")
    
    # Get institution info
    institution_repo = InstitutionRepositorySupabase(db)
    institution = await institution_repo.find_by_id(str(invitation.institution_id))
    
    return {
        "email": invitation.email,
        "name": invitation.name,
        "role": invitation.role,
        "institution_name": institution.get("name", "") if institution else "",
        "institution_logo": institution.get("logo_url") if institution else None,
        "expires_at": invitation.expires_at.isoformat() if invitation.expires_at else None,
    }


@router.post("/accept")
async def accept_invitation(
    accept_data: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Accept an invitation and create a new user account.
    Public endpoint - no auth required.
    """
    # Find invitation
    result = await db.execute(
        select(TeamInvitation).where(TeamInvitation.token == accept_data.token)
    )
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Pozvánka nebyla nalezena")
    
    if invitation.accepted:
        raise HTTPException(status_code=400, detail="Tato pozvánka již byla použita")
    
    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Platnost pozvánky vypršela")
    
    # Validate password
    if len(accept_data.password) < 8:
        raise HTTPException(status_code=400, detail="Heslo musí mít alespoň 8 znaků")
    
    # Check if user already exists
    user_repo = UserRepositorySupabase(db)
    existing = await user_repo.find_by_email(invitation.email)
    if existing:
        raise HTTPException(status_code=400, detail="Uživatel s tímto emailem již existuje")
    
    # Create user
    user = await user_repo.create({
        "email": invitation.email,
        "password_hash": hash_password(accept_data.password),
        "institution_id": str(invitation.institution_id),
        "role": invitation.role,
        "name": accept_data.name or invitation.name,
        "status": "active",
        "invited_by": str(invitation.invited_by_user_id) if invitation.invited_by_user_id else None,
    })
    
    # Mark invitation as accepted
    invitation.accepted = True
    invitation.accepted_at = datetime.now(timezone.utc)
    await db.commit()
    
    logger.info(f"Invitation accepted: {invitation.email} joined institution {invitation.institution_id}")
    
    return {
        "message": "Účet byl úspěšně vytvořen",
        "email": invitation.email,
        "redirect_to": "/login"
    }


# ============ Test Routes ============

@router.post("/test-email")
async def test_invitation_email(
    test_data: TestInviteEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a test invitation email.
    Only admins can use this endpoint.
    """
    user_repo = UserRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)
    
    user = await user_repo.find_by_id(current_user["user_id"])
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    
    async def send_test_email():
        try:
            test_link = "https://www.budezivo.cz/accept-invite?token=TEST_TOKEN_123"
            
            await EmailService.send_transactional_email(
                template_name="team_invitation",
                to_email=test_data.email,
                data={
                    "invitee_name": "Test User",
                    "inviter_name": user.get("name") or user.get("email", "").split('@')[0],
                    "institution_name": institution.get("name", "") if institution else "Test Institution",
                    "role_name": "Edukátor",
                    "invite_link": test_link,
                    "expires_hours": 48,
                },
            )
            logger.info(f"Test invitation email sent to {test_data.email}")
        except Exception as e:
            logger.error(f"Failed to send test invitation email: {str(e)}")
    
    background_tasks.add_task(send_test_email)
    
    return {"message": f"Testovací email bude odeslán na {test_data.email}"}


# ============ Setup Routes ============

@router.post("/setup-table")
async def setup_invitations_table(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create the team_invitations table if it doesn't exist.
    Admin only endpoint.
    """
    user_repo = UserRepositorySupabase(db)
    user = await user_repo.find_by_id(current_user["user_id"])
    
    if user.get("role") not in ["admin", "spravce"]:
        raise HTTPException(status_code=403, detail="Pouze administrátoři")
    
    try:
        # Check if table exists
        check_query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'team_invitations'
            );
        """)
        result = await db.execute(check_query)
        exists = result.scalar()
        
        if exists:
            return {"message": "Tabulka team_invitations již existuje", "created": False}
        
        # Create table - separate statements for asyncpg compatibility
        create_table = text("""
            CREATE TABLE team_invitations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT NOT NULL,
                institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
                invited_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                token TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL DEFAULT 'viewer',
                name TEXT,
                expires_at TIMESTAMPTZ NOT NULL,
                accepted BOOLEAN DEFAULT FALSE,
                accepted_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await db.execute(create_table)
        
        # Create indexes separately
        await db.execute(text("CREATE INDEX idx_team_invitations_email ON team_invitations(email)"))
        await db.execute(text("CREATE INDEX idx_team_invitations_token ON team_invitations(token)"))
        await db.execute(text("CREATE INDEX idx_team_invitations_institution ON team_invitations(institution_id)"))
        
        await db.commit()
        
        logger.info("team_invitations table created successfully")
        return {"message": "Tabulka team_invitations byla vytvořena", "created": True}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create team_invitations table: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chyba při vytváření tabulky: {str(e)}")


# ============ Helper Functions ============

def get_role_display_name(role: str) -> str:
    """Get human-readable role name in Czech."""
    role_names = {
        "admin": "Administrátor",
        "spravce": "Správce",
        "edukator": "Edukátor",
        "lektor": "Externí lektor",
        "pokladni": "Pokladní",
        "viewer": "Čtenář",
        "staff": "Zaměstnanec",
    }
    return role_names.get(role, role.capitalize())
