"""
Authentication routes: register, login, verify, forgot password.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends

from models.schemas import UserCreate, UserLogin, TokenResponse, ForgotPasswordRequest
from core.security import hash_password, verify_password, create_jwt_token, get_current_user
from database.repositories import UserRepository, InstitutionRepository, ThemeRepository

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    """Register new user and institution."""
    user_repo = UserRepository()
    institution_repo = InstitutionRepository()
    theme_repo = ThemeRepository()
    
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
        "operating_start_date": user_data.operating_start_date,
        "operating_end_date": user_data.operating_end_date,
        "default_program_description": user_data.default_program_description,
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
        "gdpr_consent_date": institution["created_at"],
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
    
    # Create JWT token
    token = create_jwt_token(user["id"], institution["id"], user_data.email)
    
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
async def login(credentials: UserLogin):
    """Login existing user."""
    user_repo = UserRepository()
    institution_repo = InstitutionRepository()
    
    user = await user_repo.find_by_email(credentials.email)
    if not user or not verify_password(credentials.password, user["password_hash"]):
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
async def forgot_password(data: ForgotPasswordRequest):
    """Request password reset."""
    user_repo = UserRepository()
    user = await user_repo.find_by_email(data.email)
    
    if not user:
        # Don't reveal if email exists
        return {"message": "If email exists, password reset link has been sent"}
    
    # TODO: Send email with reset link
    logger.info(f"Password reset requested for {data.email}")
    return {"message": "If email exists, password reset link has been sent"}


@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """Verify JWT token validity."""
    return {"valid": True, "user": current_user}


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user info including role."""
    user_repo = UserRepository()
    user = await user_repo.find_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
