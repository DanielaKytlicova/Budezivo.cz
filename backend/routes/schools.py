"""
Schools CRM routes - including PRO features.
Uses Supabase (PostgreSQL) for database operations.
"""
import io
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import School, PropagationRequest
from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import (
    SchoolRepositorySupabase,
    InstitutionRepositorySupabase,
    ProgramRepositorySupabase
)

router = APIRouter(prefix="/schools", tags=["Schools"])
logger = logging.getLogger(__name__)


@router.get("", response_model=List[School])
async def get_schools(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all schools for institution."""
    school_repo = SchoolRepositorySupabase(db)
    return await school_repo.find_by_institution(current_user["institution_id"])


@router.get("/export-csv")
async def export_schools_csv(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export schools to CSV - PRO feature only."""
    institution_repo = InstitutionRepositorySupabase(db)
    school_repo = SchoolRepositorySupabase(db)
    
    # Check PRO status
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    if not institution or institution.get("plan") not in ["standard", "premium"]:
        raise HTTPException(status_code=403, detail="Tato funkce je dostupná pouze v PRO verzi")
    
    # Get schools
    schools = await school_repo.find_by_institution(current_user["institution_id"])
    
    # Generate CSV
    output = io.StringIO()
    output.write("Název školy;IČO;Email;Telefon;Město;Datum registrace\n")
    for school in schools:
        created = school.get("created_at", "")
        if hasattr(created, "strftime"):
            created = created.strftime("%d.%m.%Y")
        output.write(f"{school.get('name', '')};{school.get('ico', '')};{school.get('email', '')};{school.get('phone', '')};{school.get('city', '')};{created}\n")
    
    csv_content = output.getvalue()
    output.close()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=skoly_export.csv"}
    )


@router.post("/send-propagation")
async def send_propagation(
    request: PropagationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send program promotion to schools - PRO feature only."""
    institution_repo = InstitutionRepositorySupabase(db)
    program_repo = ProgramRepositorySupabase(db)
    school_repo = SchoolRepositorySupabase(db)
    
    # Check PRO status
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    if not institution or institution.get("plan") not in ["standard", "premium"]:
        raise HTTPException(status_code=403, detail="Tato funkce je dostupná pouze v PRO verzi")
    
    # Get program
    program = await program_repo.find_by_id(request.program_id, current_user["institution_id"])
    if not program:
        raise HTTPException(status_code=404, detail="Program nenalezen")
    
    # Get schools
    schools = await school_repo.find_by_ids(current_user["institution_id"], request.school_ids)
    if not schools:
        raise HTTPException(status_code=400, detail="Nebyly vybrány žádné školy")
    
    # Get PRO settings
    pro_settings = institution.get("pro_settings", {}) or {}
    subject = pro_settings.get("email_subject_template", "Nový program: {program_name}")
    body = pro_settings.get("email_body_template", 
        "Dobrý den,\n\nrádi bychom Vás informovali o novém programu {program_name}.\n\n"
        "{program_description}\n\nRezervovat můžete zde: {reservation_url}\n\n"
        "S pozdravem,\n{institution_name}"
    )
    
    reservation_url = f"https://budezivo.cz/booking/{current_user['institution_id']}?program={request.program_id}"
    
    # Format email
    subject = subject.replace("{program_name}", program.get("name_cs", ""))
    body = body.replace("{program_name}", program.get("name_cs", ""))
    body = body.replace("{program_description}", program.get("description_cs", ""))
    body = body.replace("{reservation_url}", reservation_url)
    body = body.replace("{institution_name}", institution.get("name", ""))
    
    # Mock send emails
    sent_count = 0
    for school in schools:
        logger.info(f"[PROPAGATION] Sending to {school.get('email')}: {subject}")
        sent_count += 1
    
    return {
        "message": f"Propagace odeslána {sent_count} školám",
        "sent_count": sent_count,
        "schools": [s.get("name") for s in schools]
    }
