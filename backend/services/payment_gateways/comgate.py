"""Comgate payment gateway implementation.

Comgate REST API v1.0:
- POST https://payments.comgate.cz/v1.0/create (form-urlencoded)
- Returns: code=0&message=OK&transId=ABCD-1234-XYZW&redirect=https://...
- Webhook: Comgate POSTs form-urlencoded data to our webhook URL including
  merchant + secret (secret authenticates the call).
- Reply to webhook with "code=0&message=OK" as plain text.

The `mode` controls behaviour:
- MOCK: no HTTP call at all. Returns a redirect to our internal mock page,
        letting the main agent / admin click "Simulate success" to trigger
        the webhook logic locally. Safe when merchant credentials are placeholder.
- TEST: calls Comgate sandbox API with `test=true`.
- LIVE: calls Comgate production API with `test=false`.
"""
import hmac
import logging
import uuid
from typing import Optional
from urllib.parse import urlencode, parse_qs

import httpx

from .base import PaymentGatewayBase, PaymentInitResult, PaymentStatus, GatewayMode

logger = logging.getLogger(__name__)

COMGATE_BASE_URL = "https://payments.comgate.cz/v1.0"


class ComgateGateway(PaymentGatewayBase):
    provider_key = "comgate"

    def _is_configured(self) -> bool:
        return bool(self.merchant_id) and bool(self.secret)

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
        amount_cents = int(round(amount_czk * 100))

        if self.mode == GatewayMode.MOCK or not self._is_configured():
            # Mock mode: synthesize a redirect URL pointing to our internal sim page.
            fake_trans = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
            # Derive base URL from webhook_url (which always contains /api/)
            base = webhook_url.split('/api/')[0] if '/api/' in webhook_url else webhook_url
            redirect_url = (
                f"{base}/payment/mock"
                f"?vs={variable_symbol}&ref={ref_id}&trans={fake_trans}&return={return_url}"
            )
            logger.info(f"[Comgate:mock] amount={amount_czk} VS={variable_symbol} → {fake_trans}")
            return PaymentInitResult(
                ok=True,
                redirect_url=redirect_url,
                transaction_id=fake_trans,
                mode=GatewayMode.MOCK,
                raw={"mock": True},
            )

        payload = {
            "merchant": self.merchant_id,
            "secret": self.secret,
            "test": "true" if self.mode == GatewayMode.TEST else "false",
            "price": str(amount_cents),
            "curr": "CZK",
            "label": (description or "Platba")[:16],
            "refId": ref_id[:40],
            "method": "ALL",
            "prepareOnly": "true",
            "email": customer_email or "",
            "lang": language,
            "country": "CZ",
            "variableSymbol": variable_symbol,
            "url_paid": f"{return_url}?status=paid",
            "url_cancelled": f"{return_url}?status=cancelled",
            "url_notify": webhook_url,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{COMGATE_BASE_URL}/create",
                    content=urlencode(payload),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            parsed = {k: (v[0] if v else "") for k, v in parse_qs(resp.text).items()}
            code = parsed.get("code", "")
            if code == "0":
                return PaymentInitResult(
                    ok=True,
                    redirect_url=parsed.get("redirect"),
                    transaction_id=parsed.get("transId"),
                    mode=self.mode,
                    raw=parsed,
                )
            logger.error(f"[Comgate] create failed code={code} msg={parsed.get('message')}")
            return PaymentInitResult(
                ok=False,
                error=parsed.get("message", f"Comgate error code {code}"),
                mode=self.mode,
                raw=parsed,
            )
        except Exception as e:
            logger.exception(f"[Comgate] create exception: {e}")
            return PaymentInitResult(ok=False, error=str(e), mode=self.mode)

    async def parse_webhook(self, payload: dict) -> PaymentStatus:
        """Comgate webhook: form-urlencoded with merchant+secret for auth,
        plus transId, refId, status (PAID/CANCELLED/PENDING), price, etc.

        `secret` field authenticates the webhook — must match our configured secret.
        Hardened: refuses webhooks in TEST/LIVE mode when gateway is not configured
        (prevents spoofed "paid" notifications) and uses constant-time comparison.
        """
        provided_merchant = (payload.get("merchant") or "").strip()
        provided_secret = (payload.get("secret") or "").strip()
        if self.mode != GatewayMode.MOCK:
            if not self._is_configured():
                raise ValueError("Comgate webhook received but gateway is not configured")
            expected_merchant = (self.merchant_id or "").strip()
            expected_secret = (self.secret or "").strip()
            merchant_ok = hmac.compare_digest(provided_merchant, expected_merchant)
            secret_ok = hmac.compare_digest(provided_secret, expected_secret)
            if not (merchant_ok and secret_ok):
                raise ValueError("Invalid Comgate webhook signature")
        raw = (payload.get("status") or "").upper()
        return PaymentStatus(
            paid=raw == "PAID",
            pending=raw == "PENDING",
            failed=raw in ("CANCELLED", "CANCELED", "FAILED"),
            raw_status=raw,
            transaction_id=payload.get("transId"),
        )

    async def query_status(self, transaction_id: str) -> PaymentStatus:
        if self.mode == GatewayMode.MOCK or not self._is_configured():
            return PaymentStatus(paid=False, pending=True, failed=False, raw_status="PENDING", transaction_id=transaction_id)
        payload = {
            "merchant": self.merchant_id,
            "secret": self.secret,
            "transId": transaction_id,
            "test": "true" if self.mode == GatewayMode.TEST else "false",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{COMGATE_BASE_URL}/status",
                    content=urlencode(payload),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            parsed = {k: (v[0] if v else "") for k, v in parse_qs(resp.text).items()}
            raw = (parsed.get("status") or "").upper()
            return PaymentStatus(
                paid=raw == "PAID",
                pending=raw == "PENDING",
                failed=raw in ("CANCELLED", "CANCELED", "FAILED"),
                raw_status=raw,
                transaction_id=transaction_id,
            )
        except Exception as e:
            logger.exception(f"[Comgate] status exception: {e}")
            return PaymentStatus(paid=False, pending=True, failed=False, raw_status="UNKNOWN", transaction_id=transaction_id)
