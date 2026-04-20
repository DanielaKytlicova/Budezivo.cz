"""
Payment gateway abstraction for event payments.

Supports pluggable providers (Comgate now, GoPay in the future).
Per-institution credentials resolved via InstitutionPaymentSettings.

Key concepts:
- `provider`: 'comgate' / 'gopay' / None (disabled)
- `mode`: 'mock' (no keys, internal test page) / 'test' (sandbox) / 'live' (production)
- Webhook is source of truth; return URL only provides UX feedback.
"""
from .base import PaymentGatewayBase, PaymentInitResult, GatewayMode
from .factory import get_gateway_for_institution

__all__ = [
    "PaymentGatewayBase",
    "PaymentInitResult",
    "GatewayMode",
    "get_gateway_for_institution",
]
