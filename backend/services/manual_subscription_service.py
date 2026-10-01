"""Validation helpers for manually maintained subscription terms."""

from datetime import datetime
from typing import Optional


ALLOWED_BILLING_CYCLES = {None, "monthly", "yearly", "one_off"}
ALLOWED_RENEWAL_MODES = {"manual", "prior_consent", "new_consent"}
ALLOWED_CONSENT_STATES = {
    "pending", "accepted_in_app", "accepted_by_email", "not_required", "declined",
}
ALLOWED_PAYMENT_STATES = {
    "not_invoiced", "invoiced", "partially_paid", "paid", "overdue",
    "cancelled", "manual_review", "free",
}


def validate_manual_subscription(
    *,
    price_amount: Optional[int],
    amount_paid: int,
    currency: str,
    billing_cycle: Optional[str],
    renewal_mode: str,
    consent_status: str,
    payment_status: str,
    due_days: int,
    period_start: Optional[datetime],
    period_end: Optional[datetime],
    billing_email: Optional[str],
    copy_email: Optional[str],
) -> None:
    """Raise ValueError when manually entered terms are inconsistent."""
    if price_amount is not None and price_amount < 0:
        raise ValueError("Cena nesmí být záporná")
    if amount_paid < 0:
        raise ValueError("Uhrazená částka nesmí být záporná")
    if currency != "CZK":
        raise ValueError("V první verzi je podporována pouze měna CZK")
    if billing_cycle not in ALLOWED_BILLING_CYCLES:
        raise ValueError("Neplatná periodicita")
    if renewal_mode not in ALLOWED_RENEWAL_MODES:
        raise ValueError("Neplatný režim obnovy")
    if consent_status not in ALLOWED_CONSENT_STATES:
        raise ValueError("Neplatný stav souhlasu")
    if payment_status not in ALLOWED_PAYMENT_STATES:
        raise ValueError("Neplatný stav platby")
    if not 1 <= due_days <= 365:
        raise ValueError("Splatnost musí být 1 až 365 dní")
    if period_start and period_end and period_end <= period_start:
        raise ValueError("Konec období musí být po jeho začátku")
    for email in (billing_email, copy_email):
        if email and ("@" not in email or email.startswith("@") or email.endswith("@")):
            raise ValueError("Neplatná e-mailová adresa")
