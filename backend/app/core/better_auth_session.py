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

import asyncio
import base64
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

from fastapi import Request
from pymongo.errors import PyMongoError

from app.core.config import is_deployed_env, settings
from app.core.reporting import report_failure
from app.db.base import get_collection

logger = logging.getLogger(__name__)

# How long a session lookup may wait for the database. The driver's own limit
# is thirty seconds, which is how long a signed-in request used to hang (#1007).
SESSION_LOOKUP_TIMEOUT_SECONDS = 5


class SessionStoreUnavailable(Exception):
    """The session could not be checked because the database could not be asked.

    Not the same as a session that is not there: that one is the user's to fix
    by signing in, this one is ours. The app answers it 503, not 401, because
    the frontend ends the session in the browser on a 401 (#796, #1007).
    """


def _in_time(lookup):
    """A database call for a session, given up on after the lookup's own limit."""
    return asyncio.wait_for(lookup, SESSION_LOOKUP_TIMEOUT_SECONDS)

# better-auth sets the __Secure- name over HTTPS and the bare one over plain
# HTTP (local development).
SECURE_COOKIE_NAME = "__Secure-better-auth.session_token"
DEV_COOKIE_NAME = "better-auth.session_token"


def _accepted_cookie_names() -> List[str]:
    """A deployed environment accepts only the __Secure- name (#795).

    A browser will not let plain http or a script set a __Secure- cookie, so it
    cannot be planted by a sibling subdomain or a network attacker. The bare
    name can (cookie tossing, login CSRF), and no deployed frontend sets it.
    """
    if is_deployed_env():
        return [SECURE_COOKIE_NAME]
    return [SECURE_COOKIE_NAME, DEV_COOKIE_NAME]


def _verified_token(cookie_value: str) -> Optional[str]:
    """The session token, if the cookie carries better-auth's signature for it.

    better-call sets the cookie as url-encoded "<token>.<signature>", where the
    signature is base64(HMAC-SHA256(BETTER_AUTH_SECRET, token)). Without this
    check the token alone would authenticate, and the token is readable by any
    script on the page from /get-session and /list-sessions (#795).

    One secret only: better-auth's rotation list (``BETTER_AUTH_SECRETS``) signs
    with its first entry, which this check does not know. Turning rotation on
    in the frontend means teaching this function the list first.
    """
    token, dot, signature = unquote(cookie_value).rpartition(".")
    if not dot or not token:
        return None
    expected = base64.b64encode(
        hmac.new(settings.BETTER_AUTH_SECRET.encode(), token.encode(), hashlib.sha256).digest()
    )
    # Bytes on both sides: compare_digest raises on a non-ASCII str.
    if not hmac.compare_digest(signature.encode(), expected):
        return None
    return token


async def get_session_token_from_cookies(request: Request) -> Optional[str]:
    """Extract the verified better-auth session token from request cookies.

    Returns:
        The session token, or None when there is no cookie or its signature
        does not verify. A cookie that fails does not fall through to the
        next name.
    """
    for cookie_name in _accepted_cookie_names():
        cookie_value = request.cookies.get(cookie_name)
        if cookie_value:
            token = _verified_token(cookie_value)
            if token is None:
                logger.warning(f"Rejected {cookie_name} cookie: signature does not verify")
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
        # Get the session collection using the shared MongoDB client
        session_collection = await get_collection("session")

        # Find session by token
        session = await _in_time(session_collection.find_one({"token": session_token}))

        if not session:
            logger.warning("Session not found for provided token")
            return None

        # Check if session has expired
        expires_at = session.get("expiresAt")
        if not expires_at:
            # Fail closed. `if expires_at:` meant a session document missing the
            # field skipped the expiry check altogether and was treated as
            # valid — an unexpirable session from a malformed or
            # partially-written record (#352). A session we cannot date is a
            # session we cannot trust.
            logger.warning(
                "Session %s has no expiresAt; rejecting as invalid",
                session.get("_id"),
            )
            return None

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
                await _in_time(session_collection.delete_one({"_id": session["_id"]}))
                return None

        # Update last activity time
        await _in_time(session_collection.update_one(
            {"_id": session["_id"]},
            {"$set": {"updatedAt": datetime.now(timezone.utc)}}
        ))

        logger.debug(f"Session validated for user: {session.get('userId')}")
        return session

    except (PyMongoError, asyncio.TimeoutError) as e:
        logger.error(f"Session could not be checked: {type(e).__name__}: {str(e)}")
        report_failure("session-validation", e)
        raise SessionStoreUnavailable() from e
    except Exception as e:
        # The record itself makes no sense: refused, as a session that is not there.
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
        # Get the user collection using the shared MongoDB client
        user_collection = await get_collection("user")

        # Find user by ID (better-auth stores ID as 'id' field, not '_id')
        user = await _in_time(user_collection.find_one({"id": user_id}))

        if not user:
            # Try with _id as fallback (convert string to ObjectId)
            from bson import ObjectId
            try:
                user = await _in_time(user_collection.find_one({"_id": ObjectId(user_id)}))
            except Exception:
                logger.debug(f"Could not convert user_id to ObjectId: {user_id}")

        if user:
            logger.debug(f"Found better-auth user {user_id}")

        return user

    except (PyMongoError, asyncio.TimeoutError) as e:
        logger.error(f"Better-auth user {user_id} could not be looked up: {type(e).__name__}: {str(e)}")
        report_failure("session-validation", e)
        raise SessionStoreUnavailable() from e
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
