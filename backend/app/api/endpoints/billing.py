"""Billing endpoints: Stripe Checkout upgrade (#221) + billing portal (#222).

The plan itself is NEVER changed here — the #220 webhook is the only writer
(the client redirect back from Stripe is untrusted). This endpoint only
establishes the user<->Stripe linkage the webhook reconciles on.
"""

import asyncio
import logging
import threading
from typing import Dict, Literal, Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_rate_limiter
from app.core.config import settings
from app.core.entitlements import ai_quota_for_plan
from app.core.security import get_current_user_from_session
from app.db.user import update_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Only paying plans block a new checkout — "restricted" users (lapsed/revoked)
# are deliberately allowed through as the re-upgrade path.
PAID_PLANS = frozenset({"pro"})


class PlanQuota(BaseModel):
    """A ``None`` window is unlimited (disabled in settings, or quota off)."""

    daily: Optional[int]
    monthly: Optional[int]


@router.get("/quotas", response_model=Dict[str, PlanQuota])
async def get_plan_quotas(
    current_user: Dict = Depends(get_current_user_from_session),
):
    """AI-generation caps per plan: the one source the billing copy reads (#766)."""
    def window(limit: int) -> Optional[int]:
        # The enforcer treats <=0 as "window disabled"; never advertise it as 0.
        return limit if settings.AI_QUOTA_ENABLED and limit > 0 else None

    quotas = {plan: ai_quota_for_plan(plan) for plan in ("free", "pro")}
    return {
        plan: PlanQuota(daily=window(daily), monthly=window(monthly))
        for plan, (daily, monthly) in quotas.items()
    }


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
        # from None: the StripeError is already logged above; keep it out of the
        # sanitized 502's traceback chain.
        raise HTTPException(
            status_code=502, detail="Payment provider error — please try again"
        ) from None

    return CheckoutResponse(url=session.url)


# #771: the portal's behaviour is pinned in code, not in unversioned dashboard
# settings. Bump "portal_config_version" to roll out a changed Configuration:
# the old one stops matching the lookup, so a new one is created.
PORTAL_CONFIG_METADATA = {"app": "auto-author", "portal_config_version": "1"}
_portal_config_id: Optional[str] = None  # per-process cache; Stripe is the source of truth
# Serialises the cold-start lookup/create: Stripe answers a concurrent request
# carrying the same in-flight idempotency key with a 409, not the shared result.
_portal_config_lock = threading.Lock()


def _get_or_create_portal_config(api_key: str) -> str:
    """Return the id of our pinned portal Configuration, creating it if absent."""
    global _portal_config_id
    if _portal_config_id:
        return _portal_config_id
    with _portal_config_lock:
        if _portal_config_id:
            return _portal_config_id
        return _lookup_or_create_portal_config(api_key)


def _lookup_or_create_portal_config(api_key: str) -> str:
    global _portal_config_id
    existing = stripe.billing_portal.Configuration.list(
        api_key=api_key, active=True, limit=100
    )
    for cfg in existing.auto_paging_iter():
        meta = cfg.to_dict().get("metadata") or {}
        if all(meta.get(k) == v for k, v in PORTAL_CONFIG_METADATA.items()):
            _portal_config_id = cfg.id
            return cfg.id
    cfg = stripe.billing_portal.Configuration.create(
        api_key=api_key,
        # Fixed key: concurrent first calls collapse to one Configuration.
        idempotency_key=f"portal-config-v{PORTAL_CONFIG_METADATA['portal_config_version']}",
        metadata=PORTAL_CONFIG_METADATA,
        business_profile={"headline": "Manage your Auto Author subscription"},
        features={
            # at_period_end matches the #770 disclosure: access continues to the
            # end of the paid period, then the plan drops.
            "subscription_cancel": {"enabled": True, "mode": "at_period_end"},
            "payment_method_update": {"enabled": True},
            "invoice_history": {"enabled": True},
        },
    )
    _portal_config_id = cfg.id
    return cfg.id


class PortalResponse(BaseModel):
    url: str


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=5, window=300)),
):
    """Create a Stripe billing-portal session so a paying user can manage billing.

    Gated on having a Stripe customer, not on plan — a lapsed ("restricted")
    user still needs the portal to fix their payment method.
    """
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe billing is not configured")

    customer_id = current_user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=409,
            detail="No billing account yet — upgrade to a paid plan first",
        )

    frontend_base = settings.BETTER_AUTH_URL.rstrip("/")
    try:
        config_id = await asyncio.to_thread(
            _get_or_create_portal_config, settings.STRIPE_SECRET_KEY
        )
        session = await asyncio.to_thread(
            stripe.billing_portal.Session.create,
            api_key=settings.STRIPE_SECRET_KEY,
            customer=customer_id,
            configuration=config_id,
            return_url=f"{frontend_base}/dashboard/settings?tab=billing",
        )
    except stripe.StripeError:
        logger.error(
            "Stripe portal session failed for user %s",
            current_user.get("auth_id"),
            exc_info=True,
        )
        raise HTTPException(
            status_code=502, detail="Payment provider error — please try again"
        ) from None

    return PortalResponse(url=session.url)
