from fastapi import Depends, Header, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Optional, Callable, Any
import time
import re
from datetime import datetime, timedelta
from pydantic import BaseModel

# Note: verify_jwt_token is kept for backward compatibility but deprecated
# Authentication is now handled via session cookies in get_current_user_from_session
from app.core.security import verify_jwt_token
from app.db.database import get_collection
from app.db.database import create_audit_log
from app.core.config import settings

security = HTTPBearer()

# Simple in-memory cache for rate limiting
# In production, this should be replaced with Redis or similar
rate_limit_cache = {}


# MongoDB collection dependency
async def get_database_collection(collection_name: str):
    """Get a MongoDB collection"""
    return await get_collection(collection_name)


async def get_api_key(x_api_key: str = Header(None)):
    """Validate API key for external services"""
    # This would compare against a stored API key in a real application
    if x_api_key is None or x_api_key == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key is missing"
        )
    # You would validate the API key against your stored value here
    # For now, this is a placeholder
    return x_api_key


async def get_auth_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get the authenticated user from the JWT token"""
    token = credentials.credentials


def sanitize_input(text: str) -> str:
    """Basic sanitization of user input"""
    if not text:
        return text

    # Remove any potential script tags
    text = re.sub(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", "", text)

    # Remove any potential HTML tags
    text = re.sub(r"<[^>]*>", "", text)

    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    return text.strip()


class SanitizedModel(BaseModel):
    """Base class for models that automatically sanitize string fields"""

    def __init__(self, **data):
        # Sanitize any string fields before initialization
        for field_name, field_value in data.items():
            if isinstance(field_value, str):
                data[field_name] = sanitize_input(field_value)
        super().__init__(**data)


def get_rate_limiter(limit: int = 10, window: int = 60):
    """Create a rate limiter dependency with specific limits

    Args:
        limit: Maximum number of requests allowed in the time window
        window: Time window in seconds

    Returns:
        A dependency function that can be used with Depends()
    """

    async def rate_limiter(request: Request):
        """Rate limiting dependency function"""
        # Default: use client IP
        client_ip = request.client.host
        endpoint = request.url.path
        key = f"{client_ip}:{endpoint}"

        # Get current timestamp
        now = time.time()

        # Initialize or reset cache entry if needed
        if key not in rate_limit_cache or rate_limit_cache[key]["reset_at"] < now:
            rate_limit_cache[key] = {"count": 0, "reset_at": now + window}

        # Increment request count
        rate_limit_cache[key]["count"] += 1

        # Check if limit exceeded
        if rate_limit_cache[key]["count"] > limit:
            # Calculate retry-after time
            retry_after = int(rate_limit_cache[key]["reset_at"] - now)

            # Set headers for response
            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(rate_limit_cache[key]["reset_at"])),
                "Retry-After": str(retry_after),
            }

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers=headers,
            )

        # Return current rate limit status
        return {
            "limit": limit,
            "remaining": limit - rate_limit_cache[key]["count"],
            "reset": rate_limit_cache[key]["reset_at"],
        }

    return rate_limiter


# Keep this for backward compatibility but mark as deprecated
async def rate_limit(
    request: Request, limit: int = 10, window: int = 60, key_func: Callable = None
):
    """
    DEPRECATED: Use get_rate_limiter instead

    Rate limiting dependency

    Args:
        request: The FastAPI request object
        limit: Maximum number of requests allowed in the time window
        window: Time window in seconds
        key_func: Function that returns a string key for the rate limit
                  If None, uses the client's IP address
    """
    # Get rate limit key
    if key_func:
        key = key_func(request)
    else:
        # Default: use client IP
        client_ip = request.client.host
        endpoint = request.url.path
        key = f"{client_ip}:{endpoint}"

    # Get current timestamp
    now = time.time()

    # Initialize or reset cache entry if needed
    if key not in rate_limit_cache or rate_limit_cache[key]["reset_at"] < now:
        rate_limit_cache[key] = {"count": 0, "reset_at": now + window}

    # Increment request count
    rate_limit_cache[key]["count"] += 1

    # Check if limit exceeded
    if rate_limit_cache[key]["count"] > limit:
        # Calculate retry-after time
        retry_after = int(rate_limit_cache[key]["reset_at"] - now)

        # Set headers for response
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(rate_limit_cache[key]["reset_at"])),
            "Retry-After": str(retry_after),
        }

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers=headers,
        )

    # Return current rate limit status
    return {
        "limit": limit,
        "remaining": limit - rate_limit_cache[key]["count"],
        "reset": rate_limit_cache[key]["reset_at"],
    }


async def audit_request(
    request: Request,
    current_user: Dict,
    action: str,
    resource_type: str,
    target_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Log an audit entry for the current request.

    Note: Authentication is handled by get_current_user_from_session via session cookies.
    This function trusts that current_user has already been authenticated.

    Args:
        request: The FastAPI request object
        current_user: The authenticated user making the request (already validated)
        action: The action being performed (e.g., "create", "update", "delete")
        resource_type: The type of resource being accessed (e.g., "user", "book")
        target_id: The ID of the resource being accessed (if applicable)
        metadata: Optional dictionary of additional metadata to include in the audit log

    Returns:
        User payload dictionary with sub and email fields
    """
    # Create user payload from current_user (already authenticated via session)
    user_payload = {
        "sub": current_user.get("auth_id") or current_user.get("clerk_id") or current_user.get("id"),
        "email": current_user.get("email", "")
    }

    # Extract request details
    method = request.method
    path = request.url.path
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "")

    # Build details dictionary with request info
    details = {
        "method": method,
        "path": path,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "request_id": (
            str(request.state.request_id)
            if hasattr(request.state, "request_id")
            else None
        ),
    }

    # Merge in any additional metadata
    if metadata:
        details.update(metadata)

    # Get user ID - better-auth uses auth_id instead of clerk_id
    # Support both for migration period
    user_id = current_user.get("auth_id") or current_user.get("clerk_id") or current_user.get("id")

    # Create audit log
    await create_audit_log(
        action=action,
        actor_id=user_id,
        target_id=target_id or "unknown",
        resource_type=resource_type,
        details=details,
    )

    # Return user payload
    return user_payload
