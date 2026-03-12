"""
Public statistics and ARES integration routes.
"""
import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from database.supabase import get_db

router = APIRouter(prefix="/public", tags=["Public"])


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
    except Exception as e:
        # Return empty stats on error
        return {
            "show_stats": False,
            "institutions": 0,
            "reservations": 0,
            "satisfaction": 0
        }


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
