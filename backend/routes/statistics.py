"""
Statistics routes with real data from database.
Provides data for charts, reports, and CSV export.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract, case
from pydantic import BaseModel
import csv
import io

from core.security import get_current_user
from database.supabase import get_db
from database.models import Reservation, Program, Institution
from database.supabase_repositories import InstitutionRepositorySupabase

router = APIRouter(prefix="/statistics", tags=["Statistics"])
logger = logging.getLogger(__name__)


# ============ Pydantic Models ============

class MonthlyStats(BaseModel):
    month: str
    year: int
    bookings: int
    students: int
    teachers: int


class ProgramStats(BaseModel):
    program_id: str
    program_name: str
    bookings_count: int
    total_students: int
    total_teachers: int


class StatusStats(BaseModel):
    status: str
    count: int


class AgeGroupStats(BaseModel):
    age_group: str
    count: int


class OverviewStats(BaseModel):
    total_bookings: int
    total_students: int
    total_teachers: int
    total_visitors: int
    confirmed_bookings: int
    pending_bookings: int
    cancelled_bookings: int
    completed_bookings: int
    avg_group_size: float


class StatisticsResponse(BaseModel):
    overview: OverviewStats
    monthly: List[MonthlyStats]
    by_program: List[ProgramStats]
    by_status: List[StatusStats]
    by_age_group: List[AgeGroupStats]
    period: dict


# ============ Helper Functions ============

def get_school_year_dates(year: int = None):
    """Get start and end dates for school year (September to June)."""
    now = datetime.now(timezone.utc)
    if year is None:
        # Current school year
        if now.month >= 9:
            start_year = now.year
        else:
            start_year = now.year - 1
    else:
        start_year = year
    
    start_date = datetime(start_year, 9, 1, tzinfo=timezone.utc)
    end_date = datetime(start_year + 1, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
    return start_date, end_date


def get_semester_dates(year: int = None, semester: int = 1):
    """Get dates for semester (1 = Sep-Jan, 2 = Feb-Jun)."""
    now = datetime.now(timezone.utc)
    if year is None:
        if now.month >= 9:
            start_year = now.year
        else:
            start_year = now.year - 1
    else:
        start_year = year
    
    if semester == 1:
        start_date = datetime(start_year, 9, 1, tzinfo=timezone.utc)
        end_date = datetime(start_year + 1, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
    else:
        start_date = datetime(start_year + 1, 2, 1, tzinfo=timezone.utc)
        end_date = datetime(start_year + 1, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
    
    return start_date, end_date


def get_calendar_year_dates(year: int = None):
    """Get start and end dates for calendar year."""
    if year is None:
        year = datetime.now(timezone.utc).year
    start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    return start_date, end_date


def get_month_dates(year: int = None, month: int = None):
    """Get start and end dates for a specific month."""
    now = datetime.now(timezone.utc)
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    else:
        end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    
    return start_date, end_date


CZECH_MONTHS = {
    1: "Leden", 2: "Únor", 3: "Březen", 4: "Duben",
    5: "Květen", 6: "Červen", 7: "Červenec", 8: "Srpen",
    9: "Září", 10: "Říjen", 11: "Listopad", 12: "Prosinec"
}

AGE_GROUP_LABELS = {
    "ms_3_6": "MŠ (3-6 let)",
    "zs1_7_12": "ZŠ 1. stupeň (7-12)",
    "zs2_12_15": "ZŠ 2. stupeň (12-15)",
    "ss_14_18": "SŠ (14-18)",
    "gym_14_18": "Gymnázium (14-18)",
    "adults": "Dospělí",
    "all": "Všechny věkové skupiny",
}

STATUS_LABELS = {
    "pending": "Čekající",
    "confirmed": "Potvrzené",
    "cancelled": "Zrušené",
    "completed": "Dokončené",
    "no_show": "Nedostavil se",
}


# ============ Main Statistics Endpoint ============

@router.get("", response_model=StatisticsResponse)
async def get_statistics(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    period_type: str = Query("month", description="month, school_year, semester, calendar_year, custom"),
    year: Optional[int] = Query(None, description="Year for the period"),
    month: Optional[int] = Query(None, description="Month (1-12) for month period"),
    semester: Optional[int] = Query(None, description="Semester (1 or 2) for semester period"),
    start_date: Optional[str] = Query(None, description="Start date for custom period (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date for custom period (YYYY-MM-DD)"),
):
    """
    Get comprehensive statistics for the institution.
    
    Period types:
    - month: Current month (default) or specified month/year
    - school_year: September to June (academic year)
    - semester: First (Sep-Jan) or second (Feb-Jun) semester
    - calendar_year: January to December
    - custom: Custom date range
    """
    import uuid
    institution_id = uuid.UUID(current_user["institution_id"])
    
    # Determine date range based on period type
    if period_type == "month":
        date_start, date_end = get_month_dates(year, month)
        period_label = f"{CZECH_MONTHS[date_start.month]} {date_start.year}"
    elif period_type == "school_year":
        date_start, date_end = get_school_year_dates(year)
        period_label = f"Školní rok {date_start.year}/{date_end.year}"
    elif period_type == "semester":
        date_start, date_end = get_semester_dates(year, semester or 1)
        sem_label = "1. pololetí" if (semester or 1) == 1 else "2. pololetí"
        period_label = f"{sem_label} {date_start.year}/{date_end.year}"
    elif period_type == "calendar_year":
        date_start, date_end = get_calendar_year_dates(year)
        period_label = f"Rok {date_start.year}"
    elif period_type == "custom" and start_date and end_date:
        date_start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        date_end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        period_label = f"{start_date} - {end_date}"
    else:
        # Default to current month
        date_start, date_end = get_month_dates()
        period_label = f"{CZECH_MONTHS[date_start.month]} {date_start.year}"
    
    # Convert dates to string format for comparison with date column
    start_str = date_start.strftime("%Y-%m-%d")
    end_str = date_end.strftime("%Y-%m-%d")
    
    # Base query filter
    base_filter = and_(
        Reservation.institution_id == institution_id,
        Reservation.date >= start_str,
        Reservation.date <= end_str,
        Reservation.deleted_at.is_(None)
    )
    
    # ============ Overview Stats ============
    overview_result = await db.execute(
        select(
            func.count(Reservation.id).label("total"),
            func.coalesce(func.sum(Reservation.num_students), 0).label("students"),
            func.coalesce(func.sum(Reservation.num_teachers), 0).label("teachers"),
            func.count(case((Reservation.status == "confirmed", 1))).label("confirmed"),
            func.count(case((Reservation.status == "pending", 1))).label("pending"),
            func.count(case((Reservation.status == "cancelled", 1))).label("cancelled"),
            func.count(case((Reservation.status == "completed", 1))).label("completed"),
        ).where(base_filter)
    )
    overview_row = overview_result.fetchone()
    
    total_bookings = overview_row.total or 0
    total_students = int(overview_row.students or 0)
    total_teachers = int(overview_row.teachers or 0)
    
    overview = OverviewStats(
        total_bookings=total_bookings,
        total_students=total_students,
        total_teachers=total_teachers,
        total_visitors=total_students + total_teachers,
        confirmed_bookings=overview_row.confirmed or 0,
        pending_bookings=overview_row.pending or 0,
        cancelled_bookings=overview_row.cancelled or 0,
        completed_bookings=overview_row.completed or 0,
        avg_group_size=round(total_students / total_bookings, 1) if total_bookings > 0 else 0,
    )
    
    # ============ Monthly Stats ============
    # Get data for each month in the period
    monthly_data = []
    current = date_start.replace(day=1)
    while current <= date_end:
        month_start = current.strftime("%Y-%m-%d")
        if current.month == 12:
            next_month = current.replace(year=current.year + 1, month=1)
        else:
            next_month = current.replace(month=current.month + 1)
        month_end = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")
        
        month_result = await db.execute(
            select(
                func.count(Reservation.id).label("bookings"),
                func.coalesce(func.sum(Reservation.num_students), 0).label("students"),
                func.coalesce(func.sum(Reservation.num_teachers), 0).label("teachers"),
            ).where(and_(
                Reservation.institution_id == institution_id,
                Reservation.date >= month_start,
                Reservation.date <= month_end,
                Reservation.deleted_at.is_(None),
                Reservation.status != "cancelled"
            ))
        )
        month_row = month_result.fetchone()
        
        monthly_data.append(MonthlyStats(
            month=CZECH_MONTHS[current.month],
            year=current.year,
            bookings=month_row.bookings or 0,
            students=int(month_row.students or 0),
            teachers=int(month_row.teachers or 0),
        ))
        
        current = next_month
    
    # ============ By Program Stats ============
    program_result = await db.execute(
        select(
            Reservation.program_id,
            Program.name_cs,
            func.count(Reservation.id).label("bookings"),
            func.coalesce(func.sum(Reservation.num_students), 0).label("students"),
            func.coalesce(func.sum(Reservation.num_teachers), 0).label("teachers"),
        )
        .join(Program, Reservation.program_id == Program.id)
        .where(and_(base_filter, Reservation.status != "cancelled"))
        .group_by(Reservation.program_id, Program.name_cs)
        .order_by(func.count(Reservation.id).desc())
        .limit(10)
    )
    
    by_program = [
        ProgramStats(
            program_id=str(row.program_id),
            program_name=row.name_cs,
            bookings_count=row.bookings,
            total_students=int(row.students),
            total_teachers=int(row.teachers),
        )
        for row in program_result.fetchall()
    ]
    
    # ============ By Status Stats ============
    status_result = await db.execute(
        select(
            Reservation.status,
            func.count(Reservation.id).label("count"),
        )
        .where(and_(
            Reservation.institution_id == institution_id,
            Reservation.date >= start_str,
            Reservation.date <= end_str,
            Reservation.deleted_at.is_(None)
        ))
        .group_by(Reservation.status)
    )
    
    by_status = [
        StatusStats(
            status=STATUS_LABELS.get(row.status, row.status),
            count=row.count,
        )
        for row in status_result.fetchall()
    ]
    
    # ============ By Age Group Stats ============
    age_result = await db.execute(
        select(
            Reservation.group_type,
            func.count(Reservation.id).label("count"),
        )
        .where(and_(base_filter, Reservation.status != "cancelled"))
        .group_by(Reservation.group_type)
        .order_by(func.count(Reservation.id).desc())
    )
    
    by_age_group = [
        AgeGroupStats(
            age_group=AGE_GROUP_LABELS.get(row.group_type, row.group_type),
            count=row.count,
        )
        for row in age_result.fetchall()
    ]
    
    return StatisticsResponse(
        overview=overview,
        monthly=monthly_data,
        by_program=by_program,
        by_status=by_status,
        by_age_group=by_age_group,
        period={
            "type": period_type,
            "label": period_label,
            "start": start_str,
            "end": end_str,
        }
    )


# ============ CSV Export ============

@router.get("/export/csv")
async def export_statistics_csv(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    period_type: str = Query("month"),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    semester: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    export_type: str = Query("reservations", description="reservations, summary, programs"),
):
    """
    Export statistics to CSV.
    
    Requires PRO plan or admin exception.
    """
    import uuid
    institution_id = uuid.UUID(current_user["institution_id"])
    
    # Check if user has PRO access
    institution_repo = InstitutionRepositorySupabase(db)
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    
    if not institution:
        raise HTTPException(status_code=404, detail="Instituce nenalezena")
    
    is_pro = institution.get("plan") in ["standard", "premium"]
    csv_export_exception = institution.get("pro_settings", {}).get("csv_export_exception", False)
    
    if not is_pro and not csv_export_exception:
        raise HTTPException(
            status_code=403, 
            detail="Export CSV je dostupný pouze pro PRO verzi. Kontaktujte podporu pro výjimku."
        )
    
    # Determine date range
    if period_type == "month":
        date_start, date_end = get_month_dates(year, month)
    elif period_type == "school_year":
        date_start, date_end = get_school_year_dates(year)
    elif period_type == "semester":
        date_start, date_end = get_semester_dates(year, semester or 1)
    elif period_type == "calendar_year":
        date_start, date_end = get_calendar_year_dates(year)
    elif period_type == "custom" and start_date and end_date:
        date_start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        date_end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    else:
        date_start, date_end = get_month_dates()
    
    start_str = date_start.strftime("%Y-%m-%d")
    end_str = date_end.strftime("%Y-%m-%d")
    
    # Create CSV buffer
    output = io.StringIO()
    
    if export_type == "reservations":
        # Export all reservations
        result = await db.execute(
            select(Reservation, Program.name_cs)
            .join(Program, Reservation.program_id == Program.id)
            .where(and_(
                Reservation.institution_id == institution_id,
                Reservation.date >= start_str,
                Reservation.date <= end_str,
                Reservation.deleted_at.is_(None)
            ))
            .order_by(Reservation.date)
        )
        
        writer = csv.writer(output, delimiter=';')
        writer.writerow([
            "Datum", "Čas", "Program", "Škola", "Kontakt", "Email", "Telefon",
            "Počet žáků", "Počet pedagogů", "Věková skupina", "Status", "Poznámky"
        ])
        
        for row in result.fetchall():
            res = row[0]
            program_name = row[1]
            writer.writerow([
                res.date,
                res.time_block,
                program_name,
                res.school_name,
                res.contact_name,
                res.contact_email,
                res.contact_phone,
                res.num_students,
                res.num_teachers,
                AGE_GROUP_LABELS.get(res.group_type, res.group_type),
                STATUS_LABELS.get(res.status, res.status),
                res.notes or "",
            ])
        
        filename = f"rezervace_{start_str}_{end_str}.csv"
        
    elif export_type == "summary":
        # Export monthly summary
        writer = csv.writer(output, delimiter=';')
        writer.writerow(["Měsíc", "Rok", "Počet rezervací", "Počet žáků", "Počet pedagogů", "Celkem návštěvníků"])
        
        current = date_start.replace(day=1)
        while current <= date_end:
            month_start = current.strftime("%Y-%m-%d")
            if current.month == 12:
                next_month = current.replace(year=current.year + 1, month=1)
            else:
                next_month = current.replace(month=current.month + 1)
            month_end = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")
            
            month_result = await db.execute(
                select(
                    func.count(Reservation.id).label("bookings"),
                    func.coalesce(func.sum(Reservation.num_students), 0).label("students"),
                    func.coalesce(func.sum(Reservation.num_teachers), 0).label("teachers"),
                ).where(and_(
                    Reservation.institution_id == institution_id,
                    Reservation.date >= month_start,
                    Reservation.date <= month_end,
                    Reservation.deleted_at.is_(None),
                    Reservation.status != "cancelled"
                ))
            )
            month_row = month_result.fetchone()
            
            students = int(month_row.students or 0)
            teachers = int(month_row.teachers or 0)
            
            writer.writerow([
                CZECH_MONTHS[current.month],
                current.year,
                month_row.bookings or 0,
                students,
                teachers,
                students + teachers,
            ])
            
            current = next_month
        
        filename = f"souhrn_{start_str}_{end_str}.csv"
        
    elif export_type == "programs":
        # Export by program
        writer = csv.writer(output, delimiter=';')
        writer.writerow(["Program", "Počet rezervací", "Počet žáků", "Počet pedagogů", "Celkem návštěvníků", "Průměrná velikost skupiny"])
        
        program_result = await db.execute(
            select(
                Program.name_cs,
                func.count(Reservation.id).label("bookings"),
                func.coalesce(func.sum(Reservation.num_students), 0).label("students"),
                func.coalesce(func.sum(Reservation.num_teachers), 0).label("teachers"),
            )
            .join(Program, Reservation.program_id == Program.id)
            .where(and_(
                Reservation.institution_id == institution_id,
                Reservation.date >= start_str,
                Reservation.date <= end_str,
                Reservation.deleted_at.is_(None),
                Reservation.status != "cancelled"
            ))
            .group_by(Program.name_cs)
            .order_by(func.count(Reservation.id).desc())
        )
        
        for row in program_result.fetchall():
            students = int(row.students or 0)
            teachers = int(row.teachers or 0)
            bookings = row.bookings or 0
            avg_size = round(students / bookings, 1) if bookings > 0 else 0
            
            writer.writerow([
                row.name_cs,
                bookings,
                students,
                teachers,
                students + teachers,
                avg_size,
            ])
        
        filename = f"programy_{start_str}_{end_str}.csv"
    else:
        raise HTTPException(status_code=400, detail="Neplatný typ exportu")
    
    # Return CSV file
    output.seek(0)
    
    # Add BOM for Excel UTF-8 compatibility
    bom = '\ufeff'
    content = bom + output.getvalue()
    
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# ============ Legacy endpoints for backwards compatibility ============

@router.get("/bookings-over-time")
async def get_bookings_over_time(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get bookings over time data for charts (last 6 months)."""
    import uuid
    institution_id = uuid.UUID(current_user["institution_id"])
    
    now = datetime.now(timezone.utc)
    labels = []
    data = []
    
    for i in range(5, -1, -1):
        month_date = now - timedelta(days=i * 30)
        month_start = month_date.replace(day=1).strftime("%Y-%m-%d")
        if month_date.month == 12:
            next_month = month_date.replace(year=month_date.year + 1, month=1)
        else:
            next_month = month_date.replace(month=month_date.month + 1)
        month_end = (next_month.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
        
        result = await db.execute(
            select(func.count(Reservation.id))
            .where(and_(
                Reservation.institution_id == institution_id,
                Reservation.date >= month_start,
                Reservation.date <= month_end,
                Reservation.deleted_at.is_(None),
                Reservation.status != "cancelled"
            ))
        )
        count = result.scalar() or 0
        
        labels.append(CZECH_MONTHS[month_date.month][:3])
        data.append(count)
    
    return {"labels": labels, "data": data}


@router.get("/popular-programs")
async def get_popular_programs(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get popular programs data for charts."""
    import uuid
    institution_id = uuid.UUID(current_user["institution_id"])
    
    # Last 6 months
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=180)).strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")
    
    result = await db.execute(
        select(
            Program.name_cs,
            func.count(Reservation.id).label("count"),
        )
        .join(Program, Reservation.program_id == Program.id)
        .where(and_(
            Reservation.institution_id == institution_id,
            Reservation.date >= start_date,
            Reservation.date <= end_date,
            Reservation.deleted_at.is_(None),
            Reservation.status != "cancelled"
        ))
        .group_by(Program.name_cs)
        .order_by(func.count(Reservation.id).desc())
        .limit(5)
    )
    
    rows = result.fetchall()
    labels = [row.name_cs for row in rows]
    data = [row.count for row in rows]
    
    return {"labels": labels, "data": data}
