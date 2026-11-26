"""Stripe calls behind billing that no billing route defines: cancelling a
subscription before account deletion (#764) and the pinned portal
Configuration (#771). Split from billing.py for the 500-line limit (#1313).
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import HTTPException

from app.core.config import settings
from app.core.entitlements import DEFAULT_PLAN
from app.db.audit_log import sync_renewal_consent
from app.db.user import get_user_by_auth_id, update_user

logger = logging.getLogger(__name__)


async def cancel_subscription_for_deletion(auth_id: str) -> None:
    """Cancel ``auth_id``'s Stripe subscription before their account is deleted (#764).

    Runs before anything is deleted: on a StripeError it raises a 502 and the
    account stays as it was, so the user can retry. Read from the DB, not the
    session dict, so the admin route cancels the target's subscription.
    """
    user = await get_user_by_auth_id(auth_id)
    subscription_id = (user or {}).get("stripe_subscription_id")
    if not subscription_id:
        # Ended already; stamps consent rows a failed webhook write left bare (#948).
        await sync_renewal_consent(auth_id)
        return
    try:
        cancelled = await asyncio.to_thread(
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
    ended_at = getattr(cancelled, "canceled_at", None) or int(time.time())
    # Forget the cancelled id: if a later deletion step fails, the retry must not
    # depend on how Stripe answers a second cancel once the 24h key has expired.
    # With the id gone, the webhook treats Stripe's subscription.deleted for it
    # as another subscription's and ignores it (#768), so apply its effect here,
    # watermark included: a late pre-cancel event for the dead subscription must
    # land as stale_event, not re-establish it and grant pro.
    await update_user(
        auth_id,
        {
            # What the user was paying for, kept in the deleted account's record (#954).
            "cancelled_subscription": {
                "id": subscription_id,
                "plan": user.get("plan"),
                "status": user.get("stripe_subscription_status"),
            },
            "stripe_subscription_id": None,
            "stripe_subscription_status": None,
            "plan": DEFAULT_PLAN,
            "stripe_event_created": ended_at,
        },
        extra_filter={"stripe_subscription_id": subscription_id},
    )
    # The webhook ignores events for a closed account: date the consent record
    # from this cancel instead (#948). After the id is cleared, so a webhook
    # sync in flight re-reads it as ended. It survives the deletion.
    await sync_renewal_consent(auth_id, datetime.fromtimestamp(ended_at, timezone.utc))


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
