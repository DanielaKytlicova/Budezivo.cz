"""
Settings routes - institution, theme, PRO, notifications, locale, GDPR.
Uses Supabase (PostgreSQL) for database operations.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import (
    ThemeSettings, ThemeUpdate, ProSettings,
    InstitutionSettings, NotificationSettings, LocaleSettings, GdprSettings
)
from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import (
    InstitutionRepositorySupabase,
    ThemeRepositorySupabase,
    SettingsRepositorySupabase
)

router = APIRouter(prefix="/settings", tags=["Settings"])


# ============ Theme Settings ============

@router.get("/theme")
async def get_theme_settings(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get theme settings for current institution."""
    theme_repo = ThemeRepositorySupabase(db)
    theme = await theme_repo.find_by_institution(current_user["institution_id"])
    if not theme:
        theme = {
            "institution_id": current_user["institution_id"],
            "primary_color": "#1E293B",
            "secondary_color": "#84A98C",
            "accent_color": "#E9C46A",
            "logo_url": None,
            "header_style": "light",
            "footer_text": None
        }
    return theme


@router.get("/theme/public/{institution_id}")
async def get_public_theme_settings(institution_id: str, db: AsyncSession = Depends(get_db)):
    """Get public theme settings for booking page."""
    # Handle demo institution
    if institution_id == "demo":
        return {
            "institution_id": "demo",
            "primary_color": "#1E293B",
            "secondary_color": "#84A98C",
            "accent_color": "#E9C46A",
            "logo_url": None,
            "header_style": "light",
            "footer_text": "Demo Muzeum - Ukázkový rezervační systém"
        }
    
    theme_repo = ThemeRepositorySupabase(db)
    theme = await theme_repo.find_by_institution(institution_id)
    if not theme:
        theme = {
            "institution_id": institution_id,
            "primary_color": "#1E293B",
            "secondary_color": "#84A98C",
            "accent_color": "#E9C46A",
            "logo_url": None,
            "header_style": "light",
            "footer_text": None
        }
    return theme


@router.put("/theme", response_model=ThemeSettings)
async def update_theme_settings(
    theme_data: ThemeUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update theme settings."""
    theme_repo = ThemeRepositorySupabase(db)
    return await theme_repo.create_or_update(
        current_user["institution_id"],
        theme_data.model_dump()
    )


# ============ PRO Settings ============

@router.get("/pro")
async def get_pro_settings(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get PRO settings."""
    institution_repo = InstitutionRepositorySupabase(db)
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    
    default_settings = {
        "csv_export_enabled": True,
        "mass_propagation_enabled": True,
        "email_subject_template": "Nový program: {program_name}",
        "email_body_template": "Dobrý den,\n\nrádi bychom Vás informovali o novém programu {program_name}.\n\n{program_description}\n\nRezervovat můžete zde: {reservation_url}\n\nS pozdravem,\n{institution_name}"
    }
    
    pro_settings = institution.get("pro_settings", {}) or {}
    
    return {
        "plan": institution.get("plan", "free"),
        "is_pro": institution.get("plan") in ["standard", "premium"],
        "csv_export_exception": pro_settings.get("csv_export_exception", False),
        **default_settings,
        **pro_settings
    }


@router.put("/pro")
async def update_pro_settings(
    settings: ProSettings,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update PRO settings."""
    institution_repo = InstitutionRepositorySupabase(db)
    await institution_repo.update_pro_settings(
        current_user["institution_id"],
        settings.model_dump()
    )
    return {"message": "PRO nastavení uloženo"}


# ============ Notification Settings ============

@router.put("/notifications")
async def update_notification_settings(
    data: NotificationSettings,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update notification settings."""
    settings_repo = SettingsRepositorySupabase(db)
    await settings_repo.update_notifications(
        current_user["institution_id"],
        data.model_dump()
    )
    return {"message": "Notification settings updated"}


# ============ Locale Settings ============

@router.put("/locale")
async def update_locale_settings(
    data: LocaleSettings,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update locale settings."""
    settings_repo = SettingsRepositorySupabase(db)
    await settings_repo.update_locale(
        current_user["institution_id"],
        data.model_dump()
    )
    return {"message": "Locale settings updated"}


# ============ GDPR Settings ============

@router.put("/gdpr")
async def update_gdpr_settings(
    data: GdprSettings,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update GDPR settings."""
    settings_repo = SettingsRepositorySupabase(db)
    await settings_repo.update_gdpr(
        current_user["institution_id"],
        data.model_dump()
    )
    return {"message": "GDPR settings updated"}
