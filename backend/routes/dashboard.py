"""
Dashboard and statistics routes.
Uses Supabase (PostgreSQL) for database operations.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import DashboardStats
from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import BookingRepositorySupabase

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics."""
    booking_repo = BookingRepositorySupabase(db)
    institution_id = current_user["institution_id"]
    today = datetime.now(timezone.utc).date().isoformat()
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    
    # Today's bookings
    today_bookings = await booking_repo.count_today(institution_id, today)
    
    # Upcoming groups
    upcoming_groups = await booking_repo.count_upcoming(institution_id, today)
    
    # Bookings used this month
    bookings_used = await booking_repo.count_month(institution_id, current_month)
    
    # Default to free plan limit
    bookings_limit = 50
    
    # Capacity usage
    capacity_usage = min(100.0, (bookings_used / bookings_limit) * 100) if bookings_limit > 0 else 0
    
    return {
        "today_bookings": today_bookings,
        "upcoming_groups": upcoming_groups,
        "capacity_usage": capacity_usage,
        "bookings_used": bookings_used,
        "bookings_limit": bookings_limit
    }
