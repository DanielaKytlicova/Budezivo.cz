"""
Centralized subscription plan & feature gating for Budeživo.cz.

SINGLE SOURCE OF TRUTH for all plan logic.
Plans: free → start → pro → pro_plus (hierarchical / cumulative).

Architecture:
- Each feature has a `plan_level` (the minimum plan where it first appears).
- Higher plans automatically inherit ALL features from lower plans.
- UI reads from this config — never hardcoded.
- Backend enforces via `require_feature()` dependency.

NEVER trust frontend for plan access — ALWAYS validate in backend.
"""
import logging
from typing import Optional, List
from fastapi import HTTPException, Depends

logger = logging.getLogger(__name__)

# ============ Plan hierarchy ============

PLAN_ORDER = ["free", "start", "pro", "pro_plus"]

PLAN_LABELS = {
    "free": "Free",
    "start": "Start",
    "pro": "PRO",
    "pro_plus": "PRO+",
}

PLAN_LIMITS = {
    "free": {"programs_limit": 3, "bookings_monthly_limit": 50},
    "start": {"programs_limit": 10, "bookings_monthly_limit": 200},
    "pro": {"programs_limit": -1, "bookings_monthly_limit": 500},
    "pro_plus": {"programs_limit": -1, "bookings_monthly_limit": -1},
}

# ============ Feature definitions (with plan_level) ============
# Each feature belongs to ONE plan_level — the tier where it FIRST appears.
# Higher plans inherit it automatically.

FEATURES = [
    # --- START features (base) ---
    {"key": "reservations_basic",          "label": "Základní rezervační systém",         "plan_level": "start"},
    {"key": "program_management",          "label": "Správa programů",                    "plan_level": "start"},
    {"key": "calendar",                    "label": "Kalendář dostupnosti",               "plan_level": "start"},
    {"key": "basic_stats",                 "label": "Základní statistiky",                "plan_level": "start"},
    {"key": "branding",                    "label": "Branding instituce",                 "plan_level": "start"},
    {"key": "form_edit",                   "label": "Editace formulářů",                  "plan_level": "start"},
    {"key": "email_templates",             "label": "Emailové šablony",                   "plan_level": "start"},
    {"key": "availability_blocks",         "label": "Bloky dostupnosti",                  "plan_level": "start"},
    {"key": "contacts_from_reservations",  "label": "Získávání kontaktů z rezervací",     "plan_level": "start"},

    # --- PRO features (START + these) ---
    {"key": "parallel_programs",           "label": "Paralelní programy",                 "plan_level": "pro"},
    {"key": "advanced_stats",              "label": "Pokročilé statistiky",               "plan_level": "pro"},
    {"key": "data_export",                 "label": "Export dat (CSV/XLSX)",               "plan_level": "pro"},
    {"key": "mailing",                     "label": "Propagační mailing na školy",         "plan_level": "pro"},
    {"key": "utilization_overview",        "label": "Přehled vytíženosti",                "plan_level": "pro"},
    {"key": "waitlist",                    "label": "Náhradníci (Waitlist)",               "plan_level": "pro"},
    {"key": "events_basic",               "label": "Události (tábory, akce)",             "plan_level": "pro"},
    {"key": "collision_system",            "label": "Kolizní systém",                     "plan_level": "pro"},
    {"key": "feedback_custom_questions",   "label": "Vlastní otázky zpětné vazby",        "plan_level": "pro"},
    {"key": "audit_log",                   "label": "Audit log",                          "plan_level": "pro"},

    # --- PRO+ features (PRO + these) ---
    {"key": "events_payments",             "label": "Události vč. online plateb",         "plan_level": "pro_plus"},
    {"key": "payment_pairing",             "label": "Automatické párování plateb",         "plan_level": "pro_plus"},
    {"key": "unlimited_reservations",      "label": "Neomezené rezervace",                "plan_level": "pro_plus"},
    {"key": "api_access",                  "label": "API přístup",                        "plan_level": "pro_plus"},
    {"key": "outlook_sync",               "label": "Outlook synchronizace",               "plan_level": "pro_plus"},
    {"key": "sla_support",                "label": "Prioritní podpora (SLA)",              "plan_level": "pro_plus"},
    {"key": "auto_confirm_paid",          "label": "Automatické potvrzení po zaplacení",   "plan_level": "pro_plus"},
]

# ============ Derived structures (computed once at import) ============

# feature key → feature dict
FEATURE_MAP = {f["key"]: f for f in FEATURES}

# feature key → label
FEATURE_LABELS = {f["key"]: f["label"] for f in FEATURES}

# feature key → minimum plan
FEATURE_MIN_PLAN = {f["key"]: f["plan_level"] for f in FEATURES}

# plan → set of all feature keys (cumulative)
def _build_plan_features():
    """Build cumulative feature sets: higher plans include all lower-plan features."""
    result = {"free": set()}
    for plan in PLAN_ORDER:
        if plan == "free":
            continue
        # Start with previous plan's features
        prev_idx = PLAN_ORDER.index(plan) - 1
        prev_plan = PLAN_ORDER[prev_idx]
        inherited = set(result.get(prev_plan, set()))
        # Add features that belong to this plan level
        own = {f["key"] for f in FEATURES if f["plan_level"] == plan}
        result[plan] = inherited | own
    return result

PLAN_FEATURES = _build_plan_features()

# plan → list of features ADDED at this tier (delta, no inherited)
def _build_plan_deltas():
    result = {}
    for plan in PLAN_ORDER:
        if plan == "free":
            result[plan] = []
            continue
        result[plan] = [f for f in FEATURES if f["plan_level"] == plan]
    return result

PLAN_DELTAS = _build_plan_deltas()


# ============ Access checking ============

def has_feature_access(plan: str, plan_status: str, feature_key: str) -> bool:
    """SINGLE SOURCE OF TRUTH for feature access."""
    if plan_status != "active":
        return feature_key in PLAN_FEATURES.get("free", set())
    return feature_key in PLAN_FEATURES.get(plan, PLAN_FEATURES.get("free", set()))


def get_plan_features_full(plan: str, plan_status: str) -> dict:
    """All features with access status for a given plan."""
    effective = plan if plan_status == "active" else "free"
    active_features = PLAN_FEATURES.get(effective, set())
    result = {}
    for f in FEATURES:
        result[f["key"]] = {
            "has_access": f["key"] in active_features,
            "label": f["label"],
            "plan_level": f["plan_level"],
            "plan_level_label": PLAN_LABELS.get(f["plan_level"], f["plan_level"]),
        }
    return result


def get_plan_limits(plan: str, plan_status: str) -> dict:
    effective = plan if plan_status == "active" else "free"
    return PLAN_LIMITS.get(effective, PLAN_LIMITS["free"])


def get_plan_hierarchy() -> list:
    """Return full plan hierarchy for UI rendering.
    Each plan has: own features (delta) + inherited label.
    No duplication. UI renders this directly.
    """
    plans = []
    for plan in PLAN_ORDER:
        if plan == "free":
            plans.append({
                "key": "free",
                "label": PLAN_LABELS["free"],
                "limits": PLAN_LIMITS["free"],
                "inherits_from": None,
                "own_features": [],
                "all_feature_keys": list(PLAN_FEATURES.get("free", set())),
            })
            continue

        prev_idx = PLAN_ORDER.index(plan) - 1
        prev_plan = PLAN_ORDER[prev_idx] if prev_idx >= 0 else None

        plans.append({
            "key": plan,
            "label": PLAN_LABELS[plan],
            "limits": PLAN_LIMITS[plan],
            "inherits_from": prev_plan,
            "inherits_from_label": PLAN_LABELS.get(prev_plan, "") if prev_plan and prev_plan != "free" else None,
            "own_features": [{"key": f["key"], "label": f["label"]} for f in PLAN_DELTAS[plan]],
            "all_feature_keys": list(PLAN_FEATURES.get(plan, set())),
        })
    return plans


def compute_plan_diff(from_plan: str, to_plan: str) -> dict:
    """Compute delta between two plans: gained and lost features."""
    from_features = PLAN_FEATURES.get(from_plan, set())
    to_features = PLAN_FEATURES.get(to_plan, set())

    gained = to_features - from_features
    lost = from_features - to_features

    return {
        "gained": [{"key": k, "label": FEATURE_LABELS.get(k, k)} for k in sorted(gained)],
        "lost": [{"key": k, "label": FEATURE_LABELS.get(k, k)} for k in sorted(lost)],
        "is_upgrade": PLAN_ORDER.index(to_plan) > PLAN_ORDER.index(from_plan) if to_plan in PLAN_ORDER and from_plan in PLAN_ORDER else False,
    }


# ============ FastAPI dependency for backend enforcement ============

def require_feature(feature_key: str):
    """FastAPI dependency that blocks access if institution lacks the feature.
    
    Usage:
        @router.get("/some-endpoint")
        async def endpoint(
            current_user = Depends(get_current_user),
            db = Depends(get_db),
            _guard = Depends(require_feature("mailing")),
        ):
    """
    from core.security import get_current_user
    from database.supabase import get_db
    from database.supabase_repositories import InstitutionRepositorySupabase

    async def _check(
        current_user: dict = Depends(get_current_user),
        db=Depends(get_db),
    ):
        inst_repo = InstitutionRepositorySupabase(db)
        inst = await inst_repo.find_by_id(current_user["institution_id"])
        if not inst:
            raise HTTPException(status_code=404, detail="Instituce nenalezena")

        plan = inst.get("plan", "free")
        plan_status = inst.get("plan_status", "active")

        if not has_feature_access(plan, plan_status, feature_key):
            min_plan = FEATURE_MIN_PLAN.get(feature_key, "start")
            raise HTTPException(
                status_code=403,
                detail=f"Tato funkce vyžaduje plán {PLAN_LABELS.get(min_plan, min_plan)}. Aktuální plán: {PLAN_LABELS.get(plan, plan)}."
            )

    return _check
