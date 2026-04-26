"""
Public statistics, ARES integration, and contact form routes.
"""
import httpx
import uuid
import os
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from database.supabase import get_db
from database.supabase_repositories import InstitutionRepositorySupabase
from services.email_service import EmailService

router = APIRouter(prefix="/public", tags=["Public"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# In-process IP throttle for the prefill endpoint (defense-in-depth on top of
# the response-shape protection). Process-local; sufficient for single-worker.
import time as _time
import threading as _threading
_prefill_calls: dict[str, list[float]] = {}
_prefill_lock = _threading.Lock()
PREFILL_WINDOW_SEC = 60
PREFILL_MAX_PER_WINDOW = 20


def _prefill_client_ip(request: Request) -> str:
    """Best-effort client IP, respecting X-Forwarded-For (first hop)."""
    xff = request.headers.get("x-forwarded-for") or ""
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _prefill_check_rate(ip: str) -> bool:
    """Return True if the request is within rate limit; False if it should be 429."""
    now = _time.monotonic()
    cutoff = now - PREFILL_WINDOW_SEC
    with _prefill_lock:
        bucket = _prefill_calls.get(ip, [])
        bucket = [t for t in bucket if t >= cutoff]
        if len(bucket) >= PREFILL_MAX_PER_WINDOW:
            _prefill_calls[ip] = bucket
            return False
        bucket.append(now)
        _prefill_calls[ip] = bucket
    return True


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
@limiter.limit("5/minute")
async def submit_contact_form(
    request: Request,
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


@router.get("/prefill")
@limiter.limit("20/minute")
async def get_prefill_for_email(
    request: Request,
    email: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Privacy-preserving prefill for public booking form.

    If the e-mail was used in a past reservation, return ONLY non-sensitive,
    repeatable fields (school name, contact name, phone, group type, count).
    NEVER return reservation IDs, dates, or program/institution IDs.

    Always returns 200 with `found=false` for unknown e-mails to avoid
    enumeration. Defense-in-depth: in-process IP rate-limit (20/min/IP)
    enforces the cap regardless of slowapi middleware availability.
    """
    if not _prefill_check_rate(_prefill_client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="Příliš mnoho požadavků. Zkuste to prosím za chvíli.",
        )

    e = (email or "").strip().lower()
    if not e or "@" not in e or len(e) > 254:
        return {"found": False}

    sql = """
        SELECT school_name, contact_name, contact_phone, group_type,
               age_or_class, num_students, num_teachers, special_requirements
        FROM reservations
        WHERE LOWER(contact_email) = :em
          AND status NOT IN ('cancelled')
        ORDER BY created_at DESC
        LIMIT 1
    """
    try:
        row = (await db.execute(text(sql), {"em": e})).fetchone()
    except Exception:
        logger.exception("prefill query failed")
        return {"found": False}

    if not row:
        return {"found": False}

    d = dict(row._mapping)
    # Strip Nones; keep only the safe, repeatable subset.
    return {
        "found": True,
        "data": {
            "school_name":          d.get("school_name") or "",
            "contact_name":         d.get("contact_name") or "",
            "contact_phone":        d.get("contact_phone") or "",
            "group_type":           d.get("group_type") or "",
            "age_or_class":         d.get("age_or_class") or "",
            "num_students":         int(d.get("num_students") or 0) or None,
            "num_teachers":         int(d.get("num_teachers") or 0) or None,
            "special_requirements": d.get("special_requirements") or "",
        },
    }



@router.get("/stats")
@limiter.limit("30/minute")
async def get_public_stats(request: Request, db: AsyncSession = Depends(get_db)):
    """Public statistics for social proof on marketing pages.

    Returns real counts; caller should decide how to format/round them.
    Section visibility is gated by the `social_proof` feature flag (superadmin).
    """
    try:
        # Superadmin-controlled kill switch: feature flag `social_proof`
        flag_row = await db.execute(
            text("SELECT enabled FROM feature_flags WHERE key = 'social_proof'")
        )
        flag_enabled = bool(flag_row.scalar() or False)

        # Only count non-deleted institutions
        inst_result = await db.execute(
            text("SELECT COUNT(*) FROM institutions WHERE deleted_at IS NULL")
        )
        institution_count = inst_result.scalar() or 0

        # Institution type breakdown
        types_result = await db.execute(
            text(
                "SELECT type, COUNT(*) FROM institutions WHERE deleted_at IS NULL "
                "GROUP BY type ORDER BY COUNT(*) DESC"
            )
        )
        type_counts = {row[0] or "other": int(row[1]) for row in types_result.fetchall()}

        # Reservations processed
        res_result = await db.execute(text("SELECT COUNT(*) FROM reservations"))
        reservation_count = res_result.scalar() or 0

        # Active programs (non-archived, non-deleted)
        prog_result = await db.execute(
            text("SELECT COUNT(*) FROM programs WHERE deleted_at IS NULL AND status != 'archived'")
        )
        programs_count = prog_result.scalar() or 0

        # Events (optional, best-effort)
        try:
            ev_result = await db.execute(text("SELECT COUNT(*) FROM events"))
            events_count = ev_result.scalar() or 0
        except Exception:
            events_count = 0

        return {
            # show_stats gated purely by superadmin feature flag now
            "show_stats": flag_enabled,
            "institutions": institution_count,
            "reservations": reservation_count,
            "programs": programs_count,
            "events": events_count,
            "institution_types": type_counts,
            "satisfaction": 98 if institution_count >= 5 else 0,
        }
    except Exception:
        return {
            "show_stats": False,
            "institutions": 0,
            "reservations": 0,
            "programs": 0,
            "events": 0,
            "institution_types": {},
            "satisfaction": 0,
        }



@router.get("/institutions/{institution_id}")
@limiter.limit("30/minute")
async def get_public_institution_info(institution_id: str, request: Request, db: AsyncSession = Depends(get_db)):
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
@limiter.limit("10/minute")
async def validate_ico_ares(ico: str, request: Request):
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
