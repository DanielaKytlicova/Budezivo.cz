"""
Program management routes.
Uses Supabase (PostgreSQL) for database operations.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from models.schemas import ProgramCreate, Program
from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import (
    ProgramRepositorySupabase, 
    InstitutionRepositorySupabase,
    BookingRepositorySupabase,
)
from routes.audit import log_action

router = APIRouter(prefix="/programs", tags=["Programs"])
logger = logging.getLogger(__name__)
_pub_limiter = Limiter(key_func=get_remote_address)


class ArchiveRequest(BaseModel):
    reason: Optional[str] = None


@router.post("", response_model=Program)
async def create_program(
    program_data: ProgramCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new program."""
    program_repo = ProgramRepositorySupabase(db)
    program = await program_repo.create(
        program_data.model_dump(),
        current_user["institution_id"]
    )
    await log_action(
        db, institution_id=current_user["institution_id"],
        user_id=current_user["user_id"], user_email=current_user.get("email", ""),
        action="create", entity_type="program", entity_id=str(program.get("id", "")),
        details={"name": program_data.name_cs},
    )
    return program


@router.get("", response_model=List[Program])
async def get_programs(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all programs for authenticated user's institution."""
    program_repo = ProgramRepositorySupabase(db)
    return await program_repo.find_by_institution(current_user["institution_id"])


@router.get("/public/{institution_id}")
@_pub_limiter.limit("30/minute")
async def get_public_programs(
    institution_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    age: Optional[str] = Query(None, description="Comma-separated age categories: MS,ZS1,ZS2,SS"),
    duration: Optional[str] = Query(None, description="Duration filter: short (<60), medium (60-120), long (120+)"),
    tag: Optional[str] = Query(None, description="Comma-separated subject tags"),
):
    """Get public programs for booking page with optional filtering."""
    # Handle demo institution
    if institution_id == "demo":
        return _get_demo_programs()

    program_repo = ProgramRepositorySupabase(db)
    programs = await program_repo.find_public(institution_id)

    # ── Strip internal/sensitive fields before any processing ──
    PUBLIC_ALLOWED_FIELDS = {
        "id", "institution_id", "name_cs", "name_en", "description_cs", "description_en",
        "duration", "age_group", "age_categories", "target_groups", "subject_tags",
        "min_capacity", "max_capacity", "target_group", "price", "pricing_info", "status",
        "is_published", "available_days", "time_blocks", "start_date", "end_date",
        "min_days_before_booking", "max_days_before_booking",
        "preparation_time", "cleanup_time", "requires_approval",
    }
    programs = [{k: v for k, v in p.items() if k in PUBLIC_ALLOWED_FIELDS} for p in programs]

    # Mapping from short URL codes to internal age_group/target_groups values
    AGE_CODE_MAP = {
        "MS": ["ms_3_6"],
        "ZS1": ["zs1_7_12"],
        "ZS2": ["zs2_12_15"],
        "SS": ["ss_14_18", "ss_15_19"],
        "GYM": ["gym_14_18"],
        "ADULTS": ["adults"],
    }

    # Apply filters
    if age:
        age_filter = [a.strip().upper() for a in age.split(",") if a.strip()]
        if age_filter:
            # Expand codes to internal values for fallback matching
            expanded = set()
            for code in age_filter:
                expanded.update(AGE_CODE_MAP.get(code, [code.lower()]))

            programs = [
                p for p in programs
                if _matches_age(p, age_filter, expanded)
            ]

    if duration:
        dur_filter = duration.strip().lower()
        programs = [
            p for p in programs
            if _matches_duration(p.get("duration", 0), dur_filter)
        ]

    if tag:
        tag_filter = [t.strip().lower() for t in tag.split(",") if t.strip()]
        if tag_filter:
            programs = [
                p for p in programs
                if any(st.lower() in tag_filter for st in (p.get("subject_tags") or []))
            ]

    return programs


def _matches_age(program: dict, url_codes: list, expanded_internal: set) -> bool:
    """Check if program matches age filter using age_categories first, then fallback."""
    # Primary: check age_categories array (new field)
    cats = program.get("age_categories") or []
    if cats:
        return any(c.upper() in url_codes for c in cats)
    # Fallback: check target_groups array
    tgs = program.get("target_groups") or []
    if tgs:
        return any(tg in expanded_internal for tg in tgs)
    # Fallback: check legacy age_group string
    ag = program.get("age_group") or ""
    return ag in expanded_internal


def _matches_duration(dur: int, filt: str) -> bool:
    if filt == "short":
        return dur < 60
    elif filt == "medium":
        return 60 <= dur <= 120
    elif filt == "long":
        return dur > 120
    return True


def _get_demo_programs() -> list:
    return [
            {
                "id": "demo-1",
                "institution_id": "demo",
                "name_cs": "Seznam se s galerií",
                "name_en": "Gallery Introduction",
                "description_cs": "Interaktivní program, který seznámí děti se světem výtvarného umění.",
                "description_en": "Interactive program introducing children to visual arts.",
                "duration": 60,
                "age_group": "zs1_7_12",
                "min_capacity": 5,
                "max_capacity": 30,
                "target_group": "schools",
                "price": 50.0,
                "status": "active",
                "requires_approval": False,
                "is_published": True,
                "send_email_notification": False,
                "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "time_blocks": ["09:00-10:30"],
                "start_date": None,
                "end_date": None,
                "min_days_before_booking": 14,
                "max_days_before_booking": 90,
                "preparation_time": 10,
                "cleanup_time": 30,
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": "demo-2",
                "institution_id": "demo",
                "name_cs": "Po stopách historie",
                "name_en": "Following History",
                "description_cs": "Tematická prohlídka zaměřená na historii města a regionu.",
                "description_en": "Themed tour focused on city and regional history.",
                "duration": 90,
                "age_group": "zs2_12_15",
                "min_capacity": 5,
                "max_capacity": 30,
                "target_group": "schools",
                "price": 80.0,
                "status": "active",
                "requires_approval": False,
                "is_published": True,
                "send_email_notification": False,
                "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "time_blocks": ["09:00-10:30"],
                "start_date": None,
                "end_date": None,
                "min_days_before_booking": 14,
                "max_days_before_booking": 90,
                "preparation_time": 10,
                "cleanup_time": 30,
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": "demo-3",
                "institution_id": "demo",
                "name_cs": "Za uměním do neznáma",
                "name_en": "Art Adventure",
                "description_cs": "Kreativní workshop kombinující prohlídku s tvorbou.",
                "description_en": "Creative workshop combining exhibition tour with art creation.",
                "duration": 90,
                "age_group": "ss_14_18",
                "min_capacity": 5,
                "max_capacity": 30,
                "target_group": "schools",
                "price": 90.0,
                "status": "active",
                "requires_approval": False,
                "is_published": True,
                "send_email_notification": False,
                "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "time_blocks": ["09:00-10:30"],
                "start_date": None,
                "end_date": None,
                "min_days_before_booking": 14,
                "max_days_before_booking": 90,
                "preparation_time": 10,
                "cleanup_time": 30,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]


@router.get("/debug/{institution_id}")
async def debug_programs(
    institution_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Debug endpoint - requires auth, scoped to own institution only."""
    if current_user["institution_id"] != institution_id:
        raise HTTPException(status_code=403, detail="Přístup odepřen")

    from sqlalchemy import text

    result = await db.execute(
        text("SELECT id, name_cs, status, is_published, created_at FROM programs WHERE institution_id = :inst_id ORDER BY created_at DESC"),
        {"inst_id": institution_id},
    )
    rows = result.fetchall()

    return {
        "institution_id": institution_id,
        "total_programs": len(rows),
        "programs": [
            {
                "id": str(row[0]),
                "name_cs": row[1],
                "status": row[2],
                "is_published": row[3],
                "created_at": str(row[4]) if row[4] else None,
            }
            for row in rows
        ],
    }


@router.get("/archived")
async def get_archived_programs(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get archived programs."""
    program_repo = ProgramRepositorySupabase(db)
    return await program_repo.find_archived(current_user["institution_id"])


@router.get("/{program_id}", response_model=Program)
async def get_program(
    program_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get single program by ID."""
    program_repo = ProgramRepositorySupabase(db)
    program = await program_repo.find_by_id(program_id, current_user["institution_id"])
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


@router.put("/{program_id}", response_model=Program)
async def update_program(
    program_id: str,
    program_data: ProgramCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update existing program."""
    program_repo = ProgramRepositorySupabase(db)
    result = await program_repo.update(
        program_id,
        current_user["institution_id"],
        program_data.model_dump()
    )
    if result == 0:
        raise HTTPException(status_code=404, detail="Program not found")
    
    return await program_repo.find_by_id(program_id, current_user["institution_id"])


@router.post("/{program_id}/archive")
async def archive_program(
    program_id: str,
    data: ArchiveRequest = ArchiveRequest(),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Move program to archive."""
    program_repo = ProgramRepositorySupabase(db)
    program = await program_repo.find_by_id(program_id, current_user["institution_id"])
    if not program:
        raise HTTPException(status_code=404, detail="Program nenalezen")
    if program.get("status") == "archived":
        raise HTTPException(status_code=400, detail="Program je již archivován")
    
    await program_repo.update(program_id, current_user["institution_id"], {
        "status": "archived",
        "archived_at": datetime.now(timezone.utc),
        "archived_by": current_user["user_id"],
        "archive_reason": data.reason,
        "is_published": False,
    })
    await log_action(
        db, institution_id=current_user["institution_id"],
        user_id=current_user["user_id"], user_email=current_user.get("email", ""),
        action="archive", entity_type="program", entity_id=program_id,
        details={"name": program.get("name_cs", ""), "reason": data.reason},
    )
    return {"message": "Program přesunut do archivu"}


@router.post("/{program_id}/unarchive")
async def unarchive_program(
    program_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Restore program from archive."""
    program_repo = ProgramRepositorySupabase(db)
    program = await program_repo.find_by_id(program_id, current_user["institution_id"])
    if not program:
        raise HTTPException(status_code=404, detail="Program nenalezen")
    if program.get("status") != "archived":
        raise HTTPException(status_code=400, detail="Program není archivován")
    
    await program_repo.update(program_id, current_user["institution_id"], {
        "status": "active",
        "archived_at": None,
        "archived_by": None,
        "archive_reason": None,
    })
    await log_action(
        db, institution_id=current_user["institution_id"],
        user_id=current_user["user_id"], user_email=current_user.get("email", ""),
        action="unarchive", entity_type="program", entity_id=program_id,
        details={"name": program.get("name_cs", "")},
    )
    return {"message": "Program obnoven"}


@router.get("/{program_id}/archive-report")
async def get_archive_report(
    program_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate structured archive report with all program data, stats, and feedback."""
    program_repo = ProgramRepositorySupabase(db)
    booking_repo = BookingRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)
    
    program = await program_repo.find_by_id(program_id, current_user["institution_id"])
    if not program:
        raise HTTPException(status_code=404, detail="Program nenalezen")
    
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    
    # Get all bookings for this program
    all_bookings = await booking_repo.find_all_by_institution_for_export(current_user["institution_id"])
    program_bookings = [b for b in all_bookings if b.get("program_id") == program_id]
    
    # Compute stats
    total_reservations = len(program_bookings)
    confirmed = sum(1 for b in program_bookings if b.get("status") == "confirmed")
    completed = sum(1 for b in program_bookings if b.get("status") == "completed")
    cancelled = sum(1 for b in program_bookings if b.get("status") == "cancelled")
    total_students = sum(b.get("actual_students") or b.get("num_students", 0) for b in program_bookings)
    total_teachers = sum(b.get("actual_teachers") or b.get("num_teachers", 0) for b in program_bookings)
    unique_schools = len(set(b.get("school_name", "") for b in program_bookings if b.get("school_name")))
    
    # Get feedback (if exists)
    from database.models import Feedback
    from sqlalchemy import select
    try:
        fb_result = await db.execute(
            select(Feedback).where(Feedback.program_id == program_id)
        )
        from database.supabase_repositories import to_dict
        feedbacks = [to_dict(f) for f in fb_result.scalars().all()]
    except Exception:
        feedbacks = []
    
    # Get dates range
    dates = [b.get("date") for b in program_bookings if b.get("date")]
    date_range = {"from": min(dates) if dates else None, "to": max(dates) if dates else None}
    
    # Build school list with details
    schools_summary = {}
    for b in program_bookings:
        sn = b.get("school_name", "Neznámá")
        if sn not in schools_summary:
            schools_summary[sn] = {"visits": 0, "students": 0, "last_visit": None}
        schools_summary[sn]["visits"] += 1
        schools_summary[sn]["students"] += b.get("actual_students") or b.get("num_students", 0)
        bdate = b.get("date")
        if bdate and (not schools_summary[sn]["last_visit"] or bdate > schools_summary[sn]["last_visit"]):
            schools_summary[sn]["last_visit"] = bdate
    
    return {
        "report_generated_at": datetime.now(timezone.utc).isoformat(),
        "institution": {
            "name": institution.get("name") if institution else "",
        },
        "program": {
            "name": program.get("name_cs", ""),
            "description": program.get("description_cs", ""),
            "age_group": program.get("age_group", ""),
            "duration": program.get("duration"),
            "price": program.get("price"),
            "pricing_info": program.get("pricing_info"),
            "capacity": f"{program.get('min_capacity')}-{program.get('max_capacity')}",
            "status": program.get("status"),
            "start_date": program.get("start_date"),
            "end_date": program.get("end_date"),
            "archived_at": program.get("archived_at"),
            "archive_reason": program.get("archive_reason"),
        },
        "statistics": {
            "total_reservations": total_reservations,
            "confirmed": confirmed,
            "completed": completed,
            "cancelled": cancelled,
            "total_students": total_students,
            "total_teachers": total_teachers,
            "unique_schools": unique_schools,
            "date_range": date_range,
        },
        "schools": schools_summary,
        "feedback_count": len(feedbacks),
        "feedbacks": feedbacks[:50],
        "bookings": [
            {
                "date": b.get("date"),
                "time_block": b.get("time_block"),
                "school_name": b.get("school_name"),
                "status": b.get("status"),
                "num_students": b.get("actual_students") or b.get("num_students"),
                "contact_name": b.get("contact_name"),
            }
            for b in program_bookings
        ],
    }


@router.delete("/{program_id}")
async def delete_program(
    program_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete program."""
    program_repo = ProgramRepositorySupabase(db)
    result = await program_repo.delete(program_id, current_user["institution_id"])
    if result == 0:
        raise HTTPException(status_code=404, detail="Program not found")
    return {"message": "Program deleted"}


@router.get("/{program_id}/external-url")
async def get_program_external_url(
    program_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate URL for external bookings."""
    program_repo = ProgramRepositorySupabase(db)
    institution_repo = InstitutionRepositorySupabase(db)
    
    program = await program_repo.find_by_id(program_id, current_user["institution_id"])
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    
    base_url = "https://budezivo.cz"
    external_url = f"{base_url}/booking/{current_user['institution_id']}?program={program_id}"
    
    return {
        "url": external_url,
        "program_name": program.get("name_cs", ""),
        "institution_name": institution.get("name", "") if institution else "",
        "embed_code": f'<a href="{external_url}" target="_blank">Rezervovat: {program.get("name_cs", "")}</a>'
    }
