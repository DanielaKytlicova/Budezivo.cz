"""
Availability and calendar routes.
Uses Supabase (PostgreSQL) for database operations.
"""
import calendar
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.supabase import get_db
from database.supabase_repositories import BookingRepositorySupabase

router = APIRouter(tags=["Availability"])


@router.get("/availability/{institution_id}/{program_id}/{date}")
async def get_program_availability(
    institution_id: str,
    program_id: str,
    date: str,
    db: AsyncSession = Depends(get_db)
):
    """Get available time blocks for a program on a specific date."""
    # Default time blocks (90 minutes each)
    time_blocks = [
        {"time": "08:00-09:30", "status": "available"},
        {"time": "09:00-10:30", "status": "available"},
        {"time": "10:45-12:15", "status": "available"},
        {"time": "13:00-14:30", "status": "available"},
    ]
    
    if institution_id == "demo":
        return {"date": date, "time_blocks": time_blocks}
    
    # Check existing bookings for this date
    booking_repo = BookingRepositorySupabase(db)
    bookings = await booking_repo.find_by_program_and_date(
        institution_id, program_id, date
    )
    
    # Mark booked time blocks as unavailable
    booked_times = {b["time_block"] for b in bookings}
    for block in time_blocks:
        if block["time"] in booked_times:
            block["status"] = "booked"
    
    return {"date": date, "time_blocks": time_blocks}


@router.get("/calendar/{institution_id}/{year}/{month}")
async def get_calendar_availability(
    institution_id: str,
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db)
):
    """Get calendar month view with availability indicators."""
    # For demo, return some available dates
    if institution_id == "demo":
        num_days = calendar.monthrange(year, month)[1]
        dates = []
        for day in range(1, num_days + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            # Mark some days as available
            has_availability = day % 3 != 0
            dates.append({
                "date": date_str,
                "has_availability": has_availability,
                "available_blocks": 4 if has_availability else 0
            })
        return {"year": year, "month": month, "dates": dates}
    
    # Real implementation would check actual bookings
    return {"year": year, "month": month, "dates": []}
