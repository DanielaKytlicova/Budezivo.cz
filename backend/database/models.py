"""
SQLAlchemy models for Supabase (PostgreSQL) database.
These models mirror the schema defined in /app/supabase/migrations/001_schema.sql
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, 
    ForeignKey, ARRAY, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    plan = Column(Text, nullable=False, default='free')  # free, start, pro, pro_plus
    plan_status = Column(Text, nullable=False, default='active')  # inactive, pending, active, expired, cancelled
    plan_activated_by = Column(Text)  # payment, admin, migration, system
    plan_activated_at = Column(DateTime(timezone=True))
    plan_expires_at = Column(DateTime(timezone=True))
    plan_updated_at = Column(DateTime(timezone=True))
    requested_plan_type = Column(Text)  # pending plan request
    plan_changed_by_user_id = Column(UUID(as_uuid=True))
    plan_changed_by_superadmin_id = Column(UUID(as_uuid=True))
    auto_renew = Column(Boolean, default=False)
    billing_provider = Column(Text)  # manual, fakturoid, stripe
    billing_external_id = Column(Text)  # external invoice/subscription ID
    billing_note = Column(Text)  # internal admin note
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
    lecturer_mode = Column(Text, nullable=False, default='main')  # main | training (náslech)
    preferred_age_groups = Column(JSONB, default=list)   # e.g. ["ms_3_6","zs1_7_12"]
    supported_program_ids = Column(JSONB, default=list)  # programs the lecturer can lead
    learning_program_ids = Column(JSONB, default=list)   # programs the lecturer wants to learn
    admin_note = Column(Text)
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
    # How many lecturers this program needs. Default 1 = behaves like today.
    # When > 1, a booking is only allowed if >= this many QUALIFIED lecturers
    # (program in their supported_program_ids) are free at that time.
    required_lecturers = Column(Integer, nullable=False, default=1, server_default='1')
    target_group = Column(Text, nullable=False, default='schools')  # schools, public, both - LEGACY
    target_groups = Column(JSON, default=[])  # Array of age groups: ms_3_6, zs1_7_12, zs2_12_15, ss_14_18, gym_14_18, adults, all
    price = Column(Float, default=0.0)
    pricing_info = Column(Text)  # Free-form "30 Kč/dítě, pedagog zdarma" — display-only, propagated to confirmation email
    image_url = Column(Text)  # Cover image on public booking page (gated by `program_photos` feature flag)
    
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
    collision_lecturer_ids = Column(JSON, default=[])  # List of specific lecturer IDs to check for collisions
    blocked_program_ids = Column(JSON, default=[])  # List of program IDs that cannot overlap with this one
    
    # Assigned Lecturer
    assigned_lecturer_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    # Assigned Room
    room_id = Column(UUID(as_uuid=True), ForeignKey('rooms.id', ondelete='SET NULL'))
    
    # Archive
    archived_at = Column(DateTime(timezone=True))
    archived_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    archive_reason = Column(Text)
    # Free-form curatorial note that gets rendered into the archive PDF as the
    # "Poznámka" section. Editable from the archive page; lecturer fills this
    # in alongside the description.
    archive_custom_text = Column(Text)
    
    # Filtering & Tags
    age_categories = Column(ARRAY(Text), default=[])   # MS, ZS1, ZS2, SS
    subject_tags = Column(ARRAY(Text), default=[])      # hudební, výtvarné, technické, ...

    # Public B2B catalog (Programy pro školy) opt-in
    is_in_catalog = Column(Boolean, default=False, nullable=False)
    
    # Feedback Settings (PRO feature)
    feedback_enabled = Column(Boolean, default=True)
    feedback_questions = Column(JSON, default=[])  # [{id, question, type: "text"|"scale"|"yesno"}] max 5
    
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
    # Reliable link to a School (nullable; SET NULL on school delete). Enables
    # safe test-data purge and accurate school stats without name matching.
    school_id = Column(UUID(as_uuid=True), ForeignKey('schools.id', ondelete='SET NULL'), nullable=True)
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
    # All assigned lecturers (multi-lecturer programs). The "main" lecturer stays
    # in assigned_lecturer_id; this list holds every assigned lecturer's id (str).
    assigned_lecturer_ids = Column(JSONB, default=list)

    # Main-lecturer assignment auditability (source + human-readable reason)
    assignment_source = Column(Text)  # default_program | auto_suggest | manual_admin | unassigned
    assignment_reason = Column(Text)
    
    # GDPR
    gdpr_consent = Column(Boolean, default=False)
    gdpr_consent_date = Column(DateTime(timezone=True))
    
    # Terms Acceptance (liability disclaimer)
    terms_accepted = Column(Boolean, default=False)
    terms_accepted_at = Column(DateTime(timezone=True))
    terms_accepted_text_version = Column(Text, default='v1')

    # Marketing opt-in (M1 Phase 76 — propagates to contacts.marketing_consent)
    marketing_consent = Column(Boolean, default=False)
    
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



class UserCalendarIntegration(Base):
    """Stores Microsoft OAuth tokens for calendar sync."""
    __tablename__ = 'user_calendar_integrations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    provider = Column(Text, nullable=False, default='microsoft')
    access_token = Column(Text)
    refresh_token = Column(Text)
    expires_at = Column(DateTime(timezone=True))
    microsoft_user_id = Column(Text)
    external_calendar_id = Column(Text)
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime(timezone=True))
    sync_error = Column(Text)
    # Two-way sync mode flags (Google). Import = external events block availability;
    # export = Budeživo reservations are pushed to the user's calendar.
    import_enabled = Column(Boolean, nullable=False, default=True, server_default='true')
    export_enabled = Column(Boolean, nullable=False, default=False, server_default='false')
    auto_sync_enabled = Column(Boolean, nullable=False, default=True, server_default='true')
    # Set when the stored grant lacks a required scope (e.g. calendar.events) and
    # the user must re-authorize. Never triggers an infinite connect loop.
    needs_reconnect = Column(Boolean, nullable=False, default=False, server_default='false')
    granted_scopes = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class CalendarEventExport(Base):
    """Maps a Budeživo reservation to a provider calendar event created by us.

    Only events tracked here (and carrying extendedProperties.private.source =
    'budezivo') may be updated or deleted by Budeživo. Personal user events are
    never touched.
    """
    __tablename__ = 'calendar_event_exports'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    booking_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='CASCADE'), nullable=False)
    provider = Column(Text, nullable=False, default='google')
    google_calendar_id = Column(Text)
    google_event_id = Column(Text)
    # Provider-agnostic identifiers (used by Microsoft; Google keeps its own columns).
    external_calendar_id = Column(Text)
    external_event_id = Column(Text)
    last_synced_at = Column(DateTime(timezone=True))
    sync_status = Column(Text, default='pending')
    sync_error = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('provider', 'user_id', 'booking_id', name='uq_calendar_event_exports_provider_user_booking'),
    )


class CalendarFeedToken(Base):
    """Revocable, hashed token for a subscribable ICS feed (live URL).

    The raw token is shown to the user ONCE and stored only as a SHA-256 hash.
    Bound to institution + owner + feed type + optional entity + role-derived scope.
    """
    __tablename__ = 'calendar_feed_tokens'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    feed_type = Column(Text, nullable=False)          # institution | program | lecturer
    entity_id = Column(UUID(as_uuid=True))            # program_id / user_id / institution_id (null → institution)
    scope = Column(Text, nullable=False, default='institution')  # institution | assigned
    token_hash = Column(Text, nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    revoked_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('idx_calendar_feed_tokens_owner', 'institution_id', 'user_id', 'feed_type'),
    )



class AvailabilityBlock(Base):
    """External calendar blocks (Outlook) or manual blocks for availability."""
    __tablename__ = 'availability_blocks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    source = Column(Text, nullable=False, default='manual')  # 'outlook' | 'manual'
    external_event_id = Column(Text)
    title = Column(Text)
    override = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))



class RefreshToken(Base):
    """Refresh tokens for JWT rotation."""
    __tablename__ = 'refresh_tokens'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    user_agent = Column(Text)
    ip_address = Column(Text)


class OAuthState(Base):
    """Persistent OAuth states for multi-instance safety."""
    __tablename__ = 'oauth_states'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state = Column(Text, nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    institution_id = Column(UUID(as_uuid=True), nullable=False)
    redirect_uri = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)



# ============ EVENTS MODULE (Pilot) ============

class FeatureFlag(Base):
    """Feature flags for pilot/beta features."""
    __tablename__ = 'feature_flags'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(Text, nullable=False, unique=True)
    enabled = Column(Boolean, default=False)
    allowed_institution_ids = Column(JSON, default=[])
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Event(Base):
    """Event / Camp / Activity."""
    __tablename__ = 'events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False, default='event')  # reservation, event, camp
    description = Column(Text)
    capacity = Column(Integer, default=30)
    price = Column(Float, default=0.0)
    currency = Column(Text, default='CZK')
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    image_url = Column(Text)
    form_fields = Column(JSON, default=[])  # [{id, type, label, required, options, order}]
    # Subset of the institution's globally-allowed methods offered for THIS event.
    # NULL for free events (no payment). Values: qr, gateway, cash.
    allowed_payment_methods = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_events_institution', 'institution_id'),
    )


class EventDate(Base):
    """Specific date/time for an event."""
    __tablename__ = 'event_dates'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    start_datetime = Column(DateTime(timezone=True), nullable=False)
    end_datetime = Column(DateTime(timezone=True), nullable=False)
    capacity_override = Column(Integer)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_event_dates_event', 'event_id'),
    )


class EventApplication(Base):
    """Application / registration for an event."""
    __tablename__ = 'event_applications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    event_date_id = Column(UUID(as_uuid=True), ForeignKey('event_dates.id', ondelete='SET NULL'))
    status = Column(Text, nullable=False, default='pending')  # pending, approved, rejected
    payment_status = Column(Text, nullable=False, default='unpaid')  # unpaid, pending, paid, not_required
    payment_method = Column(Text)  # qr, gateway, cash, free
    # Manual-payment audit (who/when marked a QR/cash payment as paid)
    paid_marked_by_email = Column(Text)
    paid_marked_at = Column(DateTime(timezone=True))
    # When a "please pay" reminder was sent (QR/cash, before the event). Null = not sent.
    payment_reminder_sent_at = Column(DateTime(timezone=True))
    total_amount = Column(Float, default=0.0)
    variable_symbol = Column(Text)
    applicant_data = Column(JSON, default={})  # form field answers
    applicant_email = Column(Text)
    applicant_name = Column(Text)
    note = Column(Text)
    # Marketing opt-in (M1 Phase 76)
    marketing_consent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_event_applications_event', 'event_id'),
        Index('idx_event_applications_institution', 'institution_id'),
        Index('idx_event_applications_vs', 'variable_symbol'),
    )


class InstitutionPaymentSettings(Base):
    """Payment configuration per institution."""
    __tablename__ = 'institution_payment_settings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False, unique=True)
    payment_mode = Column(Text, default='qr')  # legacy: qr, gateway, both
    # Globally-supported methods for the institution. Values: qr, gateway, cash.
    allowed_methods = Column(JSON)
    provider = Column(Text)  # gopay, comgate, null
    iban = Column(Text)
    account_number = Column(Text)
    bank_code = Column(Text)
    account_name = Column(Text)
    gateway_api_key = Column(Text)
    gateway_secret = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class EventPayment(Base):
    """Payment tracking for event applications."""
    __tablename__ = 'event_payments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey('event_applications.id', ondelete='CASCADE'), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    provider = Column(Text, default='qr')  # qr, gopay, comgate
    status = Column(Text, default='pending')  # pending, paid, failed
    amount = Column(Float, nullable=False)
    currency = Column(Text, default='CZK')
    variable_symbol = Column(Text)
    provider_payment_id = Column(Text)
    qr_payload = Column(Text)
    paid_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_event_payments_application', 'application_id'),
    )



# ============ AVAILABILITY EXCEPTIONS ============

class AvailabilityException(Base):
    """One-off availability exceptions (closures) for programs or lecturers."""
    __tablename__ = 'availability_exceptions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    scope_type = Column(Text, nullable=False)  # 'program' or 'lecturer'
    scope_id = Column(UUID(as_uuid=True), nullable=False)  # program_id or lecturer_id
    date = Column(Text, nullable=False)  # "2026-05-15"
    start_time = Column(Text)  # "09:00" (null = all day)
    end_time = Column(Text)  # "12:00" (null = all day)
    reason = Column(Text)
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_avail_exc_scope', 'scope_type', 'scope_id', 'date'),
        Index('idx_avail_exc_institution', 'institution_id'),
    )



# ============ WAITLIST / TERM WATCHING ============

class WaitlistEntry(Base):
    """Waitlist entry for watching available program slots."""
    __tablename__ = 'waitlist_entries'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    program_id = Column(UUID(as_uuid=True), ForeignKey('programs.id', ondelete='CASCADE'), nullable=False)
    teacher_name = Column(Text, nullable=False)
    school_name = Column(Text, nullable=False)
    email = Column(Text, nullable=False)
    phone = Column(Text)
    participant_count = Column(Integer, nullable=False, default=1)
    request_type = Column(Text, nullable=False, default='specific_date')  # specific_date, date_range
    requested_date = Column(Text)  # "2026-05-15"
    range_start_date = Column(Text)
    range_end_date = Column(Text)
    preferred_time_of_day = Column(Text, default='any')  # morning, midday, afternoon, any
    notes = Column(Text)
    status = Column(Text, nullable=False, default='active')  # active, contacted, booked, cancelled, expired
    admin_note = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_waitlist_institution', 'institution_id'),
        Index('idx_waitlist_program', 'program_id'),
        Index('idx_waitlist_status', 'status'),
        Index('idx_waitlist_email_program', 'email', 'program_id'),
    )


# ============ MAILING CAMPAIGNS ============

class MailingCampaign(Base):
    """Promotional mailing campaign."""
    __tablename__ = 'mailing_campaigns'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))

    # Campaign metadata
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False, default='single_program')  # single_program | seasonal | custom
    status = Column(Text, nullable=False, default='draft')  # draft | sending | sent | partial | failed

    # Recipient selection mode
    recipient_mode = Column(Text, nullable=False, default='relevant_only')  # relevant_only | all | manual | relevant_plus_manual

    # Email content blocks
    subject = Column(Text, nullable=False, default='')
    greeting = Column(Text, nullable=False, default='')
    intro_text = Column(Text, nullable=False, default='')
    closing_text = Column(Text, nullable=False, default='')
    signature = Column(Text, nullable=False, default='')

    # Snapshots at send time
    content_snapshot = Column(JSON, default={})  # snapshot of email content
    selection_snapshot = Column(JSON, default={})  # snapshot of selection criteria
    programs_snapshot = Column(JSON, default=[])  # snapshot of programs data

    # Stats
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    # Timestamps
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_mailing_campaigns_institution', 'institution_id'),
        Index('idx_mailing_campaigns_status', 'status'),
    )


class MailingCampaignProgram(Base):
    """Programs included in a mailing campaign."""
    __tablename__ = 'mailing_campaign_programs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey('mailing_campaigns.id', ondelete='CASCADE'), nullable=False)
    program_id = Column(UUID(as_uuid=True), ForeignKey('programs.id', ondelete='SET NULL'))
    display_order = Column(Integer, default=0)

    __table_args__ = (
        Index('idx_mcp_campaign', 'campaign_id'),
    )


class MailingCampaignRecipient(Base):
    """Individual recipient of a mailing campaign."""
    __tablename__ = 'mailing_campaign_recipients'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey('mailing_campaigns.id', ondelete='CASCADE'), nullable=False)
    school_id = Column(UUID(as_uuid=True), ForeignKey('schools.id', ondelete='SET NULL'))
    contact_id = Column(UUID(as_uuid=True), ForeignKey('school_contacts.id', ondelete='SET NULL'))
    email = Column(Text, nullable=False)
    school_name = Column(Text)
    contact_name = Column(Text)

    # Delivery status
    status = Column(Text, nullable=False, default='pending')  # pending | sent | failed | skipped
    sent_at = Column(DateTime(timezone=True))
    failure_reason = Column(Text)
    email_provider_id = Column(Text)  # Resend email ID

    # Why this recipient was selected
    matching_reason = Column(JSON, default={})  # {selection_mode, matched_segments, manual_override}

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_mcr_campaign', 'campaign_id'),
        Index('idx_mcr_status', 'status'),
    )


class MailingRecipientProgram(Base):
    """Which specific programs each recipient actually received."""
    __tablename__ = 'mailing_recipient_programs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey('mailing_campaign_recipients.id', ondelete='CASCADE'), nullable=False)
    program_id = Column(UUID(as_uuid=True), ForeignKey('programs.id', ondelete='SET NULL'))
    program_name = Column(Text)  # snapshot
    program_target_groups = Column(JSON, default=[])  # snapshot

    __table_args__ = (
        Index('idx_mrp_recipient', 'recipient_id'),
    )



# ============ BILLING ORDERS ============

class BillingOrder(Base):
    """Billing order for plan activation. Tracks payment lifecycle."""
    __tablename__ = 'billing_orders'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    requested_plan_type = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default='pending')  # pending, paid, cancelled, failed, refunded
    provider = Column(Text, nullable=False, default='manual')  # manual, fakturoid, stripe
    provider_invoice_id = Column(Text)
    provider_payment_id = Column(Text)
    amount = Column(Integer)  # in smallest currency unit (CZK haléře)
    currency = Column(Text, default='CZK')
    note = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    paid_at = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_billing_orders_institution', 'institution_id'),
        Index('idx_billing_orders_status', 'status'),
        Index('idx_billing_orders_provider', 'provider'),
    )


# ============ USAGE METRICS ============

class UsageMetric(Base):
    """Institution-level feature usage tracking for product analytics."""
    __tablename__ = 'usage_metrics'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    feature_key = Column(Text, nullable=False)
    usage_count = Column(Integer, nullable=False, default=0)
    first_used_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    metadata_json = Column(JSON, default={})

    __table_args__ = (
        Index('idx_usage_metrics_institution', 'institution_id'),
        Index('idx_usage_metrics_feature', 'feature_key'),
        Index('idx_usage_metrics_inst_feature', 'institution_id', 'feature_key', unique=True),
    )



class ReservationObserver(Base):
    """Náslech — lecturer joins reservation as observer. Does NOT affect collision logic."""
    __tablename__ = 'reservation_observers'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='CASCADE'), nullable=False)
    lecturer_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    role = Column(Text, nullable=False, default='naslech')
    status = Column(Text, nullable=False, default='pending')  # pending | approved | rejected
    requested_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    approved_at = Column(DateTime(timezone=True))



# ============ TEACHER ACCOUNTS (B2C – external teacher / parent self-registration) ============

class TeacherAccount(Base):
    """
    Self-registered external teacher / parent account.
    Completely separate from `users` table (which holds institution staff).
    Used for catalog favorites and booking history. Also serves as auth for the
    public-facing B2B Catalog (Programy pro školy).
    """
    __tablename__ = 'teacher_accounts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, nullable=False, unique=True)
    password_hash = Column(Text)             # nullable → reserved for future Google OAuth-only accounts
    name = Column(Text, nullable=False)
    school_name = Column(Text)               # optional — used for prefill of bookings
    phone = Column(Text)
    auth_provider = Column(Text, nullable=False, default='password')  # password | google (future)
    google_sub = Column(Text)                # future: Google subject id
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('idx_teacher_accounts_email', 'email'),
        Index('idx_teacher_accounts_google_sub', 'google_sub'),
    )


class TeacherFavorite(Base):
    """A program a teacher has marked as favorite (per (teacher, program) pair)."""
    __tablename__ = 'teacher_favorites'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey('teacher_accounts.id', ondelete='CASCADE'), nullable=False)
    program_id = Column(UUID(as_uuid=True), ForeignKey('programs.id', ondelete='CASCADE'), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_teacher_favorites_teacher', 'teacher_id'),
        Index('idx_teacher_favorites_program', 'program_id'),
        Index('idx_teacher_favorites_unique', 'teacher_id', 'program_id', unique=True),
    )


class TeacherLoginAttempt(Base):
    """Brute-force tracker for teacher login (IP + email key)."""
    __tablename__ = 'teacher_login_attempts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identifier = Column(Text, nullable=False)   # "{ip}:{email}"
    failed_count = Column(Integer, nullable=False, default=0)
    last_failed_at = Column(DateTime(timezone=True))
    locked_until = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_teacher_login_attempts_identifier', 'identifier', unique=True),
    )



class PageView(Base):
    """Lightweight traffic-analytics record (anonymized).

    Recorded on every SPA route change via POST /api/analytics/pageview.
    ``ip_hash`` is SHA-256 of the visitor IP + the ``ADMIN_IP`` env list is
    excluded at write-time so the site owner doesn't skew their own stats.
    """
    __tablename__ = 'page_views'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    path = Column(Text, nullable=False)
    ip_hash = Column(Text, nullable=False)
    user_agent = Column(Text)
    session_id = Column(Text, nullable=False)
    referrer = Column(Text)

    __table_args__ = (
        Index('idx_page_views_created_at', 'created_at'),
        Index('idx_page_views_session', 'session_id'),
        Index('idx_page_views_path', 'path'),
    )



# ──────────────────────────────────────────────────────────────────────────
#  Contacts (Phase 76 — M1)
#  Centralized address book auto-populated from Reservation + EventApplication.
#  Deduplicated by (institution_id, lowercased email).
# ──────────────────────────────────────────────────────────────────────────

class Contact(Base):
    """A single contact person belonging to an institution.

    Sources: school reservations, event applications (workshops, camps,
    baby-play sessions etc.), or a manual admin entry.
    """
    __tablename__ = 'contacts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)

    # Identity
    first_name = Column(Text)
    last_name = Column(Text)
    email = Column(Text, nullable=False)         # primary identifier within institution
    phone = Column(Text)

    # Categorisation
    type = Column(Text, default='jine')          # skola | pedagog | rodic | verejnost | odborna_verejnost | jine
    primary_source = Column(Text)                # first source that created the contact

    # School association (denormalised for filtering speed)
    school_name = Column(Text)
    school_type = Column(Text)                   # MS | ZS | SS | VOS | VS | null

    # GDPR / marketing
    marketing_consent = Column(Boolean)          # NULL = unknown (legacy); True = opted in; False = explicitly refused
    marketing_consent_at = Column(DateTime(timezone=True))

    # Free-form admin note
    note = Column(Text)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_activity_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('idx_contacts_institution', 'institution_id'),
        Index('idx_contacts_email_inst', 'institution_id', 'email', unique=True),
        Index('idx_contacts_type', 'type'),
        Index('idx_contacts_consent', 'marketing_consent'),
    )


class ContactLink(Base):
    """Many-to-many between a Contact and a concrete activity (program / event).

    One Contact can have many links (each booking, application, repeat visit
    creates one row). Used by the targeted-mailing UI to filter recipients
    by past participation.
    """
    __tablename__ = 'contact_links'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(UUID(as_uuid=True), ForeignKey('contacts.id', ondelete='CASCADE'), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)

    # Link target — exactly one of these is set
    program_id = Column(UUID(as_uuid=True), ForeignKey('programs.id', ondelete='SET NULL'))
    event_id = Column(UUID(as_uuid=True), ForeignKey('events.id', ondelete='SET NULL'))
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='SET NULL'))
    application_id = Column(UUID(as_uuid=True), ForeignKey('event_applications.id', ondelete='SET NULL'))

    source_type = Column(Text, nullable=False)   # skolni_rezervace | jednorazova_akce | workshop | kurz | primestsky_tabor | baby_herna | rucne
    role = Column(Text)                          # objednavajici | ucastnik | zakonny_zastupce | pedagog | skolni_kontakt
    status = Column(Text)                        # prihlasen | potvrzeno | zaplaceno | zruseno | ucastnil_se
    label = Column(Text)                         # human-friendly name (program/event title at link time)

    linked_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_contact_links_contact', 'contact_id'),
        Index('idx_contact_links_institution', 'institution_id'),
        Index('idx_contact_links_program', 'program_id'),
        Index('idx_contact_links_event', 'event_id'),
        Index('idx_contact_links_source', 'source_type'),
    )


class InstitutionJoinRequest(Base):
    """Request from a user to join an existing institution (Phase 83).

    Created when:
    * Someone tries to register a new institution that collides with an
      existing one (by IČO match, or similar name+city)
    * An already-logged-in user explicitly asks to be added to a different
      institution

    Reviewed by the target institution's admin (or a superadmin) who picks the
    role and approves/rejects. Idempotent — only one ``pending`` row per
    ``(email, institution_id)`` is allowed.
    """
    __tablename__ = 'institution_join_requests'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False)

    # Identity of the requester (we always store email; user_id is set when
    # the requester was logged in at submit time)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    email = Column(Text, nullable=False)
    name = Column(Text)

    # Optional free-text message from the requester (max ~500 chars enforced
    # at the API layer)
    message = Column(Text)

    # pending | approved | rejected
    status = Column(Text, nullable=False, default='pending')

    # Role granted upon approval (chosen by the reviewing admin)
    assigned_role = Column(Text)

    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    reviewed_at = Column(DateTime(timezone=True))
    review_note = Column(Text)  # admin's explanation if rejected

    __table_args__ = (
        Index('idx_join_req_institution', 'institution_id'),
        Index('idx_join_req_email', 'email'),
        Index('idx_join_req_status', 'status'),
    )
