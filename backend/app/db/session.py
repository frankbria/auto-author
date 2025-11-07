"""
Database operations for session management
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId

from app.db import base
from app.models.session import SessionModel, SessionCreate, SessionUpdate, SessionMetadata


async def create_session(session_data: SessionCreate) -> SessionModel:
    """Create a new session

    Args:
        session_data: Session creation data

    Returns:
        Created session model
    """
    collection = base.sessions_collection

    # Generate session ID
    import secrets
    session_id = f"sess_{secrets.token_urlsafe(32)}"

    # Create session document
    now = datetime.now(timezone.utc)

    # Default expiry: 12 hours from now
    expires_at = session_data.expires_at or (now + timedelta(hours=12))

    session_doc = {
        "session_id": session_id,
        "user_id": session_data.user_id,
        "clerk_session_id": session_data.clerk_session_id,
        "created_at": now,
        "last_activity": now,
        "expires_at": expires_at,
        "is_active": True,
        "is_suspicious": False,
        "metadata": session_data.metadata.model_dump() if session_data.metadata else {},
        "request_count": 0,
        "last_endpoint": None,
        "csrf_token": f"csrf_{secrets.token_urlsafe(32)}",
    }

    # Insert into database
    result = await collection.insert_one(session_doc)

    # Retrieve and return the created session
    created_session = await collection.find_one({"_id": result.inserted_id})
    return SessionModel(**created_session)


async def get_session_by_id(session_id: str) -> Optional[SessionModel]:
    """Get a session by its ID

    Args:
        session_id: Session identifier

    Returns:
        Session model if found, None otherwise
    """
    collection = base.sessions_collection
    session_doc = await collection.find_one({"session_id": session_id})

    if session_doc:
        return SessionModel(**session_doc)
    return None


async def get_active_session_by_user(user_id: str) -> Optional[SessionModel]:
    """Get the most recent active session for a user

    Args:
        user_id: User's Clerk ID

    Returns:
        Most recent active session if found, None otherwise
    """
    collection = base.sessions_collection

    session_doc = await collection.find_one(
        {
            "user_id": user_id,
            "is_active": True,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        },
        sort=[("last_activity", -1)]
    )

    if session_doc:
        return SessionModel(**session_doc)
    return None


async def get_user_sessions(
    user_id: str,
    active_only: bool = False,
    limit: int = 10
) -> List[SessionModel]:
    """Get all sessions for a user

    Args:
        user_id: User's Clerk ID
        active_only: If True, only return active sessions
        limit: Maximum number of sessions to return

    Returns:
        List of session models
    """
    collection = base.sessions_collection

    query = {"user_id": user_id}
    if active_only:
        query["is_active"] = True
        query["expires_at"] = {"$gt": datetime.now(timezone.utc)}

    cursor = collection.find(query).sort("last_activity", -1).limit(limit)
    sessions = await cursor.to_list(length=limit)

    return [SessionModel(**session) for session in sessions]


async def update_session(session_id: str, update_data: SessionUpdate) -> Optional[SessionModel]:
    """Update a session

    Args:
        session_id: Session identifier
        update_data: Fields to update

    Returns:
        Updated session model if found, None otherwise
    """
    collection = base.sessions_collection

    # Build update document (only include fields that are set)
    update_doc = {}
    if update_data.last_activity is not None:
        update_doc["last_activity"] = update_data.last_activity
    if update_data.is_active is not None:
        update_doc["is_active"] = update_data.is_active
    if update_data.is_suspicious is not None:
        update_doc["is_suspicious"] = update_data.is_suspicious
    if update_data.metadata is not None:
        update_doc["metadata"] = update_data.metadata.model_dump()
    if update_data.request_count is not None:
        update_doc["request_count"] = update_data.request_count
    if update_data.last_endpoint is not None:
        update_doc["last_endpoint"] = update_data.last_endpoint
    if update_data.expires_at is not None:
        update_doc["expires_at"] = update_data.expires_at

    if not update_doc:
        # No updates to make
        return await get_session_by_id(session_id)

    # Update the session
    result = await collection.find_one_and_update(
        {"session_id": session_id},
        {"$set": update_doc},
        return_document=True
    )

    if result:
        return SessionModel(**result)
    return None


async def update_session_activity(session_id: str, endpoint: Optional[str] = None) -> Optional[SessionModel]:
    """Update session activity timestamp and increment request count

    Args:
        session_id: Session identifier
        endpoint: Optional endpoint path that was accessed

    Returns:
        Updated session model if found, None otherwise
    """
    collection = base.sessions_collection

    update_doc = {
        "last_activity": datetime.now(timezone.utc),
        "$inc": {"request_count": 1}
    }

    if endpoint:
        update_doc["last_endpoint"] = endpoint

    result = await collection.find_one_and_update(
        {"session_id": session_id},
        {"$set": update_doc},
        return_document=True
    )

    if result:
        return SessionModel(**result)
    return None


async def deactivate_session(session_id: str) -> bool:
    """Deactivate a session

    Args:
        session_id: Session identifier

    Returns:
        True if session was deactivated, False otherwise
    """
    collection = base.sessions_collection

    result = await collection.update_one(
        {"session_id": session_id},
        {"$set": {"is_active": False}}
    )

    return result.modified_count > 0


async def deactivate_user_sessions(user_id: str, except_session_id: Optional[str] = None) -> int:
    """Deactivate all sessions for a user

    Args:
        user_id: User's Clerk ID
        except_session_id: Optional session ID to keep active

    Returns:
        Number of sessions deactivated
    """
    collection = base.sessions_collection

    query = {"user_id": user_id}
    if except_session_id:
        query["session_id"] = {"$ne": except_session_id}

    result = await collection.update_many(
        query,
        {"$set": {"is_active": False}}
    )

    return result.modified_count


async def cleanup_expired_sessions() -> int:
    """Delete expired sessions

    Returns:
        Number of sessions deleted
    """
    collection = base.sessions_collection

    result = await collection.delete_many({
        "expires_at": {"$lt": datetime.now(timezone.utc)}
    })

    return result.deleted_count


async def get_concurrent_sessions_count(user_id: str) -> int:
    """Get count of active concurrent sessions for a user

    Args:
        user_id: User's Clerk ID

    Returns:
        Number of active sessions
    """
    collection = base.sessions_collection

    count = await collection.count_documents({
        "user_id": user_id,
        "is_active": True,
        "expires_at": {"$gt": datetime.now(timezone.utc)}
    })

    return count


async def flag_suspicious_session(session_id: str, reason: Optional[str] = None) -> bool:
    """Flag a session as suspicious

    Args:
        session_id: Session identifier
        reason: Optional reason for flagging

    Returns:
        True if session was flagged, False otherwise
    """
    collection = base.sessions_collection

    update_doc = {"is_suspicious": True}
    if reason:
        update_doc["suspicious_reason"] = reason
        update_doc["suspicious_at"] = datetime.now(timezone.utc)

    result = await collection.update_one(
        {"session_id": session_id},
        {"$set": update_doc}
    )

    return result.modified_count > 0
