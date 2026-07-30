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
        # Stripe guarantees delivery, not order. Pass the event's own timestamp
        # so an older update that arrives late cannot overwrite a newer plan
        # (#352) — idempotency above only stops the *same* event twice.
        event_created = event.get("created")
        return await _apply_subscription_event(
            event_type, subscription, event_id, event_created
        )
    except Exception:
        # Release the claim so Stripe's retry of this failure isn't treated as
        # a replay, then surface a 500 (Stripe retries non-2xx).
        await unmark_event(event_id)
        logger.error("Failed to process Stripe event %s", event_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process Stripe event")


async def _apply_subscription_event(
    event_type: str, subscription: dict, event_id: str,
    event_created: int | None = None,
) -> dict:
    """Resolve the plan for a verified customer.subscription.* event and persist it.

    ``event_created`` is Stripe's own epoch timestamp for the event. Deliveries
    are not ordered, so a subscription.updated from 10:00 can land after the one
    from 10:05 — applying it would silently downgrade (or upgrade) a user to a
    stale plan. Each applied event records its timestamp and anything older is
    ignored.
    """
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")

    if event_type == "customer.subscription.deleted":
        plan = DEFAULT_PLAN
        subscription_id = None  # the subscription is gone; don't retain a dead id
    else:
        # Scan every line item — a multi-item subscription may not list the
        # plan-bearing price first.
        plan = DEFAULT_PLAN
        for item in (subscription.get("items") or {}).get("data") or []:
            resolved = resolve_plan_for_price(((item or {}).get("price") or {}).get("id"))
            if resolved != DEFAULT_PLAN:
                plan = resolved
                break

    user = await get_user_by_stripe_customer_id(customer_id) if customer_id else None
    if user is None:
        # First event for a not-yet-linked user: checkout (#221) stamps the
        # subscription metadata with our auth_id.
        auth_id = (subscription.get("metadata") or {}).get("auth_id")
        user = await get_user_by_auth_id(auth_id) if auth_id else None
    if user is None:
        # Ack with 200 so Stripe stops retrying — there is no user to update
        # (e.g. deleted account, or a customer created outside this app). But
        # RELEASE the replay marker: once the user is linked later, an operator
        # can "Resend" the event from the Stripe dashboard (same event id) and
        # it must reprocess instead of being swallowed as a replay.
        await unmark_event(event_id)
        logger.warning(
            "Stripe %s for customer %s matches no user", event_type, customer_id
        )
        return {"status": "no_matching_user"}

    # Out-of-order guard. Stripe does not order deliveries, so an older
    # subscription.updated can arrive after a newer one and overwrite the plan
    # with a stale value — a real downgrade for a paying user. Idempotency above
    # only prevents the SAME event twice; this prevents an EARLIER one landing
    # last. Events without a timestamp (older payload shapes) are applied as
    # before rather than dropped.
    #
    # Known limit: `created` has one-second granularity, so two updates inside
    # the same second cannot be ordered by it. The filter uses `$lte` so
    # same-second events are still applied (last-write-wins within one second,
    # the pre-existing behaviour) rather than silently dropped.
    # The complete fix is to re-fetch the subscription from Stripe on each event
    # and apply canonical state; that trades an extra API call (and a new failure
    # mode when Stripe is unreachable) for exactness, and is the upgrade path if
    # same-second races ever show up in practice.
    # Enforced by Mongo as part of the write, not by a read here. Two deliveries
    # for the same customer carry DIFFERENT event ids, so mark_event_processed
    # does not serialize them: a read-then-write check lets both pass and the
    # older one land last. The condition goes in the query instead.
    ordering_filter = None
    if event_created is not None:
        ordering_filter = {
            "$or": [
                {"stripe_event_created": {"$exists": False}},
                {"stripe_event_created": None},
                {"stripe_event_created": {"$lte": event_created}},
            ]
        }

    # If a concurrent request linked this stripe_customer_id to a DIFFERENT user
    # between our lookup and this write (TOCTOU — the only way to reach it, since
    # the lookup above wins otherwise), the unique index rejects the $set -> 500
    # -> Stripe retries and its dashboard flags the failing endpoint. That's the
    # right ops signal for an inconsistent billing state; checkout (#221)
    # enforces the 1:1 link at creation time. On subscription.deleted the
    # customer id is deliberately RETAINED — the Stripe customer still exists,
    # only the subscription ended. actor_id makes every plan transition
    # auditable (billing disputes).
    updated = await update_user(
        user["auth_id"],
        {
            "plan": plan,
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            # Watermark the ordering filter above compares against.
            **({"stripe_event_created": event_created} if event_created is not None else {}),
        },
        actor_id=f"stripe:{event_id}",
        extra_filter=ordering_filter,
    )

    if updated is None and ordering_filter is not None:
        # The user exists (looked up above), so a no-match means the ordering
        # condition rejected this write: a newer event has already been applied.
        logger.info(
            "Stripe %s (created=%s) is older than the applied event for user %s "
            "— ignoring",
            event_type,
            event_created,
            user["auth_id"],
        )
        return {"status": "stale_event", "event_id": event_id}

    logger.info(
        "Stripe %s: user %s plan set to %s", event_type, user["auth_id"], plan
    )
    return {"status": "processed", "plan": plan}
