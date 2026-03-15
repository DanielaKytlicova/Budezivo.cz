"""
Authentication routes: register, login, verify, forgot password.
Uses Supabase (PostgreSQL) for database operations.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import UserCreate, UserLogin, TokenResponse, ForgotPasswordRequest
from core.security import hash_password, verify_password, create_jwt_token, get_current_user
from database.supabase import get_db
from database.supabase_repositories import (
    UserRepositorySupabase, 
    InstitutionRepositorySupabase, 
    ThemeRepositorySupabase
)
from services.email_service import (
    trigger_user_registration_email,
    trigger_password_reset_email,
    EmailService,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserCreate, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Register new user and institution."""
    user_repo = UserRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)
    theme_repo = ThemeRepositorySupabase(db)
    
    # Check if user exists
    existing = await user_repo.find_by_email(user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create institution
    institution = await institution_repo.create({
        "name": user_data.institution_name,
        "type": user_data.institution_type,
        "country": user_data.country,
        "address": user_data.address,
        "city": user_data.city,
        "ico_dic": user_data.ico_dic,
        "logo_url": user_data.logo_url,
        "default_available_days": user_data.default_available_days or ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "default_time_blocks": user_data.default_time_blocks or [{"start": "09:00", "end": "10:00"}],
        "default_program_duration": user_data.default_program_duration or 60,
        "default_program_capacity": user_data.default_program_capacity or 30,
        "default_target_group": user_data.default_target_group or "schools",
        "plan": "free",
        "programs_limit": 3,
    })
    
    # Create user
    user = await user_repo.create({
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "institution_id": institution["id"],
        "role": "admin",
        "gdpr_consent": user_data.gdpr_consent,
    })
    
    # Create default theme settings
    await theme_repo.create_or_update(institution["id"], {
        "primary_color": user_data.primary_color or "#1E293B",
        "secondary_color": user_data.secondary_color or "#84A98C",
        "accent_color": "#E9C46A",
        "logo_url": user_data.logo_url,
        "header_style": "light",
        "footer_text": None
    })
    
    # Send registration confirmation email in background
    async def send_registration_emails():
        try:
            # Send welcome email to the new user
            await trigger_user_registration_email(
                user_email=user_data.email,
                user_name=user_data.email.split('@')[0],  # Use email prefix as name
                institution_name=user_data.institution_name,
            )
            logger.info(f"Registration confirmation email sent to {user_data.email}")
            
            # Send notification to admin about new institution (optional)
            admin_email = "info@budezivo.cz"
            await EmailService.send_transactional_email(
                template_name="new_institution_registration",
                to_email=admin_email,
                data={
                    "institution_name": user_data.institution_name,
                    "institution_type": user_data.institution_type,
                    "user_email": user_data.email,
                    "institution_city": user_data.city or "",
                },
            )
            logger.info(f"New institution notification sent to admin")
        except Exception as e:
            logger.error(f"Failed to send registration emails: {str(e)}")
    
    background_tasks.add_task(send_registration_emails)
    
    # Create JWT token
    token = create_jwt_token(user["id"], institution["id"], user_data.email)
    
    logger.info(f"New institution registered: {user_data.institution_name} ({user_data.email})")
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user_data.email,
            "institution_id": institution["id"],
            "institution_name": user_data.institution_name,
            "role": "admin"
        }
    }


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login existing user."""
    user_repo = UserRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)
    
    user = await user_repo.find_by_email(credentials.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Get password hash from database (need to query without excluding it)
    from sqlalchemy import select
    from database.models import User
    result = await db.execute(select(User).where(User.email == credentials.email))
    user_obj = result.scalar_one_or_none()
    
    if not user_obj or not verify_password(credentials.password, user_obj.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    institution = await institution_repo.find_by_id(user["institution_id"])
    token = create_jwt_token(user["id"], user["institution_id"], user["email"])
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "institution_id": user["institution_id"],
            "institution_name": institution["name"] if institution else "",
            "role": user["role"]
        }
    }


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset."""
    user_repo = UserRepositorySupabase(db)
    user = await user_repo.find_by_email(data.email)
    
    if not user:
        # Don't reveal if email exists
        return {"message": "If email exists, password reset link has been sent"}
    
    # Generate reset token (in production, save this to DB with expiration)
    import secrets
    reset_token = secrets.token_urlsafe(32)
    reset_link = f"https://budezivo.cz/reset-password?token={reset_token}&email={data.email}"
    
    # Send password reset email in background
    async def send_reset_email():
        try:
            await trigger_password_reset_email(
                user_email=data.email,
                reset_link=reset_link,
            )
            logger.info(f"Password reset email sent to {data.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
    
    background_tasks.add_task(send_reset_email)
    
    logger.info(f"Password reset requested for {data.email}")
    return {"message": "If email exists, password reset link has been sent"}


@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """Verify JWT token validity."""
    return {"valid": True, "user": current_user}


@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user info including role."""
    user_repo = UserRepositorySupabase(db)
    user = await user_repo.find_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
