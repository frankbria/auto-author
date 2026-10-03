"""Billing endpoints: Stripe Checkout upgrade (#221) + billing portal (#222).

The plan itself is NEVER changed here — the #220 webhook is the only writer
(the client redirect back from Stripe is untrusted). This endpoint only
establishes the user<->Stripe linkage the webhook reconciles on.
"""

import asyncio
import hashlib
import logging
import threading
from typing import Dict, Literal, Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.api.dependencies import audit_request, get_rate_limiter
from app.core.config import settings
from app.core.entitlements import ai_quota_for_plan
from app.core.security import get_current_user_from_session
from app.db.user import get_user_by_auth_id, update_user

logger = logging.getLogger(__name__)
router = APIRouter()


async def cancel_subscription_for_deletion(auth_id: str) -> None:
    """Cancel ``auth_id``'s Stripe subscription before their account is deleted (#764).

    Runs before anything is deleted: on a StripeError it raises a 502 and the
    account stays as it was, so the user can retry. Read from the DB, not the
    session dict, so the admin route cancels the target's subscription.
    """
    user = await get_user_by_auth_id(auth_id)
    subscription_id = (user or {}).get("stripe_subscription_id")
    if not subscription_id:
        return
    try:
        await asyncio.to_thread(
            stripe.Subscription.cancel,
            subscription_id,
            api_key=settings.STRIPE_SECRET_KEY,
            idempotency_key=f"account-delete-{subscription_id}",
        )
    except stripe.StripeError:
        logger.error(
            "Stripe cancel of %s failed; not deleting user %s",
            subscription_id, auth_id, exc_info=True,
        )
        raise HTTPException(
            status_code=502,
            detail="Couldn't cancel your subscription, so your account was not "
            "deleted. Please try again.",
        ) from None
    # Forget the cancelled id: if a later deletion step fails, the retry must not
    # depend on how Stripe answers a second cancel once the 24h key has expired.
    await update_user(
        auth_id,
        {"stripe_subscription_id": None},
        extra_filter={"stripe_subscription_id": subscription_id},
    )


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


# --- Auto-renewal disclosure (#770, CA ARL / ROSCA) ---
# The ONE place the renewal terms live: the settings page shows this text next
# to the subscribe action, Stripe's hosted page repeats it, and the consent
# record stores it. Wording is plain-language pending counsel review (#791);
# bump the version whenever the template changes.
RENEWAL_DISCLOSURE_VERSION = "2026-10-02"
RENEWAL_DISCLOSURE_TEMPLATE = (
    "Auto Author Pro is {price} per {period}, charged to your payment method "
    "today and again at the start of each billing period. Your subscription "
    "renews automatically until you cancel. Cancel anytime in Auto Author under "
    "Settings → Billing → Manage billing; cancelling stops future renewals and "
    "takes effect at the end of the current billing period. Fees are "
    "non-refundable except where required by law."
)
RENEWAL_CONSENT_ACTION = "billing.renewal_consent"

# Stripe Price amounts/intervals are immutable (a new price means a new id), so
# a per-id cache can never go stale.
_PRICE_CACHE: Dict[str, object] = {}


class RenewalDisclosure(BaseModel):
    version: str
    text: str
    sha256: str
    price_id: str


def _require_stripe_checkout() -> None:
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRICE_ID_PRO:
        # Fail closed, mirroring the webhook: never talk to Stripe half-configured.
        raise HTTPException(status_code=503, detail="Stripe checkout is not configured")


def _format_price(unit_amount: int, currency: str) -> str:
    # ponytail: assumes a two-decimal currency; zero-decimal ones (JPY, KRW) need
    # Stripe's minor-unit table if the plan is ever priced in one.
    amount = f"{unit_amount / 100:,.2f}"
    return f"${amount}" if currency.lower() == "usd" else f"{amount} {currency.upper()}"


async def _current_disclosure() -> RenewalDisclosure:
    """Render the renewal terms from the live Stripe Price (the charge's own source)."""
    _require_stripe_checkout()
    price_id = settings.STRIPE_PRICE_ID_PRO
    price = _PRICE_CACHE.get(price_id)
    if price is None:
        try:
            price = await asyncio.to_thread(
                stripe.Price.retrieve, price_id, api_key=settings.STRIPE_SECRET_KEY
            )
        except stripe.StripeError:
            logger.error("Stripe price lookup failed for %s", price_id, exc_info=True)
            raise HTTPException(
                status_code=502, detail="Payment provider error — please try again"
            ) from None
        _PRICE_CACHE[price_id] = price

    recurring = getattr(price, "recurring", None)
    if recurring is None or price.unit_amount is None:
        logger.error("STRIPE_PRICE_ID_PRO %s is not a recurring fixed price", price_id)
        raise HTTPException(status_code=503, detail="Stripe checkout is not configured")

    count = recurring.interval_count or 1
    period = recurring.interval if count == 1 else f"{count} {recurring.interval}s"
    text = RENEWAL_DISCLOSURE_TEMPLATE.format(
        price=_format_price(price.unit_amount, price.currency), period=period
    )
    return RenewalDisclosure(
        version=RENEWAL_DISCLOSURE_VERSION,
        text=text,
        sha256=hashlib.sha256(text.encode()).hexdigest(),
        price_id=price_id,
    )


@router.get("/disclosure", response_model=RenewalDisclosure)
async def get_renewal_disclosure(
    current_user: Dict = Depends(get_current_user_from_session),
):
    """The auto-renewal terms the UI must show, verbatim, before the subscribe action."""
    return await _current_disclosure()


class CheckoutRequest(BaseModel):
    plan: Literal["pro"] = "pro"
    # Affirmative consent to the renewal terms, and the hash of the exact text
    # the user was shown (from GET /billing/disclosure).
    accept_renewal_terms: bool = False
    disclosure_sha256: Optional[str] = None


class CheckoutResponse(BaseModel):
    url: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    body: CheckoutRequest,
    request: Request,
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=5, window=300)),
):
    """Create a Stripe Checkout session for upgrading to a paid plan."""
    _require_stripe_checkout()

    if current_user.get("plan") in PAID_PLANS:
        raise HTTPException(status_code=409, detail="You are already on a paid plan")

    if not body.accept_renewal_terms or not body.disclosure_sha256:
        raise HTTPException(
            status_code=400,
            detail="You must agree to the automatic renewal terms to subscribe",
        )

    disclosure = await _current_disclosure()
    if body.disclosure_sha256 != disclosure.sha256:
        raise HTTPException(
            status_code=409,
            detail="The subscription terms have changed — please review them and try again",
        )

    auth_id = current_user["auth_id"]
    # Recorded BEFORE any checkout exists; if this write fails, no checkout is created.
    await audit_request(
        request,
        current_user,
        action=RENEWAL_CONSENT_ACTION,
        resource_type="billing",
        target_id=auth_id,
        metadata={
            "disclosure_version": disclosure.version,
            "disclosure_sha256": disclosure.sha256,
            "disclosure_text": disclosure.text,
            "price_id": disclosure.price_id,
        },
    )
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
            # The disclosure keys tie sub_X to its consent record in audit_logs.
            subscription_data={
                "metadata": {
                    "auth_id": auth_id,
                    "renewal_disclosure_version": disclosure.version,
                    "renewal_disclosure_sha256": disclosure.sha256,
                }
            },
            # Stripe's own checkbox + record, and the renewal terms repeated
            # beside the Subscribe button (#770). Requires a Terms of Service
            # URL in the Stripe Dashboard's public details.
            consent_collection={"terms_of_service": "required"},
            custom_text={
                "submit": {"message": disclosure.text},
                "terms_of_service_acceptance": {
                    "message": f"I agree to the [Terms of Service]({frontend_base}/terms), "
                    "including automatic renewal until I cancel."
                },
            },
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
