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
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    users = relationship("User", back_populates="institution", cascade="all, delete-orphan")
    programs = relationship("Program", back_populates="institution", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="institution", cascade="all, delete-orphan")
    schools = relationship("School", back_populates="institution", cascade="all, delete-orphan")
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
    target_group = Column(Text, nullable=False, default='schools')  # schools, public, both
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
    min_days_before_booking = Column(Integer, default=14)
    max_days_before_booking = Column(Integer, default=90)
    preparation_time = Column(Integer, default=10)
    cleanup_time = Column(Integer, default=30)
    
    # Assigned Lecturer
    assigned_lecturer_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
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
    
    # School Info
    name = Column(Text, nullable=False)
    address = Column(Text)
    city = Column(Text)
    ico = Column(Text)
    
    # Contact
    contact_person = Column(Text)
    email = Column(Text)
    phone = Column(Text)
    
    # Statistics
    booking_count = Column(Integer, default=0)
    last_booking_date = Column(DateTime(timezone=True))
    
    # Notes
    notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    institution = relationship("Institution", back_populates="schools")
    
    # Indexes
    __table_args__ = (
        Index('idx_schools_institution', 'institution_id'),
        Index('idx_schools_email', 'email'),
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
