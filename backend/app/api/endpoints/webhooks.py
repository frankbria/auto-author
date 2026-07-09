import json
import logging

import stripe
from fastapi import APIRouter, HTTPException, Request
from stripe import SignatureVerificationError

from app.core.config import settings
from app.core.entitlements import DEFAULT_PLAN, resolve_plan_for_price
from app.db.stripe_events import mark_event_processed, unmark_event
from app.db.user import (
    get_user_by_auth_id,
    get_user_by_stripe_customer_id,
    update_user,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Clerk webhooks are deprecated - users are now created automatically on better-auth signup

@router.post("/better-auth", status_code=200)
async def better_auth_webhook():
    """
    Better-auth webhook handler.

    Note: better-auth typically handles user creation/updates automatically,
    so explicit webhook handlers may not be necessary. This endpoint is a placeholder
    for future webhook implementations if needed.
    """
    logger.info("better-auth webhook received (no-op)")
    return {"message": "better-auth webhook processed"}


@router.post("/stripe", status_code=200)
async def stripe_webhook(request: Request):
    """Stripe webhook (issue #220): raw-body HMAC verify + subscription→plan sync.

    Deliberately unauthenticated — the Stripe signature over the raw body IS the
    auth (the /api/v1/webhooks prefix is session-exempt, and no middleware
    consumes the body). On ``customer.subscription.*`` events, maps the
    subscription's price to a plan (app.core.entitlements) and persists plan +
    Stripe ids on the matching user. Replays (same event id) are no-ops.
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        # Fail closed: never process unverifiable payloads.
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured")

    raw_body = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    try:
        stripe.Webhook.construct_event(
            raw_body, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, SignatureVerificationError):
        raise HTTPException(
            status_code=400, detail="Invalid Stripe webhook signature or payload"
        )

    # construct_event verified the HMAC and that the body is valid JSON; work
    # on the plain-dict payload (stripe v15's StripeObject has no dict API).
    event = json.loads(raw_body)
    event_type = event.get("type", "")
    event_id = event.get("id", "")
    if not event_type.startswith("customer.subscription.") or not event_id:
        return {"status": "ignored", "event_type": event_type}

    # Atomic claim: Stripe retries deliveries, so the same event id may arrive
    # more than once (or concurrently on two workers).
    if not await mark_event_processed(event_id):
        logger.info("Stripe event %s already processed (replay) — skipping", event_id)
        return {"status": "replay", "event_id": event_id}

    try:
        subscription = (event.get("data") or {}).get("object") or {}
        return await _apply_subscription_event(event_type, subscription)
    except Exception:
        # Release the claim so Stripe's retry of this failure isn't treated as
        # a replay, then surface a 500 (Stripe retries non-2xx).
        await unmark_event(event_id)
        logger.error("Failed to process Stripe event %s", event_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process Stripe event")


async def _apply_subscription_event(event_type: str, subscription: dict) -> dict:
    """Resolve the plan for a verified customer.subscription.* event and persist it."""
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")

    if event_type == "customer.subscription.deleted":
        plan = DEFAULT_PLAN
    else:
        items = (subscription.get("items") or {}).get("data") or []
        price_id = ((items[0] or {}).get("price") or {}).get("id") if items else None
        plan = resolve_plan_for_price(price_id)

    user = await get_user_by_stripe_customer_id(customer_id) if customer_id else None
    if user is None:
        # First event for a not-yet-linked user: checkout (#221) stamps the
        # subscription metadata with our auth_id.
        auth_id = (subscription.get("metadata") or {}).get("auth_id")
        user = await get_user_by_auth_id(auth_id) if auth_id else None
    if user is None:
        # Ack with 200 so Stripe stops retrying — there is no user to update
        # (e.g. deleted account, or a customer created outside this app).
        logger.warning(
            "Stripe %s for customer %s matches no user", event_type, customer_id
        )
        return {"status": "no_matching_user"}

    await update_user(
        user["auth_id"],
        {
            "plan": plan,
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
        },
    )
    logger.info(
        "Stripe %s: user %s plan set to %s", event_type, user["auth_id"], plan
    )
    return {"status": "processed", "plan": plan}
