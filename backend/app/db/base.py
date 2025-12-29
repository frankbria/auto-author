# backend/app/db/base.py

from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId
from app.core.config import settings
import certifi

# Configure MongoDB client with proper SSL/TLS settings for Python 3.13+ compatibility
# This ensures secure connections to MongoDB Atlas with proper certificate validation
_client = AsyncIOMotorClient(
    settings.mongo_connection_string,  # Prefers MONGODB_URI over DATABASE_URL
    tlsCAFile=certifi.where(),  # Use certifi's CA bundle for SSL certificate verification
    tls=True,  # Explicitly enable TLS (inferred from mongodb+srv:// but explicit is better)
    tlsAllowInvalidCertificates=False,  # Ensure certificate validation (security requirement)
    serverSelectionTimeoutMS=30000,  # 30-second timeout for server selection
    connectTimeoutMS=20000,  # 20-second timeout for initial connection
    socketTimeoutMS=20000,  # 20-second timeout for socket operations
)
_db = _client[settings.DATABASE_NAME]

users_collection = _db.get_collection("users")
books_collection = _db.get_collection("books")
audit_logs_collection = _db.get_collection("audit_logs")
sessions_collection = _db.get_collection("sessions")


async def get_collection(name: str):
    return _db.get_collection(name)


# Only exports the truly "core" things
__all__ = [
    "users_collection",
    "books_collection",
    "audit_logs_collection",
    "sessions_collection",
    "get_collection",
    "ObjectId",
]
