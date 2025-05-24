# backend/app/db/base.py

from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId
from app.core.config import settings

_client = AsyncIOMotorClient(settings.DATABASE_URI)
_db = _client[settings.DATABASE_NAME]

users_collection = _db.get_collection("users")
books_collection = _db.get_collection("books")
audit_logs_collection = _db.get_collection("audit_logs")


async def get_collection(name: str):
    return _db.get_collection(name)


# Only exports the truly “core” things
__all__ = [
    "users_collection",
    "books_collection",
    "audit_logs_collection",
    "get_collection",
    "ObjectId",
]
