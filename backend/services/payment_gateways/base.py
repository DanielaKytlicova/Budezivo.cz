"""Abstract payment-gateway base class."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GatewayMode(str, Enum):
    MOCK = "mock"   # No real keys; internal simulator page
    TEST = "test"   # Sandbox keys against provider
    LIVE = "live"   # Production keys


@dataclass
class PaymentInitResult:
    """Outcome of initiating a payment."""
    ok: bool
    redirect_url: Optional[str] = None
    transaction_id: Optional[str] = None  # Provider's transId if already known
    error: Optional[str] = None
    mode: GatewayMode = GatewayMode.MOCK
    raw: dict = field(default_factory=dict)


@dataclass
class PaymentStatus:
    """Normalised status from a provider."""
    paid: bool
    pending: bool
    failed: bool
    raw_status: str
    transaction_id: Optional[str] = None


class PaymentGatewayBase(ABC):
    """Base interface every payment provider must implement."""

    provider_key: str = "base"

    def __init__(self, merchant_id: str, secret: str, mode: GatewayMode):
        self.merchant_id = merchant_id
        self.secret = secret
        self.mode = mode

    @abstractmethod
    async def initiate(
        self,
        *,
        amount_czk: float,
        variable_symbol: str,
        description: str,
        ref_id: str,
        return_url: str,
        webhook_url: str,
        customer_email: Optional[str] = None,
        language: str = "cs",
    ) -> PaymentInitResult:
        """Create a payment session and return a redirect URL."""
        ...

    @abstractmethod
    async def parse_webhook(self, payload: dict) -> PaymentStatus:
        """Parse and authenticate a webhook notification."""
        ...

    @abstractmethod
    async def query_status(self, transaction_id: str) -> PaymentStatus:
        """Query the provider for the current payment status (fallback)."""
        ...
