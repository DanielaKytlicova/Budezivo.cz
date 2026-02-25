"""
Payment routes.
Uses Supabase (PostgreSQL) for database operations.
"""
import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import PaymentSessionCreate
from core.config import STRIPE_API_KEY, PACKAGE_PRICES
from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import PaymentRepositorySupabase
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest
)

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = logging.getLogger(__name__)


@router.post("/create-session")
async def create_payment_session(
    payment_data: PaymentSessionCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create Stripe checkout session."""
    if payment_data.package not in PACKAGE_PRICES:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    amount = PACKAGE_PRICES[payment_data.package][payment_data.billing_cycle]
    
    # Get origin from request
    origin = str(request.base_url).rstrip('/')
    success_url = f"{origin}/admin/plan/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/admin/plan"
    
    # Initialize Stripe checkout
    webhook_url = f"{origin}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    # Create checkout session
    checkout_request = CheckoutSessionRequest(
        amount=amount,
        currency="czk",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "institution_id": current_user["institution_id"],
            "user_id": current_user["user_id"],
            "package": payment_data.package,
            "billing_cycle": payment_data.billing_cycle
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    payment_repo = PaymentRepositorySupabase(db)
    await payment_repo.create({
        "institution_id": current_user["institution_id"],
        "user_id": current_user["user_id"],
        "session_id": session.session_id,
        "amount": amount,
        "currency": "czk",
        "package": payment_data.package,
        "status": "pending",
        "payment_status": "initiated",
    })
    
    return {"url": session.url, "session_id": session.session_id}


@router.get("/status/{session_id}")
async def get_payment_status(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment status."""
    payment_repo = PaymentRepositorySupabase(db)
    
    # Check transaction
    transaction = await payment_repo.find_by_session(
        session_id,
        current_user["institution_id"]
    )
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # If already paid, return immediately
    if transaction["payment_status"] == "paid":
        return transaction
    
    # Initialize Stripe checkout
    webhook_url = f"{os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    # Get checkout status
    checkout_status = await stripe_checkout.get_checkout_status(session_id)
    
    # Update transaction
    await payment_repo.update_status(
        session_id,
        checkout_status.status,
        checkout_status.payment_status
    )
    
    transaction["status"] = checkout_status.status
    transaction["payment_status"] = checkout_status.payment_status
    
    return transaction


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook."""
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    webhook_url = f"{str(request.base_url).rstrip('/')}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Update transaction
        payment_repo = PaymentRepositorySupabase(db)
        await payment_repo.update_status(
            webhook_response.session_id,
            webhook_response.event_type,
            webhook_response.payment_status
        )
        
        logger.info(f"Webhook processed: {webhook_response.event_type}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
