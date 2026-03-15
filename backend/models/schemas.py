"""
Pydantic models (schemas) for request/response validation.
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============ Auth Models ============

class UserBase(BaseModel):
    email: EmailStr
    institution_name: str
    institution_type: str
    country: str


class UserCreate(UserBase):
    password: str
    # Step 2 - Additional institution info
    address: Optional[str] = None
    city: Optional[str] = None
    ico_dic: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = "#1E293B"
    secondary_color: Optional[str] = "#84A98C"
    # Step 3 - Operating hours defaults
    default_available_days: Optional[List[str]] = None
    default_time_blocks: Optional[List[Dict[str, str]]] = None
    operating_start_date: Optional[str] = None
    operating_end_date: Optional[str] = None
    # Step 4 - Default program settings
    default_program_description: Optional[str] = None
    default_program_duration: Optional[int] = 60
    default_program_capacity: Optional[int] = 30
    default_target_group: Optional[str] = "schools"
    # GDPR
    gdpr_consent: bool = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    institution_id: str
    role: str = "admin"
    created_at: datetime


class TokenResponse(BaseModel):
    token: str
    user: Dict[str, Any]


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


# ============ Program Models ============

class ProgramBase(BaseModel):
    name_cs: str
    name_en: str
    description_cs: str
    description_en: str
    duration: int
    age_group: str  # Legacy - kept for backwards compatibility
    target_groups: List[str] = []  # New: Array of target groups ['ms_3_6', 'zs1_7_12', ...]
    min_capacity: int = 5
    max_capacity: int = 30
    target_group: str  # Legacy - kept for backwards compatibility
    price: Optional[float] = 0.0
    status: str = "active"
    requires_approval: bool = False
    is_published: bool = True
    send_email_notification: bool = False
    available_days: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    time_blocks: List[str] = ["09:00-10:30"]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    min_days_before_booking: int = 14
    max_days_before_booking: int = 90
    preparation_time: int = 10
    cleanup_time: int = 30


class ProgramCreate(ProgramBase):
    pass


class Program(ProgramBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    institution_id: str
    created_at: datetime


# ============ Booking Models ============

class BookingBase(BaseModel):
    program_id: str
    date: str
    time_block: str
    school_name: str
    group_type: str
    age_or_class: str
    num_students: int
    num_teachers: int = 1
    special_requirements: Optional[str] = ""
    contact_name: str
    contact_email: EmailStr
    contact_phone: str
    gdpr_consent: bool = True


class BookingCreate(BookingBase):
    pass


class Booking(BookingBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    institution_id: str
    status: str = "pending"
    actual_students: Optional[int] = None
    actual_teachers: Optional[int] = None
    assigned_lecturer_id: Optional[str] = None
    assigned_lecturer_name: Optional[str] = None
    assigned_lecturer_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class BookingUpdate(BaseModel):
    status: Optional[str] = None
    actual_students: Optional[int] = None
    actual_teachers: Optional[int] = None
    notes: Optional[str] = None
    date: Optional[str] = None
    time_block: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_name: Optional[str] = None


class BookingLectorAssign(BaseModel):
    lecturer_id: str
    lecturer_name: str


# ============ School Models ============

class SchoolBase(BaseModel):
    name: str
    contact_person: str
    email: EmailStr
    phone: str
    ico: Optional[str] = None
    city: Optional[str] = None


class School(SchoolBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    institution_id: str
    booking_count: int = 0
    created_at: datetime


# ============ Settings Models ============

class ThemeSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    institution_id: str
    primary_color: str = "#1E293B"
    secondary_color: str = "#84A98C"
    accent_color: str = "#E9C46A"
    logo_url: Optional[str] = None
    header_style: str = "light"
    footer_text: Optional[str] = None


class ThemeUpdate(BaseModel):
    primary_color: str = "#1E293B"
    secondary_color: str = "#84A98C"
    accent_color: str = "#E9C46A"
    logo_url: Optional[str] = None
    header_style: str = "light"
    footer_text: Optional[str] = None


class ProSettings(BaseModel):
    csv_export_enabled: bool = True
    csv_export_exception: bool = False  # Admin může povolit výjimku pro free plán
    mass_propagation_enabled: bool = True
    email_subject_template: str = "Nový program: {program_name}"
    email_body_template: str = "Dobrý den,\\n\\nrádi bychom Vás informovali o novém programu {program_name}.\\n\\n{program_description}\\n\\nRezervovat můžete zde: {reservation_url}\\n\\nS pozdravem,\\n{institution_name}"


class InstitutionSettings(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    ico_dic: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    psc: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None


class NotificationSettings(BaseModel):
    new_reservation: bool = False
    confirmation: bool = False
    cancellation: bool = True
    sms_enabled: bool = False


class LocaleSettings(BaseModel):
    language: str = "cs"
    timezone: str = "europe"
    date_format: str = "dd.mm.yyyy"
    time_format: str = "24h"


class GdprSettings(BaseModel):
    data_retention: str = "never"
    anonymize: bool = False


# ============ Team Models ============

class TeamMember(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    role: str
    institution_id: str
    created_at: str


class TeamInvite(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    role: str = "edukator"


class RoleUpdate(BaseModel):
    role: str


# ============ Dashboard Models ============

class DashboardStats(BaseModel):
    today_bookings: int
    upcoming_groups: int
    capacity_usage: float
    bookings_used: int
    bookings_limit: int


# ============ Payment Models ============

class PaymentTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    institution_id: str
    user_id: str
    session_id: str
    amount: float
    currency: str
    package: str
    status: str
    payment_status: str
    created_at: datetime


class PaymentSessionCreate(BaseModel):
    package: str
    billing_cycle: str


# ============ Contact Models ============

class ContactFormData(BaseModel):
    name: str
    email: EmailStr
    institution: Optional[str] = None
    subject: str = "general"
    message: str


# ============ Propagation Models ============

class PropagationRequest(BaseModel):
    school_ids: List[str]
    program_id: str
