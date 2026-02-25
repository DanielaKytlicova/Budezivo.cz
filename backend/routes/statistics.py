"""
Statistics routes.
"""
from fastapi import APIRouter, Depends

from core.security import get_current_user

router = APIRouter(prefix="/statistics", tags=["Statistics"])


@router.get("/bookings-over-time")
async def get_bookings_over_time(current_user: dict = Depends(get_current_user)):
    """Get bookings over time data for charts."""
    # Simplified: return mock data for last 6 months
    return {
        "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "data": [45, 52, 38, 65, 73, 58]
    }


@router.get("/popular-programs")
async def get_popular_programs(current_user: dict = Depends(get_current_user)):
    """Get popular programs data for charts."""
    # Mock data
    return {
        "labels": ["Program A", "Program B", "Program C"],
        "data": [125, 98, 67]
    }
