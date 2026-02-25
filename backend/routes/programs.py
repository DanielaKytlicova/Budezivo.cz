"""
Program management routes.
Uses Supabase (PostgreSQL) for database operations.
"""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import ProgramCreate, Program
from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import ProgramRepositorySupabase, InstitutionRepositorySupabase

router = APIRouter(prefix="/programs", tags=["Programs"])


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
    return program


@router.get("", response_model=List[Program])
async def get_programs(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all programs for authenticated user's institution."""
    program_repo = ProgramRepositorySupabase(db)
    return await program_repo.find_by_institution(current_user["institution_id"])


@router.get("/public/{institution_id}", response_model=List[Program])
async def get_public_programs(institution_id: str, db: AsyncSession = Depends(get_db)):
    """Get public programs for booking page."""
    # Handle demo institution
    if institution_id == "demo":
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
    
    program_repo = ProgramRepositorySupabase(db)
    return await program_repo.find_public(institution_id)


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
