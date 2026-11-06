# backend/app/db/usage.py
"""Per-user AI usage counters (cost control, issue #173).

One tiny document per (user, period-bucket), e.g. `auth_id:day:2026-07-03`.
Increments are atomic (`$inc` upsert) so racing generations can't undercount.
A TTL index on `expires_at` reaps stale buckets so the collection stays bounded.
"""

from datetime import datetime, timezone
from typing import Optional

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


async def increment_usage(user_id: str, period_key: str, ttl_seconds: Optional[int]) -> int:
    """Atomically bump the counter for ``user_id`` in ``period_key`` and return the new total.

    ``period_key`` is a stable per-window bucket (e.g. ``day:2026-07-03``). The doc
    expires ``ttl_seconds`` after first creation so old buckets self-clean. A
    ``None`` ttl never expires: the free trial's lifetime count (``trial``).
    """
    coll = await _usage_collection()
    on_insert: dict = {"user_id": user_id}
    if ttl_seconds is not None:
        now = datetime.now(timezone.utc)
        on_insert["expires_at"] = datetime.fromtimestamp(
            now.timestamp() + ttl_seconds, tz=timezone.utc
        )
    doc = await coll.find_one_and_update(
        {"_id": f"{user_id}:{period_key}"},
        {"$inc": {"count": 1}, "$setOnInsert": on_insert},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc["count"]


async def refund_usage(user_id: str, period_key: str) -> None:
    """Hand back one unit charged by ``increment_usage`` (#798): the request it
    was charged for never reached the model."""
    coll = await _usage_collection()
    await coll.update_one({"_id": f"{user_id}:{period_key}"}, {"$inc": {"count": -1}})


async def delete_usage(user_id: str) -> None:
    """Remove every counter of ``user_id``, at account deletion (#957)."""
    coll = await _usage_collection()
    await coll.delete_many({"user_id": user_id})
