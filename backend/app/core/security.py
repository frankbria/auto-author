from typing import Optional, Dict, List
from fastapi import HTTPException, status, Request
from app.core.better_auth_session import (
    validate_better_auth_session,
    get_better_auth_user,
)
from app.db.user import as_app_user
import logging

logger = logging.getLogger(__name__)

# Password hashing lives in better-auth (TypeScript), not here. The former
# passlib-backed hash_password/verify_password/pwd_context had no production
# callers — only their own tests — so they and the passlib dep went with #342.


class SessionRoleChecker:
    """Dependency for role-based access control using session cookies.

    This is the preferred method for role checking that works with
    better-auth's cookie-based authentication.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: Dict = Depends(SessionRoleChecker(["admin"]))):
            return {"message": "Welcome, admin!"}
    """

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, request: Request) -> Dict:
        from app.core.config import settings

        # E2E Test Mode: Return test user with admin role
        if settings.BYPASS_AUTH:
            logger.debug("BYPASS_AUTH enabled - returning test admin user for role check")
            return {
                "id": "test-user-id",
                "auth_id": "test-auth-id",
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "role": "admin",  # Grant admin for testing
                "plan": "free",
                "metadata": {}
            }

        # Get user from session
        user = await get_current_user_from_session(request)

        # Check if user has one of the allowed roles
        user_role = user.get("role")
        if user_role not in self.allowed_roles:
            logger.warning(
                f"User {user.get('auth_id')} with role '{user_role}' "
                f"attempted to access endpoint requiring roles: {self.allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )

        return user


async def get_current_user_from_session(request: Request) -> Dict:
    """Get the current authenticated user from better-auth session cookies.

    This is the preferred authentication method that validates session cookies
    instead of JWT tokens. It aligns with better-auth's design which stores
    sessions in httpOnly cookies.

    For E2E testing, set BYPASS_AUTH=true to bypass authentication and return a test user.

    Args:
        request: FastAPI request object containing session cookies

    Returns:
        Dict containing user data from application database

    Raises:
        HTTPException: If authentication fails or user not found
    """
    from app.core.config import settings

    # E2E Test Mode: Bypass authentication
    if settings.BYPASS_AUTH:
        logger.debug("BYPASS_AUTH enabled - returning test user")
        return {
            "id": "test-user-id",
            "auth_id": "test-auth-id",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "user",
            "plan": "free",
            "metadata": {}
        }

    # Validate session from cookies
    session = await validate_better_auth_session(request)

    if not session:
        logger.warning("No valid session found in cookies")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please sign in."
        )

    # Extract user ID from session
    user_id = session.get("userId")
    if not user_id:
        logger.error("Session exists but has no userId")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session. Please sign in again."
        )

    # Convert ObjectId to string (better-auth stores userId as ObjectId)
    user_id = str(user_id)

    # The users doc is the user (#1263). It comes joined to the session (#826);
    # a session that holds its user id as text is joined to nothing, and its
    # user is looked up on its own. A session outliving its user (deleted
    # account, #763) is not a credential.
    joined = session.get("user")
    user = as_app_user(joined[0] if joined else await get_better_auth_user(user_id))
    if not user:
        logger.warning(f"Session for user {user_id} has no user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please sign up again."
        )

    # Explicit False: records predating the field are active (schema default).
    # deleted_at marks an account whose deletion has begun (#784, #1263).
    if user.get("is_active") is False or user.get("deleted_at"):
        logger.warning(f"Rejected session for deactivated user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account is no longer active."
        )

    # better-auth refuses to sign in an unverified address (#792). This is the
    # second lock, for a session that exists anyway.
    if user.get("emailVerified") is not True:
        logger.warning(f"Refused a session for unverified user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email address to use this account."
        )

    return user


async def optional_session_security(request: Request) -> Optional[Dict]:
    """Optional session security that returns user if authenticated, None otherwise.

    This is used for endpoints that have different behavior for authenticated
    vs unauthenticated users.

    Args:
        request: FastAPI request object

    Returns:
        User dict if authenticated, None otherwise
    """
    from app.core.config import settings

    if settings.BYPASS_AUTH:
        return None

    try:
        return await get_current_user_from_session(request)
    except HTTPException:
        return None
