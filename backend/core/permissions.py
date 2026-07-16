"""Centralised role → capability rules (single readable permission layer).

Backend is the source of truth: hiding UI buttons is NOT sufficient, every
capability is enforced here. All checks are tenant-scoped by the caller using
current_user["institution_id"]; these helpers only gate by ROLE.

Roles:
  admin, spravce   – full management (config, team, billing, payments settings)
  produkcni        – production planning: calendar/reservations + block management;
                     NO payments/sensitive data, NO roles/config/billing
  ucetni           – accounting: event applications + payments (mark QR/cash paid);
                     NO programs, NO calendar availability, NO team/config
  pokladni         – legacy cashier (kept for backward compatibility ~ ucetni subset)
  edukator, lektor – program/reservation staff (existing behaviour)
  staff, viewer    – limited/read
"""
from fastapi import Depends, HTTPException

from core.security import get_current_user

# Institution configuration, team & role management, billing, payment SETTINGS
MANAGEMENT_ROLES = {"admin", "spravce"}

# Creating/editing programs and one-off events
PROGRAM_EDIT_ROLES = {"admin", "spravce", "edukator"}
EVENT_MANAGE_ROLES = {"admin", "spravce"}

# Accounting: view event applications & payments, mark manual payments paid.
# Deliberately EXCLUDES produkcni (GDPR: no access to payment/applicant data).
PAYMENTS_ROLES = {"admin", "spravce", "ucetni", "pokladni"}
MARK_PAID_ROLES = {"admin", "spravce", "ucetni", "pokladni"}

# Institution-wide block management (availability / program / room blocks).
# Deliberately EXCLUDES ucetni.
BLOCK_MANAGE_ROLES = {"admin", "spravce", "produkcni"}


def ensure_role(user: dict, allowed: set, message: str = "Nemáte oprávnění k této akci.") -> None:
    if user.get("role") not in allowed:
        raise HTTPException(status_code=403, detail=message)


def require_roles(allowed: set, message: str = "Nemáte oprávnění k této akci."):
    """FastAPI dependency factory enforcing that the caller has one of `allowed`."""
    async def _dep(current_user: dict = Depends(get_current_user)):
        ensure_role(current_user, allowed, message)
        return current_user
    return _dep
