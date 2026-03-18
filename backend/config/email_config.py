"""
Email Configuration for Budeživo.cz
Centralized email settings and sender addresses.

IMPORTANT: All environment variables are loaded at RUNTIME using getter functions
to ensure compatibility with production environments where env vars may be set
after module import.
"""
import os
import logging
from enum import Enum
from typing import Dict, Any
from pathlib import Path

# Try to load .env file (for local development only)
# In production (Railway, etc.), env vars are set by the platform
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

logger = logging.getLogger(__name__)


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
    
    # Contact
    CONTACT_FORM_SUBMISSION = "contact_form_submission"


class SenderType(str, Enum):
    """Sender address types."""
    NO_REPLY = "no_reply"
    RESERVATIONS = "reservations"
    ACCOUNTS = "accounts"


# ============ RUNTIME GETTERS ============
# These functions fetch values at runtime, not import time

def get_resend_api_key() -> str | None:
    """Get RESEND_API_KEY at runtime."""
    return os.environ.get("RESEND_API_KEY")


def get_sender_email() -> str:
    """Get SENDER_EMAIL at runtime with fallback."""
    return os.environ.get("SENDER_EMAIL", "noreply@budezivo.cz")


def get_env() -> str:
    """Get current environment."""
    return os.environ.get("ENV", "production")


def is_development() -> bool:
    """Check if running in development mode."""
    return get_env() == "development"


def get_sender_addresses() -> Dict[SenderType, str]:
    """Get sender addresses based on environment."""
    if is_development():
        dev_email = os.environ.get("DEV_EMAIL", "dev@budezivo.cz")
        return {
            SenderType.NO_REPLY: f"Budeživo <{dev_email}>",
            SenderType.RESERVATIONS: f"Rezervace Budeživo <{dev_email}>",
            SenderType.ACCOUNTS: f"Účty Budeživo <{dev_email}>",
        }
    else:
        return {
            SenderType.NO_REPLY: "Budeživo <noreply@budezivo.cz>",
            SenderType.RESERVATIONS: "Rezervace Budeživo <reservations@budezivo.cz>",
            SenderType.ACCOUNTS: "Účty Budeživo <accounts@budezivo.cz>",
        }


# ============ BACKWARDS COMPATIBILITY ============
# These are kept for modules that import them directly
# They will be evaluated at import time but should work in most cases

def _get_resend_api_key_compat():
    key = os.environ.get("RESEND_API_KEY")
    if key:
        logger.debug(f"RESEND_API_KEY loaded: {key[:8]}...")
    else:
        logger.warning("RESEND_API_KEY not found in environment")
    return key

RESEND_API_KEY = _get_resend_api_key_compat()
ENV = get_env()
IS_DEVELOPMENT = is_development()
SENDER_EMAIL = get_sender_email()
SENDER_ADDRESSES = get_sender_addresses()


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
    
    # Contact form
    EmailType.CONTACT_FORM_SUBMISSION: SenderType.NO_REPLY,
}


def get_sender_for_email_type(email_type: EmailType) -> str:
    """Get the appropriate sender address for an email type."""
    sender_type = EMAIL_TYPE_SENDERS.get(email_type, SenderType.NO_REPLY)
    addresses = get_sender_addresses()
    return addresses.get(sender_type, get_sender_email())


def get_dev_recipient(original_email: str) -> str:
    """In development mode, redirect all emails to dev email."""
    if is_development():
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
