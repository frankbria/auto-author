"""Single-use download tokens for the account export (#966).

One document per token, keyed ``_id = token``, holding the account it was issued
to. Redeeming deletes it in the same operation that reads it, so a token works
once. A TTL index reaps unredeemed ones; it runs about once a minute, so
``redeem_export_token`` checks the expiry itself.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from .base import get_collection

EXPORT_TOKEN_TTL_SECONDS = 60

# ensure the TTL index once per process on first use (stripe_events.py idiom).
_ttl_index_ensured = False


async def _tokens_collection():
    coll = await get_collection("export_tokens")
    global _ttl_index_ensured
    if not _ttl_index_ensured:
        await coll.create_index("expires_at", expireAfterSeconds=0)
        _ttl_index_ensured = True
    return coll


async def issue_export_token(auth_id: str) -> str:
    token = secrets.token_urlsafe(32)
    await (await _tokens_collection()).insert_one(
        {
            "_id": token,
            "auth_id": auth_id,
            "expires_at": datetime.now(timezone.utc)
            + timedelta(seconds=EXPORT_TOKEN_TTL_SECONDS),
        }
    )
    return token


async def redeem_export_token(token: str) -> Optional[str]:
    """Use ``token`` up. Returns the auth_id it was issued to, or None when it is
    unknown, already used or expired."""
    doc = await (await _tokens_collection()).find_one_and_delete({"_id": token})
    if doc is None:
        return None
    if doc["expires_at"].replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        return None
    return doc["auth_id"]
