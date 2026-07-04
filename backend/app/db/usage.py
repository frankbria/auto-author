# backend/app/db/usage.py
"""Per-user AI usage counters (cost control, issue #173).

One tiny document per (user, period-bucket), e.g. `auth_id:day:2026-07-03`.
Increments are atomic (`$inc` upsert) so racing generations can't undercount.
A TTL index on `expires_at` reaps stale buckets so the collection stays bounded.
"""

from datetime import datetime, timezone
from pymongo import ReturnDocument

from .base import get_collection

# ponytail: ensure the TTL index once per process on first use. Idempotent, and
# cheap — avoids wiring a startup hook just for one collection.
_ttl_index_ensured = False


async def _usage_collection():
    coll = await get_collection("usage_counters")
    global _ttl_index_ensured
    if not _ttl_index_ensured:
        # Mongo reaps documents once `expires_at` passes (expireAfterSeconds=0).
        await coll.create_index("expires_at", expireAfterSeconds=0)
        _ttl_index_ensured = True
    return coll


async def increment_usage(user_id: str, period_key: str, ttl_seconds: int) -> int:
    """Atomically bump the counter for ``user_id`` in ``period_key`` and return the new total.

    ``period_key`` is a stable per-window bucket (e.g. ``day:2026-07-03``). The doc
    expires ``ttl_seconds`` after first creation so old buckets self-clean.
    """
    coll = await _usage_collection()
    now = datetime.now(timezone.utc)
    expires_at = datetime.fromtimestamp(now.timestamp() + ttl_seconds, tz=timezone.utc)
    doc = await coll.find_one_and_update(
        {"_id": f"{user_id}:{period_key}"},
        {
            "$inc": {"count": 1},
            "$setOnInsert": {"user_id": user_id, "expires_at": expires_at},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc["count"]
