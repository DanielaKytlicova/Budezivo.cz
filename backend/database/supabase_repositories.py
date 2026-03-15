"""
Repository pattern for Supabase (PostgreSQL) database operations.
Uses SQLAlchemy async for all database queries.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    Institution, User, Program, Reservation, School, 
    ThemeSetting, Payment, ContactMessage, ProgramEmailTemplate, EmailLog
)

logger = logging.getLogger(__name__)


def to_dict(obj, exclude: set = None) -> dict:
    """Convert SQLAlchemy model to dictionary."""
    if obj is None:
        return None
    exclude = exclude or set()
    result = {}
    for c in obj.__table__.columns:
        if c.name not in exclude:
            value = getattr(obj, c.name)
            # Convert UUID to string
            if isinstance(value, uuid.UUID):
                value = str(value)
            # Convert datetime to ISO string
            elif isinstance(value, datetime):
                value = value.isoformat()
            result[c.name] = value
    return result


class UserRepositorySupabase:
    """Repository for user operations with Supabase."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_by_email(self, email: str) -> Optional[dict]:
        """Find user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        return to_dict(user) if user else None
    
    async def find_by_id(self, user_id: str) -> Optional[dict]:
        """Find user by ID, excluding password hash."""
        result = await self.db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        user = result.scalar_one_or_none()
        return to_dict(user, exclude={'password_hash'}) if user else None
    
    async def find_by_institution(self, institution_id: str) -> List[dict]:
        """Find all users in an institution."""
        result = await self.db.execute(
            select(User).where(User.institution_id == uuid.UUID(institution_id))
        )
        users = result.scalars().all()
        return [to_dict(u, exclude={'password_hash'}) for u in users]
    
    async def create(self, user_data: dict) -> dict:
        """Create new user."""
        user = User(
            id=uuid.uuid4(),
            institution_id=uuid.UUID(user_data['institution_id']),
            email=user_data['email'],
            password_hash=user_data['password_hash'],
            name=user_data.get('name'),
            role=user_data.get('role', 'viewer'),
            status=user_data.get('status', 'active'),
            invited_by=uuid.UUID(user_data['invited_by']) if user_data.get('invited_by') else None,
            gdpr_consent=user_data.get('gdpr_consent', False),
            gdpr_consent_date=datetime.now(timezone.utc) if user_data.get('gdpr_consent') else None,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return to_dict(user)
    
    async def update_role(self, user_id: str, institution_id: str, role: str) -> int:
        """Update user role."""
        result = await self.db.execute(
            update(User)
            .where(and_(
                User.id == uuid.UUID(user_id),
                User.institution_id == uuid.UUID(institution_id)
            ))
            .values(role=role)
        )
        await self.db.commit()
        return result.rowcount
    
    async def delete_by_id(self, user_id: str, institution_id: str) -> int:
        """Delete user by ID."""
        result = await self.db.execute(
            delete(User)
            .where(and_(
                User.id == uuid.UUID(user_id),
                User.institution_id == uuid.UUID(institution_id)
            ))
        )
        await self.db.commit()
        return result.rowcount


class InstitutionRepositorySupabase:
    """Repository for institution operations with Supabase."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_by_id(self, institution_id: str) -> Optional[dict]:
        """Find institution by ID."""
        result = await self.db.execute(
            select(Institution).where(Institution.id == uuid.UUID(institution_id))
        )
        inst = result.scalar_one_or_none()
        return to_dict(inst) if inst else None
    
    async def create(self, institution_data: dict) -> dict:
        """Create new institution."""
        inst = Institution(
            id=uuid.uuid4(),
            name=institution_data['name'],
            type=institution_data['type'],
            country=institution_data.get('country', 'CZ'),
            address=institution_data.get('address'),
            city=institution_data.get('city'),
            ico_dic=institution_data.get('ico_dic'),
            logo_url=institution_data.get('logo_url'),
            default_available_days=institution_data.get('default_available_days', ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']),
            default_time_blocks=institution_data.get('default_time_blocks', [{"start": "09:00", "end": "10:00"}]),
            default_program_duration=institution_data.get('default_program_duration', 60),
            default_program_capacity=institution_data.get('default_program_capacity', 30),
            default_target_group=institution_data.get('default_target_group', 'schools'),
            plan=institution_data.get('plan', 'free'),
            programs_limit=institution_data.get('programs_limit', 3),
        )
        self.db.add(inst)
        await self.db.commit()
        await self.db.refresh(inst)
        return to_dict(inst)
    
    async def update(self, institution_id: str, update_data: dict) -> int:
        """Update institution."""
        result = await self.db.execute(
            update(Institution)
            .where(Institution.id == uuid.UUID(institution_id))
            .values(**update_data)
        )
        await self.db.commit()
        return result.rowcount
    
    async def update_pro_settings(self, institution_id: str, pro_settings: dict) -> int:
        """Update PRO settings."""
        return await self.update(institution_id, {"pro_settings": pro_settings})


class ProgramRepositorySupabase:
    """Repository for program operations with Supabase."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_by_id(self, program_id: str, institution_id: str = None) -> Optional[dict]:
        """Find program by ID."""
        query = select(Program).where(Program.id == uuid.UUID(program_id))
        if institution_id:
            query = query.where(Program.institution_id == uuid.UUID(institution_id))
        result = await self.db.execute(query)
        prog = result.scalar_one_or_none()
        return to_dict(prog) if prog else None
    
    async def find_by_institution(self, institution_id: str) -> List[dict]:
        """Find all programs for an institution."""
        result = await self.db.execute(
            select(Program).where(Program.institution_id == uuid.UUID(institution_id))
        )
        programs = result.scalars().all()
        return [to_dict(p) for p in programs]
    
    async def find_public(self, institution_id: str) -> List[dict]:
        """Find all active published programs."""
        result = await self.db.execute(
            select(Program).where(and_(
                Program.institution_id == uuid.UUID(institution_id),
                Program.status == 'active'
            ))
        )
        programs = result.scalars().all()
        return [to_dict(p) for p in programs]
    
    async def create(self, program_data: dict, institution_id: str) -> dict:
        """Create new program."""
        prog = Program(
            id=uuid.uuid4(),
            institution_id=uuid.UUID(institution_id),
            name_cs=program_data['name_cs'],
            name_en=program_data.get('name_en'),
            description_cs=program_data['description_cs'],
            description_en=program_data.get('description_en'),
            duration=program_data.get('duration', 60),
            age_group=program_data['age_group'],
            min_capacity=program_data.get('min_capacity', 5),
            max_capacity=program_data.get('max_capacity', 30),
            target_group=program_data.get('target_group', 'schools'),
            target_groups=program_data.get('target_groups', []),
            price=program_data.get('price', 0.0),
            status=program_data.get('status', 'active'),
            is_published=program_data.get('is_published', True),
            requires_approval=program_data.get('requires_approval', False),
            send_email_notification=program_data.get('send_email_notification', True),
            available_days=program_data.get('available_days', ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']),
            time_blocks=program_data.get('time_blocks', ["09:00-10:30"]),
            min_days_before_booking=program_data.get('min_days_before_booking', 14),
            max_days_before_booking=program_data.get('max_days_before_booking', 90),
            preparation_time=program_data.get('preparation_time', 10),
            cleanup_time=program_data.get('cleanup_time', 30),
        )
        self.db.add(prog)
        await self.db.commit()
        await self.db.refresh(prog)
        return to_dict(prog)
    
    async def update(self, program_id: str, institution_id: str, update_data: dict) -> int:
        """Update program."""
        result = await self.db.execute(
            update(Program)
            .where(and_(
                Program.id == uuid.UUID(program_id),
                Program.institution_id == uuid.UUID(institution_id)
            ))
            .values(**update_data)
        )
        await self.db.commit()
        return result.rowcount
    
    async def delete(self, program_id: str, institution_id: str) -> int:
        """Delete program."""
        result = await self.db.execute(
            delete(Program)
            .where(and_(
                Program.id == uuid.UUID(program_id),
                Program.institution_id == uuid.UUID(institution_id)
            ))
        )
        await self.db.commit()
        return result.rowcount


class BookingRepositorySupabase:
    """Repository for booking/reservation operations with Supabase."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_by_id(self, booking_id: str, institution_id: str) -> Optional[dict]:
        """Find booking by ID."""
        result = await self.db.execute(
            select(Reservation).where(and_(
                Reservation.id == uuid.UUID(booking_id),
                Reservation.institution_id == uuid.UUID(institution_id)
            ))
        )
        booking = result.scalar_one_or_none()
        return to_dict(booking) if booking else None
    
    async def find_by_institution(self, institution_id: str) -> List[dict]:
        """Find all bookings for an institution, sorted by created_at desc."""
        result = await self.db.execute(
            select(Reservation)
            .where(Reservation.institution_id == uuid.UUID(institution_id))
            .order_by(Reservation.created_at.desc())
        )
        bookings = result.scalars().all()
        return [to_dict(b) for b in bookings]
    
    async def find_by_date(self, institution_id: str, date: str) -> List[dict]:
        """Find bookings for specific date."""
        result = await self.db.execute(
            select(Reservation).where(and_(
                Reservation.institution_id == uuid.UUID(institution_id),
                Reservation.date == date,
                Reservation.status != 'cancelled'
            ))
        )
        bookings = result.scalars().all()
        return [to_dict(b) for b in bookings]
    
    async def find_by_program_and_date(
        self, institution_id: str, program_id: str, date: str
    ) -> List[dict]:
        """Find bookings for a program on specific date."""
        result = await self.db.execute(
            select(Reservation).where(and_(
                Reservation.institution_id == uuid.UUID(institution_id),
                Reservation.program_id == uuid.UUID(program_id),
                Reservation.date == date,
                Reservation.status != 'cancelled'
            ))
        )
        bookings = result.scalars().all()
        return [to_dict(b) for b in bookings]
    
    async def count_today(self, institution_id: str, today: str) -> int:
        """Count today's non-cancelled bookings."""
        result = await self.db.execute(
            select(func.count(Reservation.id)).where(and_(
                Reservation.institution_id == uuid.UUID(institution_id),
                Reservation.date == today,
                Reservation.status != 'cancelled'
            ))
        )
        return result.scalar() or 0
    
    async def count_upcoming(self, institution_id: str, today: str) -> int:
        """Count upcoming non-cancelled bookings."""
        result = await self.db.execute(
            select(func.count(Reservation.id)).where(and_(
                Reservation.institution_id == uuid.UUID(institution_id),
                Reservation.date >= today,
                Reservation.status != 'cancelled'
            ))
        )
        return result.scalar() or 0
    
    async def count_month(self, institution_id: str, month_prefix: str) -> int:
        """Count bookings created this month."""
        # For PostgreSQL, we need to compare timestamps differently
        result = await self.db.execute(
            select(func.count(Reservation.id)).where(and_(
                Reservation.institution_id == uuid.UUID(institution_id),
                func.to_char(Reservation.created_at, 'YYYY-MM').like(f'{month_prefix}%')
            ))
        )
        return result.scalar() or 0
    
    async def create(self, booking_data: dict, institution_id: str) -> dict:
        """Create new booking."""
        booking = Reservation(
            id=uuid.uuid4(),
            institution_id=uuid.UUID(institution_id),
            program_id=uuid.UUID(booking_data['program_id']),
            date=booking_data['date'],
            time_block=booking_data['time_block'],
            school_name=booking_data['school_name'],
            group_type=booking_data['group_type'],
            age_or_class=booking_data.get('age_or_class'),
            num_students=booking_data['num_students'],
            num_teachers=booking_data.get('num_teachers', 1),
            special_requirements=booking_data.get('special_requirements'),
            contact_name=booking_data['contact_name'],
            contact_email=booking_data['contact_email'],
            contact_phone=booking_data['contact_phone'],
            status='pending',
            gdpr_consent=booking_data.get('gdpr_consent', False),
            gdpr_consent_date=datetime.now(timezone.utc) if booking_data.get('gdpr_consent') else None,
        )
        self.db.add(booking)
        await self.db.commit()
        await self.db.refresh(booking)
        return to_dict(booking)
    
    async def update(self, booking_id: str, institution_id: str, update_data: dict) -> int:
        """Update booking."""
        result = await self.db.execute(
            update(Reservation)
            .where(and_(
                Reservation.id == uuid.UUID(booking_id),
                Reservation.institution_id == uuid.UUID(institution_id)
            ))
            .values(**update_data)
        )
        await self.db.commit()
        return result.rowcount
    
    async def update_status(self, booking_id: str, institution_id: str, status: str) -> int:
        """Update booking status."""
        return await self.update(booking_id, institution_id, {"status": status})
    
    async def assign_lecturer(
        self, booking_id: str, institution_id: str,
        lecturer_id: str, lecturer_name: str
    ) -> int:
        """Assign lecturer to booking."""
        return await self.update(booking_id, institution_id, {
            "assigned_lecturer_id": uuid.UUID(lecturer_id),
            "assigned_lecturer_name": lecturer_name,
            "assigned_lecturer_at": datetime.now(timezone.utc)
        })
    
    async def unassign_lecturer(self, booking_id: str, institution_id: str) -> int:
        """Remove lecturer assignment."""
        return await self.update(booking_id, institution_id, {
            "assigned_lecturer_id": None,
            "assigned_lecturer_name": None,
            "assigned_lecturer_at": None
        })


class SchoolRepositorySupabase:
    """Repository for school/CRM operations with Supabase."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_by_institution(self, institution_id: str) -> List[dict]:
        """Find all schools for an institution."""
        result = await self.db.execute(
            select(School).where(School.institution_id == uuid.UUID(institution_id))
        )
        schools = result.scalars().all()
        return [to_dict(s) for s in schools]
    
    async def find_by_email(self, institution_id: str, email: str) -> Optional[dict]:
        """Find school by email in institution."""
        result = await self.db.execute(
            select(School).where(and_(
                School.institution_id == uuid.UUID(institution_id),
                School.email == email
            ))
        )
        school = result.scalar_one_or_none()
        return to_dict(school) if school else None
    
    async def find_by_ids(self, institution_id: str, school_ids: List[str]) -> List[dict]:
        """Find schools by IDs."""
        uuid_ids = [uuid.UUID(sid) for sid in school_ids]
        result = await self.db.execute(
            select(School).where(and_(
                School.institution_id == uuid.UUID(institution_id),
                School.id.in_(uuid_ids)
            ))
        )
        schools = result.scalars().all()
        return [to_dict(s) for s in schools]
    
    async def create(self, school_data: dict, institution_id: str) -> dict:
        """Create new school."""
        school = School(
            id=uuid.uuid4(),
            institution_id=uuid.UUID(institution_id),
            name=school_data['name'],
            contact_person=school_data.get('contact_person'),
            email=school_data.get('email'),
            phone=school_data.get('phone'),
            city=school_data.get('city'),
            ico=school_data.get('ico'),
            booking_count=school_data.get('booking_count', 1),
        )
        self.db.add(school)
        await self.db.commit()
        await self.db.refresh(school)
        return to_dict(school)
    
    async def increment_booking_count(self, school_id: str) -> None:
        """Increment booking count for school."""
        await self.db.execute(
            update(School)
            .where(School.id == uuid.UUID(school_id))
            .values(booking_count=School.booking_count + 1)
        )
        await self.db.commit()


class ThemeRepositorySupabase:
    """Repository for theme settings with Supabase."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_by_institution(self, institution_id: str) -> Optional[dict]:
        """Find theme settings for institution."""
        result = await self.db.execute(
            select(ThemeSetting).where(ThemeSetting.institution_id == uuid.UUID(institution_id))
        )
        theme = result.scalar_one_or_none()
        return to_dict(theme) if theme else None
    
    async def create_or_update(self, institution_id: str, theme_data: dict) -> dict:
        """Create or update theme settings."""
        existing = await self.find_by_institution(institution_id)
        
        if existing:
            await self.db.execute(
                update(ThemeSetting)
                .where(ThemeSetting.institution_id == uuid.UUID(institution_id))
                .values(**theme_data)
            )
            await self.db.commit()
        else:
            theme = ThemeSetting(
                id=uuid.uuid4(),
                institution_id=uuid.UUID(institution_id),
                **theme_data
            )
            self.db.add(theme)
            await self.db.commit()
        
        return await self.find_by_institution(institution_id)


class PaymentRepositorySupabase:
    """Repository for payment transactions with Supabase."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_by_session(self, session_id: str, institution_id: str) -> Optional[dict]:
        """Find payment by session ID."""
        result = await self.db.execute(
            select(Payment).where(and_(
                Payment.session_id == session_id,
                Payment.institution_id == uuid.UUID(institution_id)
            ))
        )
        payment = result.scalar_one_or_none()
        return to_dict(payment) if payment else None
    
    async def create(self, payment_data: dict) -> dict:
        """Create payment record."""
        payment = Payment(
            id=uuid.uuid4(),
            institution_id=uuid.UUID(payment_data['institution_id']),
            user_id=uuid.UUID(payment_data['user_id']) if payment_data.get('user_id') else None,
            session_id=payment_data.get('session_id'),
            amount=payment_data['amount'],
            currency=payment_data.get('currency', 'CZK'),
            package=payment_data.get('package'),
            status=payment_data.get('status', 'pending'),
            payment_status=payment_data.get('payment_status', 'initiated'),
        )
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return to_dict(payment)
    
    async def update_status(self, session_id: str, status: str, payment_status: str) -> int:
        """Update payment status."""
        result = await self.db.execute(
            update(Payment)
            .where(Payment.session_id == session_id)
            .values(status=status, payment_status=payment_status)
        )
        await self.db.commit()
        return result.rowcount


class ContactRepositorySupabase:
    """Repository for contact messages with Supabase."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, contact_data: dict) -> dict:
        """Create contact message."""
        contact = ContactMessage(
            id=uuid.uuid4(),
            name=contact_data['name'],
            email=contact_data['email'],
            institution=contact_data.get('institution'),
            subject=contact_data.get('subject', 'general'),
            message=contact_data['message'],
            status='new',
        )
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return to_dict(contact)


class SettingsRepositorySupabase:
    """Repository for institution settings with Supabase."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def update_notifications(self, institution_id: str, settings: dict) -> None:
        """Update notification settings."""
        await self.db.execute(
            update(Institution)
            .where(Institution.id == uuid.UUID(institution_id))
            .values(notification_settings=settings)
        )
        await self.db.commit()
    
    async def update_locale(self, institution_id: str, settings: dict) -> None:
        """Update locale settings."""
        await self.db.execute(
            update(Institution)
            .where(Institution.id == uuid.UUID(institution_id))
            .values(locale_settings=settings)
        )
        await self.db.commit()
    
    async def update_gdpr(self, institution_id: str, settings: dict) -> None:
        """Update GDPR settings."""
        await self.db.execute(
            update(Institution)
            .where(Institution.id == uuid.UUID(institution_id))
            .values(gdpr_settings=settings)
        )
        await self.db.commit()



class EmailTemplateRepositorySupabase:
    """Repository for program email templates with Supabase."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_by_program(self, program_id: str) -> Optional[dict]:
        """Find email template by program ID."""
        result = await self.db.execute(
            select(ProgramEmailTemplate).where(
                ProgramEmailTemplate.program_id == uuid.UUID(program_id)
            )
        )
        template = result.scalar_one_or_none()
        return to_dict(template) if template else None
    
    async def find_by_institution(self, institution_id: str) -> List[dict]:
        """Find all email templates for an institution."""
        result = await self.db.execute(
            select(ProgramEmailTemplate).where(
                ProgramEmailTemplate.institution_id == uuid.UUID(institution_id)
            )
        )
        templates = result.scalars().all()
        return [to_dict(t) for t in templates]
    
    async def create_or_update(
        self,
        program_id: str,
        institution_id: str,
        subject: str,
        body: str,
        updated_by: str
    ) -> dict:
        """Create or update email template."""
        from datetime import datetime, timezone
        
        existing = await self.find_by_program(program_id)
        
        if existing:
            # Update existing template
            await self.db.execute(
                update(ProgramEmailTemplate)
                .where(ProgramEmailTemplate.program_id == uuid.UUID(program_id))
                .values(
                    subject=subject,
                    body=body,
                    updated_by=uuid.UUID(updated_by),
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await self.db.commit()
        else:
            # Create new template
            template = ProgramEmailTemplate(
                id=uuid.uuid4(),
                program_id=uuid.UUID(program_id),
                institution_id=uuid.UUID(institution_id),
                subject=subject,
                body=body,
                updated_by=uuid.UUID(updated_by),
            )
            self.db.add(template)
            await self.db.commit()
        
        return await self.find_by_program(program_id)
    
    async def delete(self, program_id: str) -> int:
        """Delete email template."""
        result = await self.db.execute(
            delete(ProgramEmailTemplate)
            .where(ProgramEmailTemplate.program_id == uuid.UUID(program_id))
        )
        await self.db.commit()
        return result.rowcount


class EmailLogRepositorySupabase:
    """Repository for email logs with Supabase."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, log_data: dict) -> dict:
        """Create email log entry."""
        from datetime import datetime, timezone
        
        log = EmailLog(
            id=uuid.uuid4(),
            institution_id=uuid.UUID(log_data['institution_id']),
            program_id=uuid.UUID(log_data['program_id']) if log_data.get('program_id') else None,
            reservation_id=uuid.UUID(log_data['reservation_id']) if log_data.get('reservation_id') else None,
            recipient_email=log_data['recipient_email'],
            subject=log_data['subject'],
            body_snapshot=log_data.get('body_snapshot'),
            status=log_data.get('status', 'pending'),
            error_message=log_data.get('error_message'),
            email_id=log_data.get('email_id'),
            sent_at=datetime.now(timezone.utc) if log_data.get('status') == 'sent' else None,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return to_dict(log)
    
    async def find_by_program(self, program_id: str, limit: int = 50) -> List[dict]:
        """Find email logs by program."""
        result = await self.db.execute(
            select(EmailLog)
            .where(EmailLog.program_id == uuid.UUID(program_id))
            .order_by(EmailLog.created_at.desc())
            .limit(limit)
        )
        logs = result.scalars().all()
        return [to_dict(l) for l in logs]
    
    async def find_by_reservation(self, reservation_id: str) -> List[dict]:
        """Find email logs by reservation."""
        result = await self.db.execute(
            select(EmailLog)
            .where(EmailLog.reservation_id == uuid.UUID(reservation_id))
            .order_by(EmailLog.created_at.desc())
        )
        logs = result.scalars().all()
        return [to_dict(l) for l in logs]
    
    async def find_by_institution(self, institution_id: str, limit: int = 100) -> List[dict]:
        """Find all email logs for an institution."""
        result = await self.db.execute(
            select(EmailLog)
            .where(EmailLog.institution_id == uuid.UUID(institution_id))
            .order_by(EmailLog.created_at.desc())
            .limit(limit)
        )
        logs = result.scalars().all()
        return [to_dict(l) for l in logs]
    
    async def update_status(self, log_id: str, status: str, error_message: str = None) -> int:
        """Update log status."""
        from datetime import datetime, timezone
        
        values = {"status": status}
        if status == "sent":
            values["sent_at"] = datetime.now(timezone.utc)
        if error_message:
            values["error_message"] = error_message
        
        result = await self.db.execute(
            update(EmailLog)
            .where(EmailLog.id == uuid.UUID(log_id))
            .values(**values)
        )
        await self.db.commit()
        return result.rowcount
