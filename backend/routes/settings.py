"""
Settings routes - institution, theme, PRO, notifications, locale, GDPR, logo upload.
Uses Supabase (PostgreSQL) for database operations.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body
from fastapi.responses import Response
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
logger = logging.getLogger(__name__)


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
        "is_pro": institution.get("plan") in ["standard", "premium", "pro", "pro_plus"],
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

# Canonical, normalized default structure (single source of truth).
CUSTOMER_NOTIF_KEYS = {
    "reservation_created": True,
    "reservation_confirmed": True,
    "reservation_cancelled": True,
    "visit_reminder": False,            # default OFF for existing institutions
    "event_registration_received": True,
    "event_registration_confirmed": True,
    "event_registration_cancelled": True,
}
ADMIN_NOTIF_KEYS = {
    "new_reservation": False,
    "reservation_cancelled": True,
    "event_capacity_reached": False,
    "new_event_registration": False,
    "integration_error": False,
}
ADMIN_RECIPIENT_ROLES = {"admin", "spravce", "edukator"}
NOTIF_MANAGE_ROLES = {"admin", "spravce"}


def normalize_notifications(stored: dict) -> dict:
    """Return the notification settings in the canonical nested shape, merging
    any stored values (incl. legacy flat keys) over the defaults."""
    stored = stored or {}
    customer = {**CUSTOMER_NOTIF_KEYS}
    admin = {**ADMIN_NOTIF_KEYS}

    stored_customer = stored.get("customer") or {}
    stored_admin = stored.get("admin") or {}
    for k in customer:
        if isinstance(stored_customer.get(k), bool):
            customer[k] = stored_customer[k]
    for k in admin:
        if isinstance(stored_admin.get(k), bool):
            admin[k] = stored_admin[k]

    # Legacy flat keys (best-effort mapping, only if nested not present)
    if "customer" not in stored and "confirmation" in stored:
        customer["reservation_confirmed"] = bool(stored.get("confirmation"))
    if "admin" not in stored:
        if "new_reservation" in stored:
            admin["new_reservation"] = bool(stored.get("new_reservation"))
        if "cancellation" in stored:
            admin["reservation_cancelled"] = bool(stored.get("cancellation"))

    recipients = stored_admin.get("recipient_user_ids")
    if not isinstance(recipients, list):
        recipients = []
    admin["recipient_user_ids"] = [str(x) for x in recipients]

    return {"customer": customer, "admin": admin}


@router.get("/notifications")
async def get_notification_settings(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the normalized notification settings for the institution."""
    institution_repo = InstitutionRepositorySupabase(db)
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    if not institution:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")
    return normalize_notifications(institution.get("notification_settings"))


@router.put("/notifications")
async def update_notification_settings(
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update notification settings. Only admin/spravce may change them.

    Accepts only known keys; unspecified parts are preserved; recipient IDs are
    validated to be active users of the same institution with an allowed role.
    Returns the actually-saved normalized values.
    """
    if current_user.get("role") not in NOTIF_MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Nastavení notifikací mohou měnit pouze správci a administrátoři.")

    institution_repo = InstitutionRepositorySupabase(db)
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    if not institution:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")

    current = normalize_notifications(institution.get("notification_settings"))

    incoming_customer = data.get("customer") or {}
    incoming_admin = data.get("admin") or {}
    for k in CUSTOMER_NOTIF_KEYS:
        if isinstance(incoming_customer.get(k), bool):
            current["customer"][k] = incoming_customer[k]
    for k in ADMIN_NOTIF_KEYS:
        if isinstance(incoming_admin.get(k), bool):
            current["admin"][k] = incoming_admin[k]

    # Validate & filter recipient_user_ids (same institution, allowed role, active)
    if "recipient_user_ids" in incoming_admin:
        raw_ids = incoming_admin.get("recipient_user_ids") or []
        valid_ids = []
        # Keep only syntactically valid UUIDs to avoid a DB cast error.
        clean_ids = []
        if isinstance(raw_ids, list):
            import uuid as _uuid
            for x in raw_ids:
                try:
                    clean_ids.append(str(_uuid.UUID(str(x))))
                except (ValueError, AttributeError, TypeError):
                    continue
        if clean_ids:
            from database.models import User
            from sqlalchemy import select, and_
            rows = (await db.execute(
                select(User.id).where(and_(
                    User.institution_id == current_user["institution_id"],
                    User.role.in_(list(ADMIN_RECIPIENT_ROLES)),
                    User.status == "active",
                    User.deleted_at.is_(None),
                    User.id.in_(clean_ids),
                ))
            )).all()
            valid_ids = [str(r[0]) for r in rows]
        current["admin"]["recipient_user_ids"] = valid_ids

    settings_repo = SettingsRepositorySupabase(db)
    await settings_repo.update_notifications(current_user["institution_id"], current)
    return current


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


# ============ Logo Upload ============


@router.post("/logo/upload")
async def upload_logo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload institution logo (PNG, JPG, SVG, WebP). Max 2 MB."""
    from services.storage_service import ALLOWED_IMAGE_TYPES, MAX_LOGO_SIZE, upload_logo

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Nepodporovaný formát. Povoleno: PNG, JPG, SVG, WebP")

    data = await file.read()
    if len(data) > MAX_LOGO_SIZE:
        raise HTTPException(status_code=400, detail="Soubor je příliš velký (max 2 MB)")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "png"

    try:
        storage_path = upload_logo(current_user["institution_id"], data, file.content_type, ext)
    except Exception as e:
        logger.error(f"Logo upload failed: {e}")
        raise HTTPException(status_code=500, detail="Nahrání loga selhalo")

    # Update institution and theme with new logo path
    institution_repo = InstitutionRepositorySupabase(db)
    theme_repo = ThemeRepositorySupabase(db)
    logo_url = f"/api/settings/logo/{storage_path}"

    await institution_repo.update(current_user["institution_id"], {"logo_url": logo_url})
    await theme_repo.create_or_update(current_user["institution_id"], {"logo_url": logo_url})

    logger.info(f"Logo uploaded for institution {current_user['institution_id']}: {storage_path}")
    return {"logo_url": logo_url, "message": "Logo úspěšně nahráno"}


@router.get("/logo/{path:path}")
async def serve_logo(path: str):
    """Serve uploaded logo from object storage. Public (used in <img> tags)."""
    from services.storage_service import get_object

    try:
        data, content_type = get_object(path)
    except Exception:
        raise HTTPException(status_code=404, detail="Logo nenalezeno")

    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )

    return {"message": "GDPR settings updated"}
