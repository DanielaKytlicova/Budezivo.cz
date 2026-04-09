"""
SQLAlchemy models for Supabase (PostgreSQL) database.
These models mirror the schema defined in /app/supabase/migrations/001_schema.sql
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, 
    ForeignKey, ARRAY, JSON, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase


def generate_uuid():
    """Generate UUID string."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Institution(Base):
    """Institution/Organization model."""
    __tablename__ = 'institutions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)  # museum, gallery, library, cultural_center, other
    country = Column(Text, nullable=False, default='CZ')
    address = Column(Text)
    city = Column(Text)
    psc = Column(Text)
    ico_dic = Column(Text)
    phone = Column(Text)
    email = Column(Text)
    website = Column(Text)
    logo_url = Column(Text)
    primary_color = Column(Text, default='#1E293B')
    secondary_color = Column(Text, default='#84A98C')
    
    # Plan & Limits
    plan = Column(Text, nullable=False, default='free')
    plan_updated_at = Column(DateTime(timezone=True))
    programs_limit = Column(Integer, nullable=False, default=3)
    bookings_monthly_limit = Column(Integer, nullable=False, default=50)
    
    # Default Operating Settings
    default_available_days = Column(ARRAY(Text), default=['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])
    default_time_blocks = Column(JSON, default=[{"start": "09:00", "end": "10:00"}])
    operating_start_date = Column(DateTime(timezone=True))
    operating_end_date = Column(DateTime(timezone=True))
    
    # Default Program Settings
    default_program_duration = Column(Integer, default=60)
    default_program_capacity = Column(Integer, default=30)
    default_target_group = Column(Text, default='schools')
    
    # Settings
    notification_settings = Column(JSON, default={"new_reservation": True, "confirmation": True, "cancellation": True, "sms_enabled": False})
    locale_settings = Column(JSON, default={"language": "cs", "timezone": "Europe/Prague", "date_format": "dd.mm.yyyy", "time_format": "24h"})
    gdpr_settings = Column(JSON, default={"data_retention": "never", "anonymize": False})
    pro_settings = Column(JSON, default={})
    
    # Onboarding
    onboarding_completed = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    users = relationship("User", back_populates="institution", cascade="all, delete-orphan")
    programs = relationship("Program", back_populates="institution", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="institution", cascade="all, delete-orphan")
    schools = relationship("School", back_populates="institution", cascade="all, delete-orphan")
    rooms = relationship("Room", back_populates="institution", cascade="all, delete-orphan")
    theme_settings = relationship("ThemeSetting", back_populates="institution", uselist=False, cascade="all, delete-orphan")


class User(Base):
    """User model."""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    email = Column(Text, nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    name = Column(Text)
    role = Column(Text, nullable=False, default='viewer')  # admin, spravce, edukator, lektor, pokladni, viewer
    status = Column(Text, nullable=False, default='active')  # active, inactive, pending
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    # GDPR
    gdpr_consent = Column(Boolean, default=False)
    gdpr_consent_date = Column(DateTime(timezone=True))
    terms_accepted = Column(Boolean, default=False)
    
    # Metadata
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    institution = relationship("Institution", back_populates="users")
    
    # Indexes
    __table_args__ = (
        Index('idx_users_institution', 'institution_id'),
        Index('idx_users_email', 'email'),
        Index('idx_users_role', 'role'),
    )


class Program(Base):
    """Program/Activity model."""
    __tablename__ = 'programs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    
    # Basic Info (multilingual)
    name_cs = Column(Text, nullable=False)
    name_en = Column(Text)
    description_cs = Column(Text, nullable=False)
    description_en = Column(Text)
    
    # Program Details
    duration = Column(Integer, nullable=False, default=60)
    age_group = Column(Text, nullable=False)  # ms_3_6, zs1_7_12, zs2_12_15, ss_14_18, gym_14_18, adults, all
    min_capacity = Column(Integer, nullable=False, default=5)
    max_capacity = Column(Integer, nullable=False, default=30)
    target_group = Column(Text, nullable=False, default='schools')  # schools, public, both - LEGACY
    target_groups = Column(JSON, default=[])  # Array of age groups: ms_3_6, zs1_7_12, zs2_12_15, ss_14_18, gym_14_18, adults, all
    price = Column(Float, default=0.0)
    
    # Status & Publishing
    status = Column(Text, nullable=False, default='active')  # active, concept, archived
    is_published = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=False)
    send_email_notification = Column(Boolean, default=True)
    
    # Schedule Settings
    available_days = Column(ARRAY(Text), default=['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])
    time_blocks = Column(JSON, default=["09:00-10:30"])
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    
    # Booking Parameters
    min_days_before_booking = Column(Integer, default=7)
    max_days_before_booking = Column(Integer, default=180)
    preparation_time = Column(Integer, default=10)
    cleanup_time = Column(Integer, default=30)
    
    # Collision & Parallel Settings
    allow_parallel = Column(Boolean, default=False)  # If True, program can run in parallel with others
    collision_resources = Column(JSON, default=[])  # ["lecturer", "room"] - resources to check for conflicts
    blocked_program_ids = Column(JSON, default=[])  # List of program IDs that cannot overlap with this one
    
    # Assigned Lecturer
    assigned_lecturer_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    # Assigned Room
    room_id = Column(UUID(as_uuid=True), ForeignKey('rooms.id', ondelete='SET NULL'))
    
    # Archive
    archived_at = Column(DateTime(timezone=True))
    archived_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    archive_reason = Column(Text)
    
    # Filtering & Tags
    age_categories = Column(ARRAY(Text), default=[])   # MS, ZS1, ZS2, SS
    subject_tags = Column(ARRAY(Text), default=[])      # hudební, výtvarné, technické, ...
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    institution = relationship("Institution", back_populates="programs")
    reservations = relationship("Reservation", back_populates="program", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_programs_institution', 'institution_id'),
        Index('idx_programs_status', 'status'),
    )


class Reservation(Base):
    """Reservation/Booking model."""
    __tablename__ = 'reservations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    program_id = Column(UUID(as_uuid=True), ForeignKey('programs.id', ondelete='CASCADE'), nullable=False)
    
    # Booking Details
    date = Column(Text, nullable=False)  # YYYY-MM-DD format
    time_block = Column(Text, nullable=False)
    
    # School/Group Info
    school_name = Column(Text, nullable=False)
    group_type = Column(Text, nullable=False)  # ms_3_6, zs1_7_12, etc.
    age_or_class = Column(Text)
    num_students = Column(Integer, nullable=False)
    num_teachers = Column(Integer, default=1)
    special_requirements = Column(Text)
    
    # Contact Info
    contact_name = Column(Text, nullable=False)
    contact_email = Column(Text, nullable=False)
    contact_phone = Column(Text, nullable=False)
    
    # Status & Workflow
    status = Column(Text, nullable=False, default='pending')  # pending, confirmed, cancelled, completed, no_show
    confirmed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    confirmed_at = Column(DateTime(timezone=True))
    cancelled_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    cancelled_at = Column(DateTime(timezone=True))
    cancellation_reason = Column(Text)
    
    # Actual attendance (filled by cashier)
    actual_students = Column(Integer)
    actual_teachers = Column(Integer)
    notes = Column(Text)
    
    # Assigned lecturer
    assigned_lecturer_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    assigned_lecturer_name = Column(Text)
    assigned_lecturer_at = Column(DateTime(timezone=True))
    
    # GDPR
    gdpr_consent = Column(Boolean, default=False)
    gdpr_consent_date = Column(DateTime(timezone=True))
    
    # Terms Acceptance (liability disclaimer)
    terms_accepted = Column(Boolean, default=False)
    terms_accepted_at = Column(DateTime(timezone=True))
    terms_accepted_text_version = Column(Text, default='v1')
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    institution = relationship("Institution", back_populates="reservations")
    program = relationship("Program", back_populates="reservations")
    
    # Indexes
    __table_args__ = (
        Index('idx_reservations_institution', 'institution_id'),
        Index('idx_reservations_program', 'program_id'),
        Index('idx_reservations_date', 'date'),
        Index('idx_reservations_status', 'status'),
    )


class School(Base):
    """School/CRM model for repeat visitors."""
    __tablename__ = 'schools'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    
    # School Info (unique by name + city within institution)
    name = Column(Text, nullable=False)
    address = Column(Text)
    city = Column(Text)
    ico = Column(Text)
    
    # Legacy Contact (deprecated - use school_contacts)
    contact_person = Column(Text)
    email = Column(Text)
    phone = Column(Text)
    
    # Statistics
    booking_count = Column(Integer, default=0)
    last_booking_date = Column(DateTime(timezone=True))
    
    # Tags & Source
    tags = Column(JSON, default=[])
    source = Column(Text, default='organic')  # organic, import, reservation
    
    # Notes
    notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    institution = relationship("Institution", back_populates="schools")
    contacts = relationship("SchoolContact", back_populates="school", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_schools_institution', 'institution_id'),
        Index('idx_schools_email', 'email'),
        Index('idx_schools_name_city', 'institution_id', 'name', 'city'),
    )


class Room(Base):
    """Room/Space model for collision management."""
    __tablename__ = 'rooms'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    capacity = Column(Integer)
    equipment = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    institution = relationship("Institution", back_populates="rooms")
    
    __table_args__ = (
        Index('idx_rooms_institution', 'institution_id'),
    )


class SchoolContact(Base):
    """Contact person for a school (1:N relationship)."""
    __tablename__ = 'school_contacts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(UUID(as_uuid=True), ForeignKey('schools.id', ondelete='CASCADE'), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    
    # Contact Info
    email = Column(Text, nullable=False)
    name = Column(Text)  # e.g. "Pedagog 1", "Ředitel"
    phone = Column(Text)
    
    # Status
    status = Column(Text, nullable=False, default='active')  # active, invalid, pending_verification
    
    # Email Validation
    email_validated = Column(Boolean, default=False)
    email_validation_error = Column(Text)
    last_email_sent_at = Column(DateTime(timezone=True))
    last_email_bounced = Column(Boolean, default=False)
    
    # Primary contact flag
    is_primary = Column(Boolean, default=False)
    
    # Notes
    notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    school = relationship("School", back_populates="contacts")
    
    # Indexes
    __table_args__ = (
        Index('idx_school_contacts_school', 'school_id'),
        Index('idx_school_contacts_email', 'email'),
        Index('idx_school_contacts_institution', 'institution_id'),
        Index('idx_school_contacts_status', 'status'),
    )


class ThemeSetting(Base):
    """Theme settings for institution branding."""
    __tablename__ = 'theme_settings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Colors
    primary_color = Column(Text, default='#1E293B')
    secondary_color = Column(Text, default='#84A98C')
    accent_color = Column(Text, default='#E9C46A')
    
    # Branding
    logo_url = Column(Text)
    header_style = Column(Text, default='light')  # light, dark
    footer_text = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    institution = relationship("Institution", back_populates="theme_settings")


class Payment(Base):
    """Payment transaction model."""
    __tablename__ = 'payments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='SET NULL'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    # Payment Details
    amount = Column(Float, nullable=False)
    currency = Column(Text, nullable=False, default='CZK')
    payment_method = Column(Text)  # card, bank_transfer, cash, invoice
    
    # Status
    status = Column(Text, nullable=False, default='pending')  # pending, paid, failed, refunded, cancelled
    payment_status = Column(Text, default='initiated')
    
    # Stripe Integration
    session_id = Column(Text)
    stripe_payment_intent_id = Column(Text)
    
    # Package Purchase
    package = Column(Text)  # basic, standard, premium
    billing_cycle = Column(Text)  # monthly, yearly
    
    # Metadata
    paid_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        Index('idx_payments_institution', 'institution_id'),
        Index('idx_payments_session', 'session_id'),
    )


class ContactMessage(Base):
    """Contact form messages."""
    __tablename__ = 'contact_messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Sender Info
    name = Column(Text, nullable=False)
    email = Column(Text, nullable=False)
    institution = Column(Text)
    
    # Message
    subject = Column(Text, default='general')
    message = Column(Text, nullable=False)
    
    # Status
    status = Column(Text, default='new')  # new, read, replied, archived
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    replied_at = Column(DateTime(timezone=True))


class ProgramEmailTemplate(Base):
    """Email template for program booking confirmations."""
    __tablename__ = 'program_email_templates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id = Column(UUID(as_uuid=True), ForeignKey('programs.id', ondelete='CASCADE'), nullable=False, unique=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    
    # Template Content
    subject = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    
    # Metadata
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        Index('idx_email_templates_program', 'program_id'),
        Index('idx_email_templates_institution', 'institution_id'),
    )


class EmailLog(Base):
    """Log of sent emails for audit and debugging."""
    __tablename__ = 'email_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    program_id = Column(UUID(as_uuid=True), ForeignKey('programs.id', ondelete='SET NULL'))
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='SET NULL'))
    
    # Email Details
    recipient_email = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)
    body_snapshot = Column(Text)  # Snapshot of rendered email body
    
    # Status
    status = Column(Text, nullable=False, default='pending')  # pending, sent, failed
    error_message = Column(Text)
    email_id = Column(Text)  # External ID from email provider (Resend)
    
    # Metadata
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        Index('idx_email_logs_institution', 'institution_id'),
        Index('idx_email_logs_reservation', 'reservation_id'),
        Index('idx_email_logs_status', 'status'),
    )


class FeedbackQuestion(Base):
    """Configurable feedback questions for institutions."""
    __tablename__ = 'feedback_questions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    
    # Question Details
    question_text = Column(Text, nullable=False)
    question_type = Column(Text, nullable=False, default='rating')  # rating, text, yesno
    is_required = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        Index('idx_feedback_questions_institution', 'institution_id'),
        Index('idx_feedback_questions_active', 'is_active'),
    )


class Feedback(Base):
    """Feedback submissions from teachers after reservations."""
    __tablename__ = 'feedbacks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='CASCADE'), nullable=False, unique=True)
    program_id = Column(UUID(as_uuid=True), ForeignKey('programs.id', ondelete='SET NULL'))
    
    # Feedback Token (for public access)
    token = Column(Text, nullable=False, unique=True)
    
    # Answers (JSON format: {question_id: answer_value})
    answers = Column(JSON, default={})
    
    # Overall Rating (1-5)
    overall_rating = Column(Integer)
    
    # Would Recommend (yes/no)
    would_recommend = Column(Boolean)
    
    # Additional Comments
    additional_comments = Column(Text)
    
    # Status
    status = Column(Text, nullable=False, default='pending')  # pending, submitted, expired
    
    # Email Tracking
    email_sent_at = Column(DateTime(timezone=True))
    reminder_sent_at = Column(DateTime(timezone=True))
    
    # Submission Info
    submitted_at = Column(DateTime(timezone=True))
    submitted_by_email = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    reservation = relationship("Reservation", backref="feedback")
    
    # Indexes
    __table_args__ = (
        Index('idx_feedbacks_institution', 'institution_id'),
        Index('idx_feedbacks_reservation', 'reservation_id'),
        Index('idx_feedbacks_token', 'token'),
        Index('idx_feedbacks_status', 'status'),
    )


class TeamInvitation(Base):
    """Team invitation model for inviting users to institutions."""
    __tablename__ = 'team_invitations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    invited_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Token for secure access
    token = Column(Text, nullable=False, unique=True)
    
    # Role to assign on acceptance
    role = Column(Text, nullable=False, default='viewer')
    
    # Name (optional, for display)
    name = Column(Text)
    
    # Expiration (48 hours by default)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Status
    accepted = Column(Boolean, default=False)
    accepted_at = Column(DateTime(timezone=True))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        Index('idx_team_invitations_email', 'email'),
        Index('idx_team_invitations_token', 'token'),
        Index('idx_team_invitations_institution', 'institution_id'),
    )


class LecturerAvailability(Base):
    """Recurring weekly availability for lecturers."""
    __tablename__ = 'lecturer_availability'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lecturer_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(Text, nullable=False)  # "08:00"
    end_time = Column(Text, nullable=False)    # "12:00"
    is_recurring = Column(Boolean, default=True)
    specific_date = Column(Text)  # "2026-04-15" for one-off blocks (null = recurring)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_lecturer_avail_lecturer', 'lecturer_id'),
        Index('idx_lecturer_avail_institution', 'institution_id'),
    )


class LecturerTimeOff(Base):
    """Specific time-off / blockages for lecturers."""
    __tablename__ = 'lecturer_time_off'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lecturer_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    start_date = Column(Text, nullable=False)      # "2026-03-25"
    end_date = Column(Text, nullable=False)         # "2026-03-25" (same for single day)
    start_time = Column(Text)                        # "08:00" (null = all day)
    end_time = Column(Text)                          # "16:00" (null = all day)
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_lecturer_timeoff_lecturer', 'lecturer_id'),
        Index('idx_lecturer_timeoff_institution', 'institution_id'),
    )



class AuditLog(Base):
    """Audit log for admin actions."""
    __tablename__ = 'audit_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    user_email = Column(Text, default='')
    action = Column(Text, nullable=False)       # create, update, delete, archive, confirm, cancel, ...
    entity_type = Column(Text, nullable=False)  # program, reservation, school, settings, ...
    entity_id = Column(Text)
    details = Column(JSON, default={})
    ip_address = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_audit_logs_institution', 'institution_id'),
        Index('idx_audit_logs_created', 'created_at'),
    )
