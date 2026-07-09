# backend/app/db/stripe_events.py
"""Stripe webhook replay/idempotency tracking (issue #220).

One tiny document per processed Stripe event, keyed ``_id = event.id`` — the
unique ``_id`` guard makes the "have we seen this event?" check atomic across
workers and restarts (same idiom as app/db/usage.py). A TTL index reaps old
markers; Stripe stops retrying an event after ~3 days, so 30 days is generous.
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


async def mark_event_processed(
    event_id: str, ttl_seconds: int = EVENT_MARKER_TTL_SECONDS
) -> bool:
    """Atomically claim ``event_id``. True = fresh (process it); False = replay."""
    coll = await _events_collection()
    try:
        await coll.insert_one(
            {
                "_id": event_id,
                "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
            }
        )
        return True
    except DuplicateKeyError:
        return False


async def unmark_event(event_id: str) -> None:
    """Release a claimed event id so Stripe's retry of a failed processing
    attempt isn't misclassified as a replay."""
    coll = await _events_collection()
    await coll.delete_one({"_id": event_id})
