"""Canonical institution notification preferences.

Keep defaults and legacy-data normalization outside the routes so every email
producer makes the same decision as the Settings UI.
"""

CUSTOMER_NOTIF_KEYS = {
    "reservation_created": True,
    "reservation_confirmed": True,
    "reservation_cancelled": True,
    "visit_reminder": True,
    # A receipt for a one-off event registration is transactional and mandatory.
    "event_registration_received": True,
    "event_registration_confirmed": True,
    "event_registration_cancelled": True,
}

ADMIN_NOTIF_KEYS = {
    "new_reservation": True,
    "reservation_cancelled": False,
    "event_capacity_reached": False,
    "new_event_registration": False,
    "integration_error": False,
}

ADMIN_RECIPIENT_ROLES = {"admin", "spravce"}
NOTIF_MANAGE_ROLES = {"admin", "spravce"}


def normalize_notifications(stored: dict | None) -> dict:
    """Merge stored and legacy values over safe canonical defaults."""
    stored = stored or {}
    customer = {**CUSTOMER_NOTIF_KEYS}
    admin = {**ADMIN_NOTIF_KEYS}

    stored_customer = stored.get("customer") or {}
    stored_admin = stored.get("admin") or {}
    for key in customer:
        if isinstance(stored_customer.get(key), bool):
            customer[key] = stored_customer[key]
    for key in admin:
        if isinstance(stored_admin.get(key), bool):
            admin[key] = stored_admin[key]

    if "customer" not in stored and "confirmation" in stored:
        customer["reservation_confirmed"] = bool(stored.get("confirmation"))
    if "admin" not in stored:
        if "new_reservation" in stored:
            admin["new_reservation"] = bool(stored.get("new_reservation"))
        if "cancellation" in stored:
            admin["reservation_cancelled"] = bool(stored.get("cancellation"))

    recipients = stored_admin.get("recipient_user_ids")
    if not isinstance(recipients, list):
        recipients = []
    admin["recipient_user_ids"] = [str(value) for value in recipients]

    # This message is proof that a public registration was received. It must
    # never be disabled by stale or manually edited JSON.
    customer["event_registration_received"] = True
    return {"customer": customer, "admin": admin}
