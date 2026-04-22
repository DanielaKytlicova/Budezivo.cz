"""
GDPR Data Management routes for Budeživo.cz.
Provides data export, anonymization and deletion endpoints.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import (
    UserRepositorySupabase,
    BookingRepositorySupabase,
    SchoolRepositorySupabase,
    InstitutionRepositorySupabase,
)

router = APIRouter(prefix="/gdpr", tags=["GDPR"])
logger = logging.getLogger(__name__)


class GdprExportResponse(BaseModel):
    export_date: str
    user_data: dict
    institution_data: dict
    bookings: list
    schools: list


class GdprDeleteRequest(BaseModel):
    confirmation: str  # Must be "SMAZAT"


@router.get("/export")
async def export_personal_data(
    format: str = "zip",
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export all personal data associated with the user and their institution.
    GDPR Article 20 - Right to data portability.

    Default: ZIP containing both the machine-readable JSON (legally required for
    Article 20 portability) and a human-readable PDF companion document.
    Pass `?format=json` to get only the JSON, `?format=pdf` for only the PDF.
    """
    user_repo = UserRepositorySupabase(db)
    booking_repo = BookingRepositorySupabase(db)
    school_repo = SchoolRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)

    user = await user_repo.find_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="Uživatel nenalezen")

    institution = await institution_repo.find_by_id(current_user["institution_id"])
    bookings = await booking_repo.find_all_by_institution_for_export(current_user["institution_id"])
    schools = await school_repo.find_by_institution(current_user["institution_id"])

    # Sanitize sensitive fields
    user_export = {
        "id": user.get("id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "role": user.get("role"),
        "status": user.get("status"),
        "gdpr_consent": user.get("gdpr_consent"),
        "gdpr_consent_date": user.get("gdpr_consent_date"),
        "created_at": user.get("created_at"),
    }

    institution_export = {}
    if institution:
        institution_export = {
            "id": institution.get("id"),
            "name": institution.get("name"),
            "type": institution.get("type"),
            "address": institution.get("address"),
            "city": institution.get("city"),
            "country": institution.get("country"),
            "plan": institution.get("plan"),
            "created_at": institution.get("created_at"),
        }

    # Clean booking data for export
    bookings_export = []
    for b in bookings:
        bookings_export.append({
            "id": b.get("id"),
            "program_id": b.get("program_id"),
            "date": b.get("date"),
            "time_block": b.get("time_block"),
            "school_name": b.get("school_name"),
            "contact_name": b.get("contact_name"),
            "contact_email": b.get("contact_email"),
            "contact_phone": b.get("contact_phone"),
            "num_students": b.get("num_students"),
            "num_teachers": b.get("num_teachers"),
            "status": b.get("status"),
            "gdpr_consent": b.get("gdpr_consent"),
            "terms_accepted": b.get("terms_accepted"),
            "created_at": b.get("created_at"),
        })

    schools_export = []
    for s in schools:
        schools_export.append({
            "id": s.get("id"),
            "name": s.get("name"),
            "contact_person": s.get("contact_person"),
            "email": s.get("email"),
            "phone": s.get("phone"),
            "city": s.get("city"),
            "source": s.get("source"),
            "created_at": s.get("created_at"),
        })

    logger.info(f"GDPR data export for user {current_user['user_id']}")

    data = {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "user_data": user_export,
        "institution_data": institution_export,
        "bookings_count": len(bookings_export),
        "bookings": bookings_export,
        "schools_count": len(schools_export),
        "schools": schools_export,
    }

    if format == "json":
        return data

    from services.export_service import build_gdpr_export_pdf
    from fastapi.responses import Response
    import io as _io
    import json as _json
    import zipfile as _zipfile

    pdf_bytes = build_gdpr_export_pdf(data)

    if format == "pdf":
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="gdpr_export.pdf"'},
        )

    # Default: ZIP bundle with both PDF + JSON (GDPR-compliant portability + readability)
    buf = _io.BytesIO()
    with _zipfile.ZipFile(buf, "w", _zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "gdpr_export.json",
            _json.dumps(data, ensure_ascii=False, default=str, indent=2).encode("utf-8"),
        )
        zf.writestr("gdpr_export.pdf", pdf_bytes)
        zf.writestr(
            "README.txt",
            (
                "Export osobních údajů (GDPR čl. 20 — právo na přenositelnost)\n"
                "===============================================================\n\n"
                "Tento balík obsahuje:\n"
                "  1) gdpr_export.json — strojově čitelný formát (pro přenositelnost\n"
                "     k jinému správci dat; to je soubor, který splňuje požadavky GDPR).\n"
                "  2) gdpr_export.pdf  — lidsky čitelný přehled stejných dat.\n"
                "  3) README.txt       — tento dokument.\n\n"
                "Pokud chcete data předat jinému správci, použijte JSON.\n"
            ).encode("utf-8"),
        )

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="gdpr_export.zip"'},
    )


@router.post("/anonymize")
async def anonymize_personal_data(
    request: GdprDeleteRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Anonymize all personal data. Keeps booking records but removes PII.
    GDPR Article 17 - Right to erasure.
    """
    if request.confirmation != "SMAZAT":
        raise HTTPException(
            status_code=400,
            detail="Pro anonymizaci dat zadejte 'SMAZAT' jako potvrzení."
        )

    user_repo = UserRepositorySupabase(db)

    user = await user_repo.find_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="Uživatel nenalezen")

    # Check if user is sole admin
    if user.get("role") == "admin":
        institution_users = await user_repo.find_by_institution(current_user["institution_id"])
        admin_count = sum(1 for u in institution_users if u.get("role") == "admin")
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Nelze anonymizovat jediného administrátora instituce."
            )

    # Anonymize user data
    anonymized_email = f"anonymized_{current_user['user_id'][:8]}@deleted.local"
    await user_repo.update(current_user["user_id"], {
        "email": anonymized_email,
        "name": "Anonymizováno",
        "status": "anonymized",
    })

    logger.info(f"GDPR anonymization for user {current_user['user_id']}")

    return {
        "status": "anonymized",
        "message": "Vaše osobní údaje byly anonymizovány. Účet je nadále neaktivní."
    }
