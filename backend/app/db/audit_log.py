# backend/app/db/audit_log.py

from .base import audit_logs_collection
from datetime import datetime, timezone
from typing import Dict


async def create_audit_log(
    action: str, actor_id: str, target_id: str, resource_type: str, details: Dict = None, session=None
) -> Dict:
    log_data = {
        "action": action,
        "actor_id": actor_id,
        "target_id": target_id,
        "resource_type": resource_type,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc),
        "ip_address": None,
    }
    await audit_logs_collection.insert_one(log_data, session=session)
    return log_data
