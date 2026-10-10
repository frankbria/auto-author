# backend/app/db/stripe_events.py
"""Stripe webhook replay/idempotency tracking (issue #220).

One tiny document per processed Stripe event, keyed ``_id = event.id``. The
marker is written only AFTER the event's effect is applied (#769): a worker that
dies mid-apply leaves no marker, so Stripe's retry re-applies instead of being
swallowed as a replay. A duplicate that races past the check re-applies the
same idempotent write. A TTL index reaps old markers; Stripe stops retrying an
event after ~3 days, so 30 days is generous.
"""

from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from .base import get_collection

EVENT_MARKER_TTL_SECONDS = 30 * 24 * 3600

# ponytail: ensure the TTL index once per process on first use (usage.py idiom).
_ttl_index_ensured = False


async def _events_collection():
    coll = await get_collection("processed_stripe_events")
    global _ttl_index_ensured
    if not _ttl_index_ensured:
        await coll.create_index("expires_at", expireAfterSeconds=0)
        _ttl_index_ensured = True
    return coll


async def is_event_processed(event_id: str) -> bool:
    coll = await _events_collection()
    return await coll.find_one({"_id": event_id}, {"_id": 1}) is not None


async def mark_event_processed(
    event_id: str, ttl_seconds: int = EVENT_MARKER_TTL_SECONDS
) -> None:
    """Record ``event_id`` as applied. Call only after its effect is persisted."""
    coll = await _events_collection()
    try:
        await coll.insert_one(
            {
                "_id": event_id,
                "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
            }
        )
    except DuplicateKeyError:
        pass  # a concurrent duplicate delivery recorded it first
