"""
Pydantic models (schemas) for request/response validation.
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr, validator
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
    name: Optional[str] = None  # Personal name (first + last)
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
    terms_accepted: bool = False


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
    refresh_token: Optional[str] = None
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
    pricing_info: Optional[str] = None
    image_url: Optional[str] = None
    status: str = "active"
    requires_approval: bool = False
    is_published: bool = True
    is_in_catalog: bool = False  # Opt-in to public B2B catalog "Programy pro školy"
    send_email_notification: bool = False
    available_days: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    time_blocks: List[str] = ["09:00-10:30"]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    min_days_before_booking: int = 14
    max_days_before_booking: int = 90
    preparation_time: int = 0
    cleanup_time: int = 0
    # Collision & Parallel Settings
    allow_parallel: bool = False
    collision_resources: List[str] = []
    collision_lecturer_ids: List[str] = []
    blocked_program_ids: List[str] = []
    # How many lecturers this program needs (default 1 = unchanged behavior).
    # When > 1, a booking requires that many qualified+free lecturers in the slot.
    required_lecturers: int = 1
    # Assigned Lecturer
    assigned_lecturer_id: Optional[str] = None
    # Assigned Room
    room_id: Optional[str] = None
    # Feedback Settings (PRO)
    feedback_enabled: bool = True
    feedback_questions: List[dict] = []
    # Archive (lecturer-editable curatorial note rendered into the archive PDF)
    archive_custom_text: Optional[str] = None

    @validator('feedback_enabled', pre=True, always=True)
    def default_feedback_enabled(cls, v):
        return v if v is not None else True

    @validator('required_lecturers', pre=True, always=True)
    def clamp_required_lecturers(cls, v):
        try:
            return max(1, int(v)) if v is not None else 1
        except (TypeError, ValueError):
            return 1

    @validator('feedback_questions', pre=True, always=True)
    def default_feedback_questions(cls, v):
        return v if v is not None else []


class ProgramCreate(ProgramBase):
    pass


class Program(ProgramBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    institution_id: str
    assigned_lecturer_id: Optional[str] = None
    created_at: datetime


# ============ Booking Models ============

class BookingBase(BaseModel):
    program_id: str
    date: str
    time_block: str
    school_name: str
    group_type: str
    age_or_class: Optional[str] = None
    num_students: int
    num_teachers: int = 1
    special_requirements: Optional[str] = ""
    contact_name: str
    contact_email: EmailStr
    contact_phone: str
    gdpr_consent: bool = True
    marketing_consent: bool = False  # M1 Phase 76 — opt-in to future promotional mailings


class BookingCreate(BookingBase):
    terms_accepted: bool = False
    terms_accepted_text_version: Optional[str] = "v1"
    # Optional admin override: lecturer selected manually. Ignored on public endpoint.
    assigned_lecturer_id: Optional[str] = None


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
    assignment_source: Optional[str] = None
    assignment_reason: Optional[str] = None
    notes: Optional[str] = None
    terms_accepted: Optional[bool] = None
    terms_accepted_at: Optional[datetime] = None
    terms_accepted_text_version: Optional[str] = None
    program_name: Optional[str] = None
    visit_reminder_sent_at: Optional[datetime] = None
    visit_reminder_last_attempt_at: Optional[datetime] = None
    visit_reminder_error: Optional[str] = None
    created_at: datetime


class PublicBooking(BookingBase):
    """Public booking response - excludes internal fields like institution_id, notes, etc."""
    model_config = ConfigDict(extra="ignore")
    id: str
    status: str = "pending"
    terms_accepted: Optional[bool] = None
    program_name: Optional[str] = None
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
    contact_person: Optional[str] = ""
    email: EmailStr
    phone: Optional[str] = ""
    ico: Optional[str] = None
    city: Optional[str] = None
    notes: Optional[str] = None


class School(SchoolBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    institution_id: str
    booking_count: int = 0
    tags: Optional[List[str]] = []
    source: Optional[str] = "organic"  # organic, import, reservation
    created_at: datetime


class SchoolUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    ico: Optional[str] = None
    city: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


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
    name: Optional[str] = None
    role: str
    status: Optional[str] = None
    lecturer_mode: Optional[str] = "main"  # main | training (náslech)
    preferred_age_groups: Optional[List[str]] = []
    supported_program_ids: Optional[List[str]] = []
    learning_program_ids: Optional[List[str]] = []
    admin_note: Optional[str] = None
    institution_id: str
    created_at: str


class LecturerProfileUpdate(BaseModel):
    preferred_age_groups: Optional[List[str]] = None
    supported_program_ids: Optional[List[str]] = None
    learning_program_ids: Optional[List[str]] = None
    admin_note: Optional[str] = None
    name: Optional[str] = None


class TeamInvite(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    role: str = "edukator"
    lecturer_mode: Optional[str] = "main"


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



# ============ Lecturer Availability Models ============

class LecturerAvailabilityCreate(BaseModel):
    days_of_week: List[int] = []  # 0=Monday, 6=Sunday, allows multi-select (for recurring)
    start_time: str  # "08:00"
    end_time: str    # "12:00"
    specific_date: Optional[str] = None  # "2026-04-15" for one-off blocks

class LecturerAvailabilityUpdate(BaseModel):
    day_of_week: Optional[int] = None
    start_time: str
    end_time: str
    specific_date: Optional[str] = None

class LecturerAvailabilityResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    lecturer_id: str
    day_of_week: int
    start_time: str
    end_time: str
    is_recurring: bool = True
    specific_date: Optional[str] = None

class LecturerTimeOffCreate(BaseModel):
    start_date: str  # "2026-03-25"
    end_date: str    # "2026-03-25"
    start_time: Optional[str] = None  # "08:00" (null = all day)
    end_time: Optional[str] = None    # "16:00"
    reason: Optional[str] = None

class LecturerTimeOffUpdate(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    reason: Optional[str] = None

class LecturerTimeOffResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    lecturer_id: str
    start_date: str
    end_date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    reason: Optional[str] = None
