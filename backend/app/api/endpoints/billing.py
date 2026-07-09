"""Billing endpoints (issue #221): start a Stripe Checkout upgrade.

The plan itself is NEVER changed here — the #220 webhook is the only writer
(the client redirect back from Stripe is untrusted). This endpoint only
establishes the user<->Stripe linkage the webhook reconciles on.
"""

import asyncio
import logging
from typing import Dict, Literal

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_rate_limiter
from app.core.config import settings
from app.core.security import get_current_user_from_session
from app.db.user import update_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Only paying plans block a new checkout — "restricted" users (lapsed/revoked)
# are deliberately allowed through as the re-upgrade path.
PAID_PLANS = frozenset({"pro"})


class CheckoutRequest(BaseModel):
    plan: Literal["pro"] = "pro"


class CheckoutResponse(BaseModel):
    url: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    body: CheckoutRequest,
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=5, window=300)),
):
    """Create a Stripe Checkout session for upgrading to a paid plan."""
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRICE_ID_PRO:
        # Fail closed, mirroring the webhook: never talk to Stripe half-configured.
        raise HTTPException(status_code=503, detail="Stripe checkout is not configured")

    if current_user.get("plan") in PAID_PLANS:
        raise HTTPException(status_code=409, detail="You are already on a paid plan")

    auth_id = current_user["auth_id"]
    frontend_base = settings.BETTER_AUTH_URL.rstrip("/")

    try:
        # The Stripe SDK is synchronous/blocking — keep it off the event loop (#175).
        customer_id = current_user.get("stripe_customer_id")
        if not customer_id:
            customer = await asyncio.to_thread(
                stripe.Customer.create,
                api_key=settings.STRIPE_SECRET_KEY,
                email=current_user.get("email"),
                metadata={"auth_id": auth_id},
                # Same key => Stripe returns the same customer for ~24h, so a
                # double-click race can't mint two customers for one user.
                idempotency_key=f"checkout-customer-{auth_id}",
            )
            customer_id = customer.id
            await update_user(
                auth_id, {"stripe_customer_id": customer_id}, actor_id=auth_id
            )

        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            api_key=settings.STRIPE_SECRET_KEY,
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": settings.STRIPE_PRICE_ID_PRO, "quantity": 1}],
            # client_reference_id + subscription metadata are what the #220
            # webhook uses to find this user before the customer id is linked.
            client_reference_id=auth_id,
            subscription_data={"metadata": {"auth_id": auth_id}},
            success_url=f"{frontend_base}/dashboard/settings?checkout=success",
            cancel_url=f"{frontend_base}/dashboard/settings?checkout=cancel",
        )
    except stripe.StripeError:
        logger.error("Stripe checkout failed for user %s", auth_id, exc_info=True)
        raise HTTPException(
            status_code=502, detail="Payment provider error — please try again"
        )

    return CheckoutResponse(url=session.url)
