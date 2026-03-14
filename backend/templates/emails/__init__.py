# Email templates module
from .templates import (
    get_template,
    get_available_templates,
    TEMPLATE_REGISTRY,
    # Account templates
    user_registration_confirmation,
    account_activation,
    password_reset,
    password_changed,
    # Reservation templates
    reservation_created_teacher,
    reservation_created_institution,
    reservation_confirmed,
    reservation_rejected,
    reservation_updated,
    reservation_cancelled,
    # Reminder templates
    reservation_reminder_teacher,
    reservation_reminder_institution,
    # Admin templates
    new_institution_registration,
)

__all__ = [
    "get_template",
    "get_available_templates",
    "TEMPLATE_REGISTRY",
    "user_registration_confirmation",
    "account_activation", 
    "password_reset",
    "password_changed",
    "reservation_created_teacher",
    "reservation_created_institution",
    "reservation_confirmed",
    "reservation_rejected",
    "reservation_updated",
    "reservation_cancelled",
    "reservation_reminder_teacher",
    "reservation_reminder_institution",
    "new_institution_registration",
]
