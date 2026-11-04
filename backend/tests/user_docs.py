"""Users documents as better-auth writes them (#1263): keyed by ``_id``, with
no ``auth_id`` field. The app derives ``auth_id`` from ``_id`` when it reads one."""

from bson import ObjectId

from app.db.base import get_collection
from app.db.user import user_key


def user_doc(auth_id: str = None, **fields) -> dict:
    """``fields`` stored under ``auth_id``'s key (a fresh ObjectId when None)."""
    key = user_key(auth_id) if auth_id else {"_id": ObjectId()}
    return {**fields, **key}


async def insert_user(auth_id: str = None, **fields) -> str:
    """Insert a users document and return its id as the app passes it around."""
    doc = user_doc(auth_id, **fields)
    await (await get_collection("users")).insert_one(doc)
    return str(doc["_id"])
