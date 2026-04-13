"""
Feedback API routes for the Teacher Feedback System.

Handles:
- Admin: CRUD for feedback questions
- Admin: View/filter feedback submissions
- Admin: Export feedback to CSV/Excel
- Public: Submit feedback form
"""
import uuid
import secrets
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
import csv
import io

from database.supabase import get_db
from database.models import (
    Feedback, FeedbackQuestion, Reservation, Program, Institution, User
)
from core.security import get_current_user

router = APIRouter(prefix="/feedback", tags=["Feedback"])


# ============ Pydantic Models ============

class FeedbackQuestionCreate(BaseModel):
    question_text: str
    question_type: str = "rating"  # rating, text, yesno
    is_required: bool = True
    display_order: int = 0


class FeedbackQuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    is_required: Optional[bool] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class FeedbackQuestionResponse(BaseModel):
    id: str
    question_text: str
    question_type: str
    is_required: bool
    display_order: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackSubmission(BaseModel):
    """Public form submission model."""
    answers: dict = Field(default_factory=dict)  # {question_id: answer_value}
    overall_rating: Optional[int] = Field(None, ge=1, le=5)
    would_recommend: Optional[bool] = None
    additional_comments: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    reservation_id: str
    program_id: Optional[str]
    program_name: Optional[str] = None
    school_name: Optional[str] = None
    reservation_date: Optional[str] = None
    answers: dict
    overall_rating: Optional[int]
    would_recommend: Optional[bool]
    additional_comments: Optional[str]
    status: str
    submitted_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackStatistics(BaseModel):
    total_feedbacks: int
    average_rating: Optional[float]
    recommendation_rate: Optional[float]
    by_rating: dict  # {1: count, 2: count, ...}
    by_program: List[dict]  # [{program_name, count, avg_rating}]


# ============ Helper Functions ============

def generate_feedback_token() -> str:
    """Generate a secure random token for public feedback access."""
    return secrets.token_urlsafe(32)


def check_admin_or_edukator(user: dict) -> bool:
    """Check if user has admin or edukator role."""
    return user.get('role') in ['admin', 'spravce', 'edukator', 'staff']


def check_admin_only(user: dict) -> bool:
    """Check if user has admin role."""
    return user.get('role') in ['admin', 'spravce']


# ============ Admin: Feedback Questions CRUD ============

@router.get("/questions", response_model=List[FeedbackQuestionResponse])
async def get_feedback_questions(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all feedback questions for the institution."""
    query = select(FeedbackQuestion).where(
        FeedbackQuestion.institution_id == current_user['institution_id']
    )
    
    if not include_inactive:
        query = query.where(FeedbackQuestion.is_active == True)
    
    query = query.order_by(FeedbackQuestion.display_order)
    
    result = await db.execute(query)
    questions = result.scalars().all()
    
    return [
        FeedbackQuestionResponse(
            id=str(q.id),
            question_text=q.question_text,
            question_type=q.question_type,
            is_required=q.is_required,
            display_order=q.display_order,
            is_active=q.is_active,
            created_at=q.created_at
        )
        for q in questions
    ]


@router.post("/questions", response_model=FeedbackQuestionResponse, status_code=201)
async def create_feedback_question(
    data: FeedbackQuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new feedback question (Admin only)."""
    if not check_admin_only(current_user):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění vytvářet otázky")
    
    question = FeedbackQuestion(
        institution_id=current_user['institution_id'],
        question_text=data.question_text,
        question_type=data.question_type,
        is_required=data.is_required,
        display_order=data.display_order,
        created_by=current_user['user_id']
    )
    
    db.add(question)
    await db.commit()
    await db.refresh(question)
    
    return FeedbackQuestionResponse(
        id=str(question.id),
        question_text=question.question_text,
        question_type=question.question_type,
        is_required=question.is_required,
        display_order=question.display_order,
        is_active=question.is_active,
        created_at=question.created_at
    )


@router.put("/questions/{question_id}", response_model=FeedbackQuestionResponse)
async def update_feedback_question(
    question_id: str,
    data: FeedbackQuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a feedback question (Admin only)."""
    if not check_admin_only(current_user):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění upravovat otázky")
    
    result = await db.execute(
        select(FeedbackQuestion).where(
            FeedbackQuestion.id == question_id,
            FeedbackQuestion.institution_id == current_user['institution_id']
        )
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="Otázka nenalezena")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(question, key, value)
    
    await db.commit()
    await db.refresh(question)
    
    return FeedbackQuestionResponse(
        id=str(question.id),
        question_text=question.question_text,
        question_type=question.question_type,
        is_required=question.is_required,
        display_order=question.display_order,
        is_active=question.is_active,
        created_at=question.created_at
    )


@router.delete("/questions/{question_id}")
async def delete_feedback_question(
    question_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete (deactivate) a feedback question (Admin only)."""
    if not check_admin_only(current_user):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění mazat otázky")
    
    result = await db.execute(
        select(FeedbackQuestion).where(
            FeedbackQuestion.id == question_id,
            FeedbackQuestion.institution_id == current_user['institution_id']
        )
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="Otázka nenalezena")
    
    # Soft delete - just deactivate
    question.is_active = False
    await db.commit()
    
    return {"message": "Otázka byla deaktivována"}


# ============ Admin: View Feedback Submissions ============

@router.get("/submissions", response_model=List[FeedbackResponse])
async def get_feedback_submissions(
    status_filter: Optional[str] = None,
    program_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get feedback submissions with filters (Admin/Edukator)."""
    if not check_admin_or_edukator(current_user):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění zobrazit zpětné vazby")
    
    query = (
        select(Feedback, Reservation, Program)
        .join(Reservation, Feedback.reservation_id == Reservation.id)
        .outerjoin(Program, Feedback.program_id == Program.id)
        .where(Feedback.institution_id == current_user['institution_id'])
    )
    
    # Apply filters
    if status_filter:
        query = query.where(Feedback.status == status_filter)
    
    if program_id:
        query = query.where(Feedback.program_id == program_id)
    
    if date_from:
        query = query.where(Reservation.date >= date_from)
    
    if date_to:
        query = query.where(Reservation.date <= date_to)
    
    if min_rating:
        query = query.where(Feedback.overall_rating >= min_rating)
    
    if max_rating:
        query = query.where(Feedback.overall_rating <= max_rating)
    
    query = query.order_by(Feedback.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    rows = result.all()
    
    feedbacks = []
    for feedback, reservation, program in rows:
        feedbacks.append(FeedbackResponse(
            id=str(feedback.id),
            reservation_id=str(feedback.reservation_id),
            program_id=str(feedback.program_id) if feedback.program_id else None,
            program_name=program.name_cs if program else None,
            school_name=reservation.school_name,
            reservation_date=reservation.date,
            answers=feedback.answers or {},
            overall_rating=feedback.overall_rating,
            would_recommend=feedback.would_recommend,
            additional_comments=feedback.additional_comments,
            status=feedback.status,
            submitted_at=feedback.submitted_at,
            created_at=feedback.created_at
        ))
    
    return feedbacks


@router.get("/submissions/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_detail(
    feedback_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get single feedback detail."""
    if not check_admin_or_edukator(current_user):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění")
    
    result = await db.execute(
        select(Feedback, Reservation, Program)
        .join(Reservation, Feedback.reservation_id == Reservation.id)
        .outerjoin(Program, Feedback.program_id == Program.id)
        .where(
            Feedback.id == feedback_id,
            Feedback.institution_id == current_user['institution_id']
        )
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(status_code=404, detail="Zpětná vazba nenalezena")
    
    feedback, reservation, program = row
    
    return FeedbackResponse(
        id=str(feedback.id),
        reservation_id=str(feedback.reservation_id),
        program_id=str(feedback.program_id) if feedback.program_id else None,
        program_name=program.name_cs if program else None,
        school_name=reservation.school_name,
        reservation_date=reservation.date,
        answers=feedback.answers or {},
        overall_rating=feedback.overall_rating,
        would_recommend=feedback.would_recommend,
        additional_comments=feedback.additional_comments,
        status=feedback.status,
        submitted_at=feedback.submitted_at,
        created_at=feedback.created_at
    )


# ============ Admin: Statistics ============

@router.get("/statistics", response_model=FeedbackStatistics)
async def get_feedback_statistics(
    program_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get feedback statistics for the institution."""
    if not check_admin_or_edukator(current_user):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění")
    
    base_query = (
        select(Feedback)
        .join(Reservation, Feedback.reservation_id == Reservation.id)
        .where(
            Feedback.institution_id == current_user['institution_id'],
            Feedback.status == 'submitted'
        )
    )
    
    if program_id:
        base_query = base_query.where(Feedback.program_id == program_id)
    
    if date_from:
        base_query = base_query.where(Reservation.date >= date_from)
    
    if date_to:
        base_query = base_query.where(Reservation.date <= date_to)
    
    # Total count
    count_result = await db.execute(
        select(func.count(Feedback.id)).select_from(base_query.subquery())
    )
    total_feedbacks = count_result.scalar() or 0
    
    # Average rating
    avg_result = await db.execute(
        select(func.avg(Feedback.overall_rating))
        .select_from(base_query.where(Feedback.overall_rating.isnot(None)).subquery())
    )
    average_rating = avg_result.scalar()
    
    # Recommendation rate
    rec_result = await db.execute(
        select(
            func.count(Feedback.id).filter(Feedback.would_recommend == True),
            func.count(Feedback.id).filter(Feedback.would_recommend.isnot(None))
        ).select_from(base_query.subquery())
    )
    rec_row = rec_result.one()
    recommendation_rate = None
    if rec_row[1] and rec_row[1] > 0:
        recommendation_rate = round((rec_row[0] / rec_row[1]) * 100, 1)
    
    # By rating distribution
    by_rating = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    rating_dist_result = await db.execute(
        select(Feedback.overall_rating, func.count(Feedback.id))
        .where(
            Feedback.institution_id == current_user['institution_id'],
            Feedback.status == 'submitted',
            Feedback.overall_rating.isnot(None)
        )
        .group_by(Feedback.overall_rating)
    )
    for rating, count in rating_dist_result.all():
        if rating in by_rating:
            by_rating[rating] = count
    
    # By program
    by_program_result = await db.execute(
        select(
            Program.name_cs,
            func.count(Feedback.id),
            func.avg(Feedback.overall_rating)
        )
        .join(Feedback, Feedback.program_id == Program.id)
        .where(
            Feedback.institution_id == current_user['institution_id'],
            Feedback.status == 'submitted'
        )
        .group_by(Program.id, Program.name_cs)
        .order_by(func.count(Feedback.id).desc())
        .limit(10)
    )
    by_program = [
        {
            "program_name": name,
            "count": count,
            "avg_rating": round(avg, 2) if avg else None
        }
        for name, count, avg in by_program_result.all()
    ]
    
    return FeedbackStatistics(
        total_feedbacks=total_feedbacks,
        average_rating=round(average_rating, 2) if average_rating else None,
        recommendation_rate=recommendation_rate,
        by_rating=by_rating,
        by_program=by_program
    )


# ============ Admin: Export ============

@router.get("/export")
async def export_feedback_csv(
    program_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Export feedback data as CSV."""
    if not check_admin_only(current_user):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění exportovat data")
    
    query = (
        select(Feedback, Reservation, Program)
        .join(Reservation, Feedback.reservation_id == Reservation.id)
        .outerjoin(Program, Feedback.program_id == Program.id)
        .where(
            Feedback.institution_id == current_user['institution_id'],
            Feedback.status == 'submitted'
        )
    )
    
    if program_id:
        query = query.where(Feedback.program_id == program_id)
    
    if date_from:
        query = query.where(Reservation.date >= date_from)
    
    if date_to:
        query = query.where(Reservation.date <= date_to)
    
    query = query.order_by(Reservation.date.desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Datum rezervace',
        'Program',
        'Škola',
        'Celkové hodnocení',
        'Doporučil by',
        'Komentář',
        'Datum vyplnění'
    ])
    
    for feedback, reservation, program in rows:
        writer.writerow([
            reservation.date,
            program.name_cs if program else '',
            reservation.school_name,
            feedback.overall_rating or '',
            'Ano' if feedback.would_recommend else ('Ne' if feedback.would_recommend is False else ''),
            feedback.additional_comments or '',
            feedback.submitted_at.strftime('%Y-%m-%d %H:%M') if feedback.submitted_at else ''
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=feedback_export_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


# ============ Public: Feedback Form ============

@router.get("/public/{token}")
async def get_public_feedback_form(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Get public feedback form data by token."""
    result = await db.execute(
        select(Feedback, Reservation, Program, Institution)
        .join(Reservation, Feedback.reservation_id == Reservation.id)
        .join(Institution, Feedback.institution_id == Institution.id)
        .outerjoin(Program, Feedback.program_id == Program.id)
        .where(Feedback.token == token)
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(status_code=404, detail="Formulář nebyl nalezen nebo už není platný")
    
    feedback, reservation, program, institution = row
    
    if feedback.status == 'submitted':
        raise HTTPException(status_code=400, detail="Zpětná vazba již byla odeslána")
    
    if feedback.status == 'expired':
        raise HTTPException(status_code=400, detail="Platnost formuláře vypršela")
    
    # Get institution-level questions
    questions_result = await db.execute(
        select(FeedbackQuestion)
        .where(
            FeedbackQuestion.institution_id == feedback.institution_id,
            FeedbackQuestion.is_active == True
        )
        .order_by(FeedbackQuestion.display_order)
    )
    questions = questions_result.scalars().all()
    
    # Build questions list: institution-level questions
    all_questions = [
        {
            "id": str(q.id),
            "question_text": q.question_text,
            "question_type": q.question_type,
            "is_required": q.is_required
        }
        for q in questions
    ]
    
    # Add program-level custom feedback questions (from program.feedback_questions JSONB)
    if program and program.feedback_enabled and program.feedback_questions:
        for pq in program.feedback_questions:
            if pq.get("question"):
                # Map program question types to feedback types
                q_type = pq.get("type", "text")
                if q_type == "scale":
                    q_type = "rating"
                all_questions.append({
                    "id": f"prog_{pq.get('id', '')}",
                    "question_text": pq["question"],
                    "question_type": q_type,
                    "is_required": False
                })
    
    return {
        "institution_name": institution.name,
        "institution_logo": institution.logo_url,
        "program_name": program.name_cs if program else None,
        "reservation_date": reservation.date,
        "school_name": reservation.school_name,
        "feedback_enabled": program.feedback_enabled if program else True,
        "questions": all_questions
    }


@router.post("/public/{token}")
async def submit_public_feedback(
    token: str,
    data: FeedbackSubmission,
    db: AsyncSession = Depends(get_db)
):
    """Submit feedback via public form."""
    result = await db.execute(
        select(Feedback).where(Feedback.token == token)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Formulář nebyl nalezen")
    
    if feedback.status == 'submitted':
        raise HTTPException(status_code=400, detail="Zpětná vazba již byla odeslána")
    
    if feedback.status == 'expired':
        raise HTTPException(status_code=400, detail="Platnost formuláře vypršela")
    
    # Update feedback
    feedback.answers = data.answers
    feedback.overall_rating = data.overall_rating
    feedback.would_recommend = data.would_recommend
    feedback.additional_comments = data.additional_comments
    feedback.status = 'submitted'
    feedback.submitted_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {"message": "Děkujeme za vaši zpětnou vazbu!"}


# ============ Create Feedback Request (Internal) ============

async def create_feedback_request(
    db: AsyncSession,
    reservation_id: str,
    institution_id: str,
    program_id: str
) -> Feedback:
    """Create a pending feedback request for a completed reservation."""
    token = generate_feedback_token()
    
    feedback = Feedback(
        institution_id=institution_id,
        reservation_id=reservation_id,
        program_id=program_id,
        token=token,
        status='pending'
    )
    
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    
    return feedback


# ============ Database Migration Endpoint ============

@router.post("/setup-tables")
async def setup_feedback_tables(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create feedback tables if they don't exist (Admin only)."""
    if not check_admin_only(current_user):
        raise HTTPException(status_code=403, detail="Pouze admin může vytvořit tabulky")
    
    from sqlalchemy import text
    
    statements = [
        # Create feedback_questions table
        """
        CREATE TABLE IF NOT EXISTS feedback_questions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
            question_text TEXT NOT NULL,
            question_type TEXT NOT NULL DEFAULT 'rating',
            is_required BOOLEAN DEFAULT true,
            display_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT true,
            created_by UUID REFERENCES users(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_feedback_questions_institution ON feedback_questions(institution_id)",
        "CREATE INDEX IF NOT EXISTS idx_feedback_questions_active ON feedback_questions(is_active)",
        
        # Create feedbacks table
        """
        CREATE TABLE IF NOT EXISTS feedbacks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
            reservation_id UUID NOT NULL UNIQUE REFERENCES reservations(id) ON DELETE CASCADE,
            program_id UUID REFERENCES programs(id) ON DELETE SET NULL,
            token TEXT NOT NULL UNIQUE,
            answers JSONB DEFAULT '{}',
            overall_rating INTEGER,
            would_recommend BOOLEAN,
            additional_comments TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            email_sent_at TIMESTAMPTZ,
            reminder_sent_at TIMESTAMPTZ,
            submitted_at TIMESTAMPTZ,
            submitted_by_email TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_feedbacks_institution ON feedbacks(institution_id)",
        "CREATE INDEX IF NOT EXISTS idx_feedbacks_reservation ON feedbacks(reservation_id)",
        "CREATE INDEX IF NOT EXISTS idx_feedbacks_token ON feedbacks(token)",
        "CREATE INDEX IF NOT EXISTS idx_feedbacks_status ON feedbacks(status)",
    ]
    
    try:
        for stmt in statements:
            await db.execute(text(stmt))
        await db.commit()
        return {"message": "Tabulky pro zpětnou vazbu byly úspěšně vytvořeny"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Chyba při vytváření tabulek: {str(e)}")
