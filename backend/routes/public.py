"""
Public statistics, ARES integration, and contact form routes.
"""
import httpx
import uuid
import os
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from database.supabase import get_db
from database.supabase_repositories import InstitutionRepositorySupabase
from services.email_service import EmailService

router = APIRouter(prefix="/public", tags=["Public"])
logger = logging.getLogger(__name__)

# Admin email for contact form submissions
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "info@budezivo.cz")


class ContactFormRequest(BaseModel):
    """Contact/demo form request model."""
    name: str
    institution: str
    email: EmailStr
    availability: str = ""
    source: str = "Kontaktní formulář"


@router.post("/contact")
async def submit_contact_form(
    data: ContactFormRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit contact/demo form. Sends email to admin.
    """
    async def send_contact_email():
        try:
            result = await EmailService.send_transactional_email(
                template_name="contact_form_submission",
                to_email=ADMIN_EMAIL,
                data={
                    "name": data.name,
                    "institution": data.institution,
                    "email": data.email,
                    "availability": data.availability,
                    "source": data.source,
                },
                reply_to=data.email,
            )
            logger.info(f"Contact form email sent: {result.get('status')} - {result.get('email_id')}")
        except Exception as e:
            logger.error(f"Failed to send contact form email: {str(e)}")
    
    background_tasks.add_task(send_contact_email)
    
    return {
        "status": "success",
        "message": "Děkujeme za váš zájem! Brzy vás budeme kontaktovat."
    }


@router.get("/stats")
async def get_public_stats(db: AsyncSession = Depends(get_db)):
    """
    Get public statistics for marketing purposes.
    Returns counts only if there are 20+ institutions.
    """
    try:
        # Count institutions
        result = await db.execute(text("SELECT COUNT(*) FROM institutions"))
        institution_count = result.scalar() or 0
        
        # Count reservations
        result = await db.execute(text("SELECT COUNT(*) FROM reservations"))
        reservation_count = result.scalar() or 0
        
        # Only show stats if we have 20+ institutions
        show_stats = institution_count >= 20
        
        return {
            "show_stats": show_stats,
            "institutions": institution_count if show_stats else 0,
            "reservations": reservation_count if show_stats else 0,
            "satisfaction": 95 if show_stats else 0  # Static for now
        }
    except Exception:
        # Return empty stats on error
        return {
            "show_stats": False,
            "institutions": 0,
            "reservations": 0,
            "satisfaction": 0
        }



@router.get("/institutions/{institution_id}")
async def get_public_institution_info(institution_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get public institution information for booking pages.
    Returns basic info: name, logo, plan (for feature gating).
    Logo is fetched from theme settings.
    """
    from database.supabase_repositories import ThemeRepositorySupabase
    
    # Handle demo institution
    if institution_id == "demo":
        return {
            "id": "demo",
            "name": "Demo Muzeum",
            "logo_url": None,
            "plan": "pro",  # Demo has PRO features
            "type": "museum"
        }
    
    try:
        institution_repo = InstitutionRepositorySupabase(db)
        theme_repo = ThemeRepositorySupabase(db)
        
        institution = await institution_repo.find_by_id(institution_id)
        
        if not institution:
            raise HTTPException(status_code=404, detail="Institution not found")
        
        # Get logo from theme settings
        theme = await theme_repo.find_by_institution(institution_id)
        logo_url = theme.get("logo_url") if theme else None
        
        # Return only public info
        return {
            "id": str(institution.get("id")),
            "name": institution.get("name"),
            "logo_url": logo_url,
            "plan": institution.get("plan", "free"),
            "type": institution.get("type")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/ares/{ico}")
async def validate_ico_ares(ico: str):
    """
    Validate IČO against ARES (Administrativní registr ekonomických subjektů).
    Returns company info if found.
    
    ARES API documentation: https://ares.gov.cz/
    """
    # Clean ICO - remove spaces
    ico = ico.strip()
    
    # Validate ICO format (7-8 digits)
    if not ico.isdigit() or len(ico) < 7 or len(ico) > 8:
        raise HTTPException(
            status_code=400, 
            detail="Neplatný formát IČ. IČ musí obsahovat 7-8 číslic."
        )
    
    # Pad ICO to 8 digits
    ico = ico.zfill(8)
    
    try:
        # ARES API v3 endpoint
        url = f"https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers={
                "Accept": "application/json"
            })
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="IČ nebylo nalezeno v registru ARES."
                )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail="Chyba při komunikaci s ARES. Zkuste to později."
                )
            
            data = response.json()
            
            # Extract relevant info from ARES response
            # Handle sidlo (address) - might be dict or might have textovaAdresa
            sidlo = data.get("sidlo", {})
            address = sidlo.get("textovaAdresa", "") if isinstance(sidlo, dict) else ""
            if not address and isinstance(sidlo, dict):
                address = _format_ares_address(sidlo)
            
            return {
                "valid": True,
                "ico": data.get("ico", ico),
                "name": data.get("obchodniJmeno", ""),
                "address": address,
                "legal_form": data.get("pravniForma", ""),  # Just the code
                "dic": data.get("dic", ""),
                "registration_date": data.get("datumVzniku", ""),
            }
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Vypršel čas při dotazu na ARES. Zkuste to později."
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Chyba při komunikaci s ARES: {str(e)}"
        )


def _format_ares_address(sidlo: dict) -> str:
    """Format ARES address object to string."""
    parts = []
    
    if sidlo.get("nazevUlice"):
        street = sidlo.get("nazevUlice", "")
        if sidlo.get("cisloDomovni"):
            street += f" {sidlo.get('cisloDomovni')}"
        if sidlo.get("cisloOrientacni"):
            street += f"/{sidlo.get('cisloOrientacni')}"
        parts.append(street)
    
    if sidlo.get("nazevObce"):
        city = sidlo.get("nazevObce", "")
        if sidlo.get("psc"):
            city = f"{sidlo.get('psc')} {city}"
        parts.append(city)
    
    return ", ".join(parts)
