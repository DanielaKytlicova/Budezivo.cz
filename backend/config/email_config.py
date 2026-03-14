"""
Email Configuration for Budeživo.cz
Centralized email settings and sender addresses.
"""
import os
from enum import Enum
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


class EmailType(str, Enum):
    """Email type categories."""
    # Account
    USER_REGISTRATION_CONFIRMATION = "user_registration_confirmation"
    ACCOUNT_ACTIVATION = "account_activation"
    PASSWORD_RESET = "password_reset"
    PASSWORD_CHANGED = "password_changed"
    
    # Reservations
    RESERVATION_CREATED_TEACHER = "reservation_created_teacher"
    RESERVATION_CREATED_INSTITUTION = "reservation_created_institution"
    RESERVATION_CONFIRMED = "reservation_confirmed"
    RESERVATION_REJECTED = "reservation_rejected"
    RESERVATION_UPDATED = "reservation_updated"
    RESERVATION_CANCELLED = "reservation_cancelled"
    
    # Reminders
    RESERVATION_REMINDER_TEACHER = "reservation_reminder_teacher"
    RESERVATION_REMINDER_INSTITUTION = "reservation_reminder_institution"
    
    # Admin
    NEW_INSTITUTION_REGISTRATION = "new_institution_registration"


class SenderType(str, Enum):
    """Sender address types."""
    NO_REPLY = "no_reply"
    RESERVATIONS = "reservations"
    ACCOUNTS = "accounts"


# Environment
ENV = os.environ.get("ENV", "production")
IS_DEVELOPMENT = ENV == "development"

# Resend API
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

# Sender addresses - production vs development
if IS_DEVELOPMENT:
    DEV_EMAIL = os.environ.get("DEV_EMAIL", "dev@budezivo.cz")
    SENDER_ADDRESSES = {
        SenderType.NO_REPLY: f"Budeživo <{DEV_EMAIL}>",
        SenderType.RESERVATIONS: f"Rezervace Budeživo <{DEV_EMAIL}>",
        SenderType.ACCOUNTS: f"Účty Budeživo <{DEV_EMAIL}>",
    }
else:
    SENDER_ADDRESSES = {
        SenderType.NO_REPLY: "Budeživo <no-reply@budezivo.cz>",
        SenderType.RESERVATIONS: "Rezervace Budeživo <reservations@budezivo.cz>",
        SenderType.ACCOUNTS: "Účty Budeživo <accounts@budezivo.cz>",
    }

# Default sender for backwards compatibility
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

# Email type to sender mapping
EMAIL_TYPE_SENDERS: Dict[EmailType, SenderType] = {
    # Account emails use accounts sender
    EmailType.USER_REGISTRATION_CONFIRMATION: SenderType.ACCOUNTS,
    EmailType.ACCOUNT_ACTIVATION: SenderType.ACCOUNTS,
    EmailType.PASSWORD_RESET: SenderType.ACCOUNTS,
    EmailType.PASSWORD_CHANGED: SenderType.ACCOUNTS,
    
    # Reservation emails use reservations sender
    EmailType.RESERVATION_CREATED_TEACHER: SenderType.RESERVATIONS,
    EmailType.RESERVATION_CREATED_INSTITUTION: SenderType.RESERVATIONS,
    EmailType.RESERVATION_CONFIRMED: SenderType.RESERVATIONS,
    EmailType.RESERVATION_REJECTED: SenderType.RESERVATIONS,
    EmailType.RESERVATION_UPDATED: SenderType.RESERVATIONS,
    EmailType.RESERVATION_CANCELLED: SenderType.RESERVATIONS,
    
    # Reminders use reservations sender
    EmailType.RESERVATION_REMINDER_TEACHER: SenderType.RESERVATIONS,
    EmailType.RESERVATION_REMINDER_INSTITUTION: SenderType.RESERVATIONS,
    
    # Admin emails use no-reply
    EmailType.NEW_INSTITUTION_REGISTRATION: SenderType.NO_REPLY,
}


def get_sender_for_email_type(email_type: EmailType) -> str:
    """Get the appropriate sender address for an email type."""
    sender_type = EMAIL_TYPE_SENDERS.get(email_type, SenderType.NO_REPLY)
    return SENDER_ADDRESSES.get(sender_type, SENDER_EMAIL)


def get_dev_recipient(original_email: str) -> str:
    """In development mode, redirect all emails to dev email."""
    if IS_DEVELOPMENT:
        return os.environ.get("DEV_EMAIL", "dev@budezivo.cz")
    return original_email


# Available template variables with Czech descriptions
TEMPLATE_VARIABLES: Dict[str, str] = {
    "institution_name": "Název instituce",
    "institution_email": "Email instituce",
    "institution_phone": "Telefon instituce",
    "institution_address": "Adresa instituce",
    "program_name": "Název programu",
    "program_description": "Popis programu",
    "program_duration": "Délka programu (min)",
    "reservation_date": "Datum rezervace",
    "reservation_time": "Čas rezervace",
    "reservation_id": "ID rezervace",
    "teacher_name": "Jméno učitele/kontaktu",
    "teacher_email": "Email učitele",
    "teacher_phone": "Telefon učitele",
    "school_name": "Název školy",
    "children_count": "Počet dětí/žáků",
    "teachers_count": "Počet pedagogů",
    "special_requirements": "Speciální požadavky",
    "user_name": "Jméno uživatele",
    "user_email": "Email uživatele",
    "reset_link": "Odkaz pro reset hesla",
    "activation_link": "Aktivační odkaz",
    "cancellation_reason": "Důvod zrušení",
    "rejection_reason": "Důvod odmítnutí",
    "booking_url": "URL rezervačního systému",
    "dashboard_url": "URL administrace",
}
