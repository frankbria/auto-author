# backend/app/db/audit_log.py

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict

from app.core.reporting import report_failure

from .base import audit_logs_collection, get_collection

logger = logging.getLogger(__name__)

AUDIT_LOG_RETENTION = timedelta(days=90)

# Legal evidence of auto-renewal consent (#770): these rows must outlive the TTL.
RENEWAL_CONSENT_ACTION = "billing.renewal_consent"
RETAINED_ACTIONS = frozenset({RENEWAL_CONSENT_ACTION})


def renewal_consent_expiry(ended_at: datetime) -> datetime:
    """Consent rows are kept until the subscription ends plus 4 calendar years
    (#948, owner decision of 2026-11-09: California's limit for unfair-competition
    claims). While the subscription exists the row has no expires_at."""
    try:
        return ended_at.replace(year=ended_at.year + 4)
    except ValueError:  # 29 February into a year with none
        return ended_at.replace(year=ended_at.year + 4, month=3, day=1)


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
        log_data["expires_at"] = renewal_consent_expiry(now)
    elif action not in RETAINED_ACTIONS:
        log_data["expires_at"] = now + AUDIT_LOG_RETENTION
    await audit_logs_collection.insert_one(log_data, session=session)
    return log_data


def _consent_rows(auth_id: str) -> Dict:
    return {"action": RENEWAL_CONSENT_ACTION, "actor_id": auth_id}


async def renewal_consent_live(auth_id: str) -> None:
    """The user's subscription exists: keep their consent rows with no expiry (#948)."""
    await audit_logs_collection.update_many(
        _consent_rows(auth_id), {"$unset": {"expires_at": ""}}
    )


async def renewal_consent_ended(auth_id: str, ended_at: datetime) -> None:
    """The user's subscription ended at ``ended_at``: their consent rows expire
    4 years later (#948). A stamp already later than that is kept."""
    await audit_logs_collection.update_many(
        _consent_rows(auth_id),
        {"$max": {"expires_at": renewal_consent_expiry(ended_at)}},
    )


async def sync_renewal_consent(auth_id: str, ended_at: datetime) -> None:
    """Make the user's consent rows match their stored subscription: no expiry
    while it exists, else ``ended_at`` + 4 years (#948).

    Read from the users document, not the event, and read again after writing:
    two webhook deliveries can write the user in one order and the rows in the
    other, and whichever writes the rows last then puts them right.
    """
    from app.core.entitlements import subscription_exists
    from app.db.user import get_user_by_auth_id

    written = None
    for _ in range(3):
        user = await get_user_by_auth_id(auth_id)
        exists = user is not None and subscription_exists(user)
        if exists == written:
            return
        written = exists
        if exists:
            await renewal_consent_live(auth_id)
        else:
            await renewal_consent_ended(auth_id, ended_at)


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
    """Consent rows written before #948 have no expiry. Date each user's from the
    best record of when their subscription ended (``_known_end``); rows of a
    subscription that still exists stay as they are."""
    from app.core.entitlements import subscription_exists
    from app.db.user import get_user_by_auth_id

    unstamped = {"action": RENEWAL_CONSENT_ACTION, "expires_at": {"$exists": False}}
    for auth_id in await audit_logs_collection.distinct("actor_id", unstamped):
        user = await get_user_by_auth_id(auth_id)
        if user is None or not subscription_exists(user):
            await renewal_consent_ended(auth_id, await _known_end(auth_id, user))


async def _known_end(auth_id: str, user) -> datetime:
    """The earliest end date known to be no earlier than the real one.

    A deleted account: its deletion, which cancelled any subscription first.
    A user with subscription events: the newest one applied (the deletion's).
    A user with none never subscribed: their latest consent. Else now.
    """
    if user is None:
        record = await (await get_collection("deleted_users")).find_one({"auth_id": auth_id})
        return _utc((record or {}).get("deleted_at"))
    marks = [user.get("stripe_event_created"),
             *(user.get("stripe_event_created_by_subscription") or {}).values()]
    marks = [m for m in marks if isinstance(m, (int, float))]
    if marks:
        return datetime.fromtimestamp(max(marks), timezone.utc)
    latest = await audit_logs_collection.find_one(
        _consent_rows(auth_id), sort=[("timestamp", -1)]
    )
    return _utc((latest or {}).get("timestamp"))


def _utc(value) -> datetime:
    if not isinstance(value, datetime):
        return datetime.now(timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
