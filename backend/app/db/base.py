# backend/app/db/base.py

from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId
from app.core.config import settings
import certifi

# Determine if we're connecting to MongoDB Atlas (requires TLS) or local MongoDB (no TLS)
is_atlas = settings.mongo_connection_string.startswith("mongodb+srv://")

# Configure MongoDB client with SSL/TLS settings appropriate for the connection type
# MongoDB Atlas (mongodb+srv://) requires TLS with certificate validation
# Local MongoDB (mongodb://localhost) does not use TLS
if is_atlas:
    _client = AsyncIOMotorClient(
        settings.mongo_connection_string,  # Prefers MONGODB_URI over DATABASE_URL
        tlsCAFile=certifi.where(),  # Use certifi's CA bundle for SSL certificate verification
        tls=True,  # Explicitly enable TLS for Atlas connections
        tlsAllowInvalidCertificates=False,  # Ensure certificate validation (security requirement)
        serverSelectionTimeoutMS=30000,  # 30-second timeout for server selection
        connectTimeoutMS=20000,  # 20-second timeout for initial connection
        socketTimeoutMS=20000,  # 20-second timeout for socket operations
    )
else:
    # Local MongoDB - no TLS configuration needed
    _client = AsyncIOMotorClient(
        settings.mongo_connection_string,
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
