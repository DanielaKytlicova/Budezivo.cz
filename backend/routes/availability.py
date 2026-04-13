"""
Availability and calendar routes.
Uses Supabase (PostgreSQL) for database operations.
"""
import calendar
from datetime import datetime, date as date_type, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.supabase import get_db
from database.supabase_repositories import BookingRepositorySupabase, ProgramRepositorySupabase
from services.collision_service import (
    get_collision_info_for_availability,
    check_lecturer_available_for_block,
    check_any_lecturer_available_for_block,
    check_lecturer_has_any_availability_on_date,
)

router = APIRouter(tags=["Availability"])


def get_day_name(date_obj: date_type) -> str:
    """Get day name in English lowercase."""
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    return days[date_obj.weekday()]


@router.get("/availability/{institution_id}/{program_id}/{date}")
async def get_program_availability(
    institution_id: str,
    program_id: str,
    date: str,
    db: AsyncSession = Depends(get_db)
):
    """Get available time blocks for a program on a specific date."""
    # Get program to check its time blocks and available days
    program_repo = ProgramRepositorySupabase(db)
    program = await program_repo.find_by_id(program_id, institution_id)
    
    if not program:
        return {"date": date, "time_blocks": []}
    
    # Get time blocks from program settings or use defaults
    program_time_blocks = program.get("time_blocks") or ["09:00-10:30", "10:45-12:15", "13:00-14:30"]
    available_days = program.get("available_days") or ["monday", "tuesday", "wednesday", "thursday", "friday"]
    program_duration = program.get("duration") or 60
    prep_time = program.get("preparation_time") or 0
    cleanup_time = program.get("cleanup_time") or 0
    
    # Check if the date's day of week is in available days
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        day_name = get_day_name(date_obj)
        if day_name not in available_days:
            return {"date": date, "time_blocks": []}
    except ValueError:
        return {"date": date, "time_blocks": []}
    
    def time_to_min(t):
        h, m = map(int, t.split(':'))
        return h * 60 + m
    
    def min_to_time(m):
        return f"{m // 60:02d}:{m % 60:02d}"
    
    # Expand time windows into individual slots based on program duration
    expanded_blocks = []
    for tb in program_time_blocks:
        if '-' in tb:
            parts = tb.split('-')
            window_start = time_to_min(parts[0].strip())
            window_end = time_to_min(parts[1].strip())
            window_span = window_end - window_start
            
            # If the window is significantly larger than the duration, expand into individual slots
            if window_span > program_duration + 15:
                slot_start = window_start
                step = 30  # 30-minute intervals
                while slot_start + program_duration <= window_end:
                    slot_end = slot_start + program_duration
                    slot_str = f"{min_to_time(slot_start)}-{min_to_time(slot_end)}"
                    expanded_blocks.append(slot_str)
                    slot_start += step
            else:
                expanded_blocks.append(tb)
        else:
            # Single time like "09:00" — convert to full slot
            start = time_to_min(tb.strip())
            end = start + program_duration
            expanded_blocks.append(f"{min_to_time(start)}-{min_to_time(end)}")
    
    # Create time blocks from expanded list
    time_blocks = [{"time": tb, "status": "available"} for tb in expanded_blocks]
    
    if institution_id == "demo":
        return {"date": date, "time_blocks": time_blocks}
    
    # Check existing bookings for this date
    booking_repo = BookingRepositorySupabase(db)
    bookings = await booking_repo.find_by_program_and_date(
        institution_id, program_id, date
    )
    
    # Parse booked time ranges for overlap detection (handles both old window and new slot formats)
    booked_ranges = []
    for b in bookings:
        if b.get("status") == "cancelled":
            continue
        tb = b.get("time_block", "")
        if '-' in tb:
            parts = tb.split('-')
            booked_ranges.append((time_to_min(parts[0].strip()), time_to_min(parts[1].strip())))
        elif tb:
            start = time_to_min(tb.strip())
            booked_ranges.append((start, start + program_duration))
    
    def slot_overlaps_booking(slot_str):
        """Check if a time slot overlaps with any existing booking."""
        if '-' in slot_str:
            parts = slot_str.split('-')
            s_start = time_to_min(parts[0].strip())
            s_end = time_to_min(parts[1].strip())
        else:
            s_start = time_to_min(slot_str.strip())
            s_end = s_start + program_duration
        for b_start, b_end in booked_ranges:
            if s_start < b_end and s_end > b_start:
                return True
        return False
    
    # Get program's assigned lecturer and collision settings
    assigned_lecturer_id = program.get("assigned_lecturer_id")
    collision_resources = program.get("collision_resources") or []
    has_lecturer_collision = "lecturer" in collision_resources
    
    for block in time_blocks:
        if slot_overlaps_booking(block["time"]):
            block["status"] = "booked"
        elif block["status"] == "available":
            # Check cross-program collisions
            is_blocked = await get_collision_info_for_availability(
                db, institution_id, program_id, date, block["time"]
            )
            if is_blocked:
                block["status"] = "booked"
            # Check lecturer availability when lecturer collision is enabled
            elif has_lecturer_collision:
                if assigned_lecturer_id:
                    # Check assigned lecturer specifically
                    lecturer_available = await check_lecturer_available_for_block(
                        db, str(assigned_lecturer_id), institution_id,
                        date, block["time"], program_duration
                    )
                    if not lecturer_available:
                        block["status"] = "unavailable"
                else:
                    # No assigned lecturer — check if ANY team lecturer is available
                    any_available = await check_any_lecturer_available_for_block(
                        db, institution_id, date, block["time"], program_duration
                    )
                    if not any_available:
                        block["status"] = "unavailable"
    
    return {"date": date, "time_blocks": time_blocks}


@router.get("/calendar/{institution_id}/{year}/{month}")
async def get_calendar_availability(
    institution_id: str,
    year: int,
    month: int,
    program_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get calendar month view with availability indicators.
    Shows which days have available time slots based on program settings.
    """
    num_days = calendar.monthrange(year, month)[1]
    dates = []
    today = date_type.today()
    
    # For demo institution, return mock data
    if institution_id == "demo":
        for day in range(1, num_days + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            date_obj = date_type(year, month, day)
            is_past = date_obj < today
            is_weekend = date_obj.weekday() >= 5
            has_availability = not is_past and not is_weekend and day % 3 != 0
            dates.append({
                "date": date_str,
                "has_availability": has_availability,
                "available_blocks": 4 if has_availability else 0
            })
        return {"year": year, "month": month, "dates": dates}
    
    # Get programs for this institution to determine available days and time blocks
    program_repo = ProgramRepositorySupabase(db)
    
    # Get all active programs or specific program
    if program_id:
        program = await program_repo.find_by_id(program_id, institution_id)
        programs = [program] if program else []
    else:
        programs = await program_repo.find_by_institution(institution_id)
        programs = [p for p in programs if p.get("status") == "active" and p.get("is_published")]
    
    if not programs:
        # No programs - return empty calendar
        for day in range(1, num_days + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            dates.append({
                "date": date_str,
                "has_availability": False,
                "available_blocks": 0
            })
        return {"year": year, "month": month, "dates": dates}
    
    # Aggregate available days from all programs (or use specific program)
    all_available_days = set()
    all_time_blocks = []
    
    for prog in programs:
        available_days = prog.get("available_days") or ["monday", "tuesday", "wednesday", "thursday", "friday"]
        time_blocks = prog.get("time_blocks") or ["09:00-10:30", "10:45-12:15", "13:00-14:30"]
        all_available_days.update(available_days)
        all_time_blocks.extend(time_blocks)
    
    # Remove duplicates from time blocks
    unique_time_blocks = list(set(all_time_blocks))
    total_blocks = len(unique_time_blocks)
    
    # Get min/max days before booking from first program
    min_days_before = programs[0].get("min_days_before_booking", 1) if programs else 1
    max_days_before = programs[0].get("max_days_before_booking", 90) if programs else 90
    
    # Check validity dates
    start_date = None
    end_date = None
    if programs:
        prog = programs[0]
        if prog.get("start_date"):
            try:
                start_date = datetime.fromisoformat(str(prog["start_date"]).replace('Z', '+00:00')).date()
            except (ValueError, TypeError):
                pass
        if prog.get("end_date"):
            try:
                end_date = datetime.fromisoformat(str(prog["end_date"]).replace('Z', '+00:00')).date()
            except (ValueError, TypeError):
                pass
    
    # Check if program has lecturer collision settings
    has_lecturer_collision = False
    prog_assigned_lecturer = None
    scheduled_lecturer_ids = []
    if programs:
        prog = programs[0]
        collision_resources = prog.get("collision_resources") or []
        has_lecturer_collision = "lecturer" in collision_resources
        if prog.get("assigned_lecturer_id"):
            prog_assigned_lecturer = str(prog["assigned_lecturer_id"])
    
    # Pre-load scheduled lecturers for monthly check (only when needed)
    if has_lecturer_collision and program_id and not prog_assigned_lecturer:
        from services.collision_service import get_institution_lecturers
        from database.models import LecturerAvailability
        from sqlalchemy import select as sa_select, and_ as sa_and
        import uuid as _uuid
        lecturer_ids = await get_institution_lecturers(db, institution_id)
        for lid in lecturer_ids:
            result = await db.execute(
                sa_select(LecturerAvailability.id).where(sa_and(
                    LecturerAvailability.lecturer_id == _uuid.UUID(lid),
                    LecturerAvailability.institution_id == _uuid.UUID(institution_id)
                )).limit(1)
            )
            if result.scalar_one_or_none() is not None:
                scheduled_lecturer_ids.append(lid)
    
    # Build calendar
    for day in range(1, num_days + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        date_obj = date_type(year, month, day)
        day_name = get_day_name(date_obj)
        
        # Check various availability conditions
        is_past = date_obj < today
        is_too_soon = (date_obj - today).days < min_days_before
        is_too_far = (date_obj - today).days > max_days_before
        is_available_day = day_name in all_available_days
        
        # Check validity period
        is_before_start = start_date and date_obj < start_date
        is_after_end = end_date and date_obj > end_date
        
        # Determine availability
        has_availability = (
            not is_past and 
            not is_too_soon and 
            not is_too_far and 
            is_available_day and
            not is_before_start and
            not is_after_end
        )
        
        # Check lecturer availability for this day (when specific program selected)
        if has_availability and has_lecturer_collision and program_id:
            if prog_assigned_lecturer:
                lect_avail = await check_lecturer_has_any_availability_on_date(
                    db, prog_assigned_lecturer, institution_id, date_str
                )
                if not lect_avail:
                    has_availability = False
            else:
                # No assigned lecturer — check only SCHEDULED team lecturers
                if scheduled_lecturer_ids:
                    any_lect_avail = False
                    for lid in scheduled_lecturer_ids:
                        if await check_lecturer_has_any_availability_on_date(db, lid, institution_id, date_str):
                            any_lect_avail = True
                            break
                    if not any_lect_avail:
                        has_availability = False
        
        available_blocks = total_blocks if has_availability else 0
        
        dates.append({
            "date": date_str,
            "has_availability": has_availability,
            "available_blocks": available_blocks
        })
    
    return {"year": year, "month": month, "dates": dates}
