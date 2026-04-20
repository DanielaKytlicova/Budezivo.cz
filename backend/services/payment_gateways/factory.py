"""Factory for payment gateway instances.

Resolves provider + credentials from InstitutionPaymentSettings and returns
the appropriate gateway instance in the correct mode.

Mode detection (per-institution):
- No `provider` OR no `gateway_api_key` → MOCK (local simulator page)
- `gateway_test_mode` truthy OR merchant id prefixed with 'TEST_' → TEST
- Otherwise → LIVE
"""
import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import InstitutionPaymentSettings
from .base import PaymentGatewayBase, GatewayMode
from .comgate import ComgateGateway

logger = logging.getLogger(__name__)


def _detect_mode(settings: Optional[InstitutionPaymentSettings]) -> GatewayMode:
    if not settings:
        return GatewayMode.MOCK
    merchant = (settings.gateway_api_key or "").strip()
    secret = (settings.gateway_secret or "").strip()
    if not merchant or not secret:
        return GatewayMode.MOCK
    # Convention for placeholder/test keys: prefix "TEST_"
    if merchant.upper().startswith("TEST_"):
        return GatewayMode.TEST
    return GatewayMode.LIVE


async def get_gateway_for_institution(
    db: AsyncSession,
    institution_id: str,
) -> tuple[Optional[PaymentGatewayBase], Optional[InstitutionPaymentSettings], GatewayMode]:
    """Return the (gateway, settings, mode) tuple for the institution.

    gateway may be None if no provider is configured (caller should use QR only).
    settings is always returned when present in DB.
    """
    inst_uuid = uuid.UUID(institution_id) if not isinstance(institution_id, uuid.UUID) else institution_id
    result = await db.execute(
        select(InstitutionPaymentSettings).where(InstitutionPaymentSettings.institution_id == inst_uuid)
    )
    settings = result.scalar_one_or_none()

    provider = (settings.provider or "").strip().lower() if settings else ""
    mode = _detect_mode(settings)

    if provider == "comgate":
        return ComgateGateway(
            merchant_id=settings.gateway_api_key or "",
            secret=settings.gateway_secret or "",
            mode=mode,
        ), settings, mode

    # Future: gopay etc.
    return None, settings, mode
