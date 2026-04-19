"""
Billing provider abstraction — supports manual, Fakturoid, future Stripe.
"""
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import BillingOrder, Institution
from database.supabase_repositories import InstitutionRepositorySupabase
from services.plan_service import PLAN_LIMITS, PLAN_LABELS

logger = logging.getLogger(__name__)


class BillingProviderInterface(ABC):
    """Abstract billing provider. Implement for each payment system."""

    @abstractmethod
    async def create_invoice(self, db: AsyncSession, order: BillingOrder) -> dict:
        """Create invoice in external system. Return {invoice_id, url}."""
        ...

    @abstractmethod
    async def check_payment_status(self, db: AsyncSession, order: BillingOrder) -> str:
        """Check payment status. Return 'paid', 'pending', 'failed', 'cancelled'."""
        ...

    @abstractmethod
    async def handle_webhook(self, db: AsyncSession, payload: dict) -> Optional[str]:
        """Process webhook from billing provider. Return order_id if matched."""
        ...


class ManualBillingProvider(BillingProviderInterface):
    """Manual billing — admin confirms payment manually."""

    async def create_invoice(self, db: AsyncSession, order: BillingOrder) -> dict:
        return {"invoice_id": None, "url": None, "note": "Manuální fakturace"}

    async def check_payment_status(self, db: AsyncSession, order: BillingOrder) -> str:
        return order.status

    async def handle_webhook(self, db: AsyncSession, payload: dict) -> Optional[str]:
        return None


class FakturoidBillingProvider(BillingProviderInterface):
    """Fakturoid integration — placeholder for future implementation."""

    async def create_invoice(self, db: AsyncSession, order: BillingOrder) -> dict:
        # TODO: Implement Fakturoid API call
        logger.info(f"Fakturoid: would create invoice for order {order.id}")
        return {"invoice_id": None, "url": None, "note": "Fakturoid integration pending"}

    async def check_payment_status(self, db: AsyncSession, order: BillingOrder) -> str:
        # TODO: Query Fakturoid API for payment status
        return order.status

    async def handle_webhook(self, db: AsyncSession, payload: dict) -> Optional[str]:
        # TODO: Parse Fakturoid webhook, match to order
        return None


# Provider registry
BILLING_PROVIDERS = {
    "manual": ManualBillingProvider(),
    "fakturoid": FakturoidBillingProvider(),
}


def get_billing_provider(provider_name: str) -> BillingProviderInterface:
    return BILLING_PROVIDERS.get(provider_name, BILLING_PROVIDERS["manual"])


async def create_billing_order(
    db: AsyncSession,
    institution_id: str,
    requested_plan: str,
    provider: str = "manual",
    amount: int = 0,
    currency: str = "CZK",
    created_by: str = None,
    note: str = None,
) -> dict:
    """Create a billing order and optionally trigger invoice creation."""
    order = BillingOrder(
        institution_id=institution_id,
        requested_plan_type=requested_plan,
        status="pending",
        provider=provider,
        amount=amount,
        currency=currency,
        created_by=uuid.UUID(created_by) if created_by else None,
        note=note,
    )
    db.add(order)
    await db.flush()

    # Try to create invoice via provider
    bp = get_billing_provider(provider)
    invoice_result = await bp.create_invoice(db, order)
    if invoice_result.get("invoice_id"):
        order.provider_invoice_id = invoice_result["invoice_id"]

    await db.commit()

    return {
        "order_id": str(order.id),
        "status": order.status,
        "provider": order.provider,
        "invoice_id": order.provider_invoice_id,
    }


async def confirm_billing_order(db: AsyncSession, order_id: str, confirmed_by: str = "payment") -> dict:
    """Confirm payment for a billing order and activate the plan.
    Idempotent — does not activate twice.
    """
    result = await db.execute(
        select(BillingOrder).where(BillingOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        return {"error": "Order not found"}

    if order.status == "paid":
        return {"message": "Already paid", "order_id": str(order.id)}

    now = datetime.now(timezone.utc)

    # Update order
    order.status = "paid"
    order.paid_at = now

    # Activate plan
    inst_repo = InstitutionRepositorySupabase(db)
    limits = PLAN_LIMITS.get(order.requested_plan_type, PLAN_LIMITS["free"])

    await inst_repo.update(str(order.institution_id), {
        "plan": order.requested_plan_type,
        "plan_status": "active",
        "plan_activated_by": confirmed_by,
        "plan_activated_at": now,
        "plan_updated_at": now,
        "requested_plan_type": None,
        "programs_limit": limits["programs_limit"],
        "bookings_monthly_limit": limits["bookings_monthly_limit"],
    })

    await db.commit()

    logger.info(f"Billing order {order_id} confirmed. Plan {order.requested_plan_type} activated for institution {order.institution_id}")

    return {
        "message": f"Plán {PLAN_LABELS.get(order.requested_plan_type, order.requested_plan_type)} aktivován",
        "order_id": str(order.id),
        "plan": order.requested_plan_type,
    }
