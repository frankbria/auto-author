# backend/app/db/base.py

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import monitoring
from bson.objectid import ObjectId
from app.core.config import settings

logger = logging.getLogger(__name__)


class ConnectionPoolMonitor(monitoring.ConnectionPoolListener):
    """Monitor MongoDB connection pool events for debugging and metrics."""

    def connection_created(self, event):
        logger.info(f"MongoDB connection created: {event.connection_id} at {event.address}")

    def connection_ready(self, event):
        """Called when a connection has completed a handshake and is ready to use."""
        logger.debug(f"MongoDB connection ready: {event.connection_id} at {event.address}")

    def connection_closed(self, event):
        logger.info(f"MongoDB connection closed: {event.connection_id} at {event.address}, reason: {event.reason}")

    def connection_check_out_started(self, event):
        logger.debug(f"MongoDB connection checkout started at {event.address}")

    def connection_check_out_failed(self, event):
        logger.warning(f"MongoDB connection checkout failed at {event.address}, reason: {event.reason}")

    def connection_checked_out(self, event):
        logger.debug(f"MongoDB connection checked out: {event.connection_id} at {event.address}")

    def connection_checked_in(self, event):
        logger.debug(f"MongoDB connection checked in: {event.connection_id} at {event.address}")

    def pool_created(self, event):
        logger.info(f"MongoDB connection pool created at {event.address}")

    def pool_cleared(self, event):
        logger.warning(f"MongoDB connection pool cleared at {event.address}")

    def pool_closed(self, event):
        logger.info(f"MongoDB connection pool closed at {event.address}")


# Production-ready connection pool configuration
# maxPoolSize: Maximum connections in the pool (handles production load)
# minPoolSize: Minimum connections to keep warm (reduces connection overhead)
# serverSelectionTimeoutMS: Fast failure detection for unreachable servers
# waitQueueTimeoutMS: Prevents connection starvation under heavy load
# maxIdleTimeMS: Clean up idle connections to free resources
_client = AsyncIOMotorClient(
    settings.DATABASE_URI,
    maxPoolSize=50,  # Handle production load
    minPoolSize=10,  # Maintain warm connections
    serverSelectionTimeoutMS=5000,  # 5 second timeout for server selection
    waitQueueTimeoutMS=5000,  # 5 second timeout for connection acquisition
    maxIdleTimeMS=60000,  # Close connections idle for 60 seconds
    event_listeners=[ConnectionPoolMonitor()],
)
_db = _client[settings.DATABASE_NAME]

logger.info(
    f"MongoDB client initialized with pool settings: "
    f"maxPoolSize=50, minPoolSize=10, serverSelectionTimeoutMS=5000, "
    f"waitQueueTimeoutMS=5000, maxIdleTimeMS=60000"
)

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
