"""
Better-auth session validation module.

This module validates better-auth session cookies and retrieves user data
from MongoDB. It replaces JWT-based authentication with cookie-based
session authentication.

Better-auth stores sessions in the 'session' collection with the following schema:
- id: String (session ID)
- token: String (session token from cookie)
- userId: String (reference to user in 'user' collection)
- expiresAt: Date (session expiration time)
- createdAt: Date (session creation time)
- updatedAt: Date (last activity time)
- ipAddress: String (optional)
- userAgent: String (optional)
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Request, HTTPException, status
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cookie names used by better-auth (with and without __Secure- prefix)
SESSION_COOKIE_NAMES = [
    "__Secure-better-auth.session_token",  # Production (HTTPS)
    "better-auth.session_token",            # Development (HTTP)
]


def _get_mongo_client() -> AsyncIOMotorClient:
    """Get MongoDB client for session validation.

    Note: This creates a separate client to avoid circular imports with db.base.
    In production, consider using a shared connection pool.
    """
    return AsyncIOMotorClient(settings.DATABASE_URL)


async def get_session_token_from_cookies(request: Request) -> Optional[str]:
    """Extract better-auth session token from request cookies.

    Tries both __Secure- prefixed cookies (production) and
    non-prefixed cookies (development).

    Args:
        request: FastAPI request object

    Returns:
        Session token string or None if not found
    """
    for cookie_name in SESSION_COOKIE_NAMES:
        token = request.cookies.get(cookie_name)
        if token:
            logger.debug(f"Found session token in cookie: {cookie_name}")
            return token

    return None


async def validate_better_auth_session(request: Request) -> Optional[Dict[str, Any]]:
    """Validate better-auth session from cookies and return session data.

    This function:
    1. Extracts the session token from cookies
    2. Looks up the session in MongoDB
    3. Validates the session hasn't expired
    4. Returns the session data including user ID

    Args:
        request: FastAPI request object containing cookies

    Returns:
        Dict containing session data with userId, or None if invalid

    Raises:
        HTTPException: If session is expired or invalid
    """
    # Extract session token from cookies
    session_token = await get_session_token_from_cookies(request)

    if not session_token:
        logger.debug("No session token found in cookies")
        return None

    try:
        # Connect to MongoDB and look up the session
        client = _get_mongo_client()
        db = client[settings.DATABASE_NAME]
        session_collection = db.get_collection("session")

        # Find session by token
        session = await session_collection.find_one({"token": session_token})

        if not session:
            logger.warning(f"Session not found for token: {session_token[:10]}...")
            return None

        # Check if session has expired
        expires_at = session.get("expiresAt")
        if expires_at:
            # Handle both datetime objects and ISO strings
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            elif not isinstance(expires_at, datetime):
                # Try to convert from timestamp if it's a number
                try:
                    expires_at = datetime.fromtimestamp(float(expires_at), tz=timezone.utc)
                except (ValueError, TypeError):
                    logger.error(f"Invalid expiresAt format: {expires_at}")
                    return None

            # Make sure we're comparing timezone-aware datetimes
            now = datetime.now(timezone.utc)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if expires_at < now:
                logger.info(f"Session expired at {expires_at} (current time: {now})")
                # Optionally clean up expired session
                await session_collection.delete_one({"_id": session["_id"]})
                return None

        # Update last activity time
        await session_collection.update_one(
            {"_id": session["_id"]},
            {"$set": {"updatedAt": datetime.now(timezone.utc)}}
        )

        logger.debug(f"Session validated for user: {session.get('userId')}")
        return session

    except Exception as e:
        logger.error(f"Error validating session: {str(e)}")
        return None


async def get_better_auth_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user data from better-auth's user collection.

    Better-auth stores users in the 'user' collection with fields:
    - id: String (user ID)
    - email: String
    - name: String (optional)
    - image: String (optional)
    - emailVerified: Boolean
    - createdAt: Date
    - updatedAt: Date

    Args:
        user_id: The better-auth user ID from the session

    Returns:
        Dict containing user data, or None if not found
    """
    try:
        client = _get_mongo_client()
        db = client[settings.DATABASE_NAME]
        user_collection = db.get_collection("user")

        # Find user by ID (better-auth stores ID as 'id' field, not '_id')
        user = await user_collection.find_one({"id": user_id})

        if not user:
            # Try with _id as fallback
            user = await user_collection.find_one({"_id": user_id})

        if user:
            logger.debug(f"Found better-auth user: {user.get('email')}")

        return user

    except Exception as e:
        logger.error(f"Error fetching better-auth user {user_id}: {str(e)}")
        return None


async def get_user_from_session(request: Request) -> Optional[Dict[str, Any]]:
    """Convenience function to get user data from session cookies.

    This combines session validation and user lookup into a single call.

    Args:
        request: FastAPI request object

    Returns:
        Dict containing better-auth user data, or None if not authenticated
    """
    session = await validate_better_auth_session(request)

    if not session:
        return None

    user_id = session.get("userId")
    if not user_id:
        logger.warning("Session exists but has no userId")
        return None

    return await get_better_auth_user(user_id)
