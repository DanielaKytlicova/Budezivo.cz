"""
Centralized subscription plan & feature gating for Budeživo.cz.

Plans: free, start, pro, pro_plus
Status: inactive, pending, active, expired

NEVER trust frontend for plan access — ALWAYS validate in backend.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---- Plan definitions ----

PLAN_ORDER = ["free", "start", "pro", "pro_plus"]

PLAN_LIMITS = {
    "free": {
        "programs_limit": 3,
        "bookings_monthly_limit": 50,
    },
    "start": {
        "programs_limit": 10,
        "bookings_monthly_limit": 200,
    },
    "pro": {
        "programs_limit": -1,  # unlimited
        "bookings_monthly_limit": -1,
    },
    "pro_plus": {
        "programs_limit": -1,
        "bookings_monthly_limit": -1,
    },
}

# Features available per plan (cumulative — higher plans include lower plan features)
PLAN_FEATURES = {
    "free": {
        "basic_bookings",
        "basic_calendar",
        "basic_schools_crm",
        "basic_feedback",
        "basic_statistics",
    },
    "start": {
        "basic_bookings",
        "basic_calendar",
        "basic_schools_crm",
        "basic_feedback",
        "basic_statistics",
        "csv_export",
        "school_import",
        "advanced_statistics",
        "custom_email_templates",
        "waitlist",
    },
    "pro": {
        "basic_bookings",
        "basic_calendar",
        "basic_schools_crm",
        "basic_feedback",
        "basic_statistics",
        "csv_export",
        "school_import",
        "advanced_statistics",
        "custom_email_templates",
        "waitlist",
        "bulk_email",
        "mailings",
        "collision_system",
        "lecturer_management",
        "room_management",
        "feedback_custom_questions",
        "unified_availability",
        "outlook_integration",
        "audit_log",
    },
    "pro_plus": {
        "basic_bookings",
        "basic_calendar",
        "basic_schools_crm",
        "basic_feedback",
        "basic_statistics",
        "csv_export",
        "school_import",
        "advanced_statistics",
        "custom_email_templates",
        "waitlist",
        "bulk_email",
        "mailings",
        "collision_system",
        "lecturer_management",
        "room_management",
        "feedback_custom_questions",
        "unified_availability",
        "outlook_integration",
        "audit_log",
        "events_module",
        "payment_settings",
        "api_access",
        "white_label",
        "priority_support",
    },
}

# Human-readable plan names
PLAN_LABELS = {
    "free": "Free",
    "start": "Start",
    "pro": "PRO",
    "pro_plus": "PRO+",
}

# Human-readable feature names (for UI)
FEATURE_LABELS = {
    "csv_export": "CSV/XLSX export",
    "school_import": "Import škol",
    "advanced_statistics": "Pokročilé statistiky",
    "custom_email_templates": "Vlastní emailové šablony",
    "waitlist": "Hlídání termínů (Waitlist)",
    "bulk_email": "Hromadné emaily",
    "mailings": "Propagační mailingy",
    "collision_system": "Kolizní systém",
    "lecturer_management": "Správa lektorů",
    "room_management": "Správa místností",
    "feedback_custom_questions": "Vlastní otázky zpětné vazby",
    "unified_availability": "Sjednocená dostupnost",
    "outlook_integration": "Outlook integrace",
    "audit_log": "Audit log",
    "events_module": "Události a přihlášky",
    "payment_settings": "Platební nastavení",
    "api_access": "API přístup",
    "white_label": "White label",
    "priority_support": "Prioritní podpora",
}

# Which plan is required for each feature (minimum)
FEATURE_MIN_PLAN = {}
for feature in FEATURE_LABELS:
    for plan in PLAN_ORDER:
        if feature in PLAN_FEATURES.get(plan, set()):
            FEATURE_MIN_PLAN[feature] = plan
            break


def has_feature_access(plan: str, plan_status: str, feature_key: str) -> bool:
    """Check if a plan+status combination grants access to a feature.
    
    CRITICAL: This is the single source of truth for feature access.
    """
    if plan_status != "active":
        # Inactive/pending/expired plans only get free features
        plan = "free"
    
    features = PLAN_FEATURES.get(plan, PLAN_FEATURES["free"])
    return feature_key in features


def get_plan_features(plan: str, plan_status: str) -> dict:
    """Get all features and their access status for a given plan."""
    effective_plan = plan if plan_status == "active" else "free"
    features = PLAN_FEATURES.get(effective_plan, PLAN_FEATURES["free"])
    
    result = {}
    for feature_key, label in FEATURE_LABELS.items():
        has_access = feature_key in features
        min_plan = FEATURE_MIN_PLAN.get(feature_key, "start")
        result[feature_key] = {
            "has_access": has_access,
            "label": label,
            "min_plan": min_plan,
            "min_plan_label": PLAN_LABELS.get(min_plan, min_plan),
        }
    return result


def get_plan_limits(plan: str, plan_status: str) -> dict:
    """Get resource limits for a given plan."""
    effective_plan = plan if plan_status == "active" else "free"
    return PLAN_LIMITS.get(effective_plan, PLAN_LIMITS["free"])


def get_minimum_plan_for_feature(feature_key: str) -> Optional[str]:
    """Get the minimum plan required for a feature."""
    return FEATURE_MIN_PLAN.get(feature_key)
