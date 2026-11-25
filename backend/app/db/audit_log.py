# backend/app/db/audit_log.py

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict

from app.core.reporting import report_failure

from .base import audit_logs_collection

logger = logging.getLogger(__name__)

AUDIT_LOG_RETENTION = timedelta(days=90)

# Legal evidence of auto-renewal consent (#770): these rows must outlive the TTL.
RENEWAL_CONSENT_ACTION = "billing.renewal_consent"
RETAINED_ACTIONS = frozenset({RENEWAL_CONSENT_ACTION})
# Kept until the subscription ends plus 4 years (#948, owner decision of
# 2026-11-09: California's limit for unfair-competition claims). While the
# subscription is live the row has no expires_at.
RENEWAL_CONSENT_RETENTION = timedelta(days=4 * 365 + 1)


async def create_audit_log(
    action: str, actor_id: str, target_id: str, resource_type: str, details: Dict = None, session=None
) -> Dict:
    now = datetime.now(timezone.utc)
    log_data = {
        "action": action,
        "actor_id": actor_id,
        "target_id": target_id,
        "resource_type": resource_type,
        "details": details or {},
        "timestamp": now,
    }
    # Rows without expires_at are ignored by the TTL monitor. Consent is
    # recorded before Checkout, so until a subscription goes live it is dated
    # as if one ended now: an abandoned checkout must not keep it forever.
    if action == RENEWAL_CONSENT_ACTION:
        log_data["expires_at"] = now + RENEWAL_CONSENT_RETENTION
    elif action not in RETAINED_ACTIONS:
        log_data["expires_at"] = now + AUDIT_LOG_RETENTION
    await audit_logs_collection.insert_one(log_data, session=session)
    return log_data


def _consent_rows(auth_id: str) -> Dict:
    return {"action": RENEWAL_CONSENT_ACTION, "actor_id": auth_id}


async def renewal_consent_live(auth_id: str) -> None:
    """The user's subscription is live: keep their consent rows with no expiry (#948)."""
    await audit_logs_collection.update_many(
        _consent_rows(auth_id), {"$unset": {"expires_at": ""}}
    )


async def renewal_consent_ended(auth_id: str, ended_at: datetime) -> None:
    """The user's subscription ended at ``ended_at``: their consent rows expire
    4 years later (#948). A stamp already later than that is kept."""
    await audit_logs_collection.update_many(
        _consent_rows(auth_id),
        {"$max": {"expires_at": ended_at + RENEWAL_CONSENT_RETENTION}},
    )


async def audit_after_write(**kwargs) -> None:
    """create_audit_log for a write that has already landed (#847): a failed row
    is logged and reported, never raised into a write that succeeded."""
    try:
        await create_audit_log(**kwargs)
    except Exception as error:
        logger.error("Could not audit %s", kwargs.get("action"), exc_info=True)
        report_failure("audit", error)


async def ensure_audit_log_indexes() -> None:
    """Create the audit_logs TTL + actor indexes and backfill legacy rows (#787).

    Idempotent; each step is logged and never fatal so a startup can't be
    bricked by it.
    """
    coll = audit_logs_collection
    try:
        await coll.create_index("expires_at", name="audit_logs_ttl_idx", expireAfterSeconds=0)
    except Exception:
        logger.error("Failed to create TTL index on audit_logs.expires_at", exc_info=True)

    try:
        await coll.create_index(
            [("actor_id", 1), ("timestamp", -1)], name="actor_timestamp_idx"
        )
    except Exception:
        logger.error("Failed to create actor index on audit_logs", exc_info=True)

    try:
        # Rows written before the TTL existed would otherwise live forever.
        retention_ms = int(AUDIT_LOG_RETENTION.total_seconds() * 1000)
        await coll.update_many(
            {"expires_at": {"$exists": False}, "action": {"$nin": list(RETAINED_ACTIONS)}},
            [{"$set": {"expires_at": {"$add": [
                # A missing or non-date timestamp would fail the whole update.
                {"$cond": [{"$eq": [{"$type": "$timestamp"}, "date"]}, "$timestamp", "$$NOW"]},
                retention_ms,
            ]}}}],
        )
    except Exception:
        logger.error("Failed to backfill audit_logs.expires_at", exc_info=True)

    try:
        await _backfill_renewal_consent()
    except Exception:
        logger.error("Failed to backfill renewal-consent expiry", exc_info=True)


async def _backfill_renewal_consent() -> None:
    """Consent rows written before #948 have no expiry. Unless the user's
    subscription is still live, date them as ending now: the real end is not
    recorded, and now is never earlier than it."""
    from app.core.entitlements import has_live_subscription
    from app.db.user import get_user_by_auth_id

    unstamped = {"action": RENEWAL_CONSENT_ACTION, "expires_at": {"$exists": False}}
    now = datetime.now(timezone.utc)
    for auth_id in await audit_logs_collection.distinct("actor_id", unstamped):
        user = await get_user_by_auth_id(auth_id)
        if user is None or not has_live_subscription(user):
            await renewal_consent_ended(auth_id, now)
