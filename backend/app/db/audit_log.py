# backend/app/db/audit_log.py

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict

from .base import audit_logs_collection

logger = logging.getLogger(__name__)

AUDIT_LOG_RETENTION = timedelta(days=90)

# Legal evidence of auto-renewal consent (#770): these rows must outlive the TTL.
RETAINED_ACTIONS = frozenset({"billing.renewal_consent"})


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
    # Rows without expires_at are ignored by the TTL monitor.
    if action not in RETAINED_ACTIONS:
        log_data["expires_at"] = now + AUDIT_LOG_RETENTION
    await audit_logs_collection.insert_one(log_data, session=session)
    return log_data


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
