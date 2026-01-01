from passlib.context import CryptContext
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, Request
from app.core.better_auth_session import (
    validate_better_auth_session,
    get_better_auth_user,
)
import logging

logger = logging.getLogger(__name__)

# Create a password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a stored password against one provided by user."""
    return pwd_context.verify(plain_password, hashed_password)


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

    # Get better-auth user to extract email/name for auto-creation
    better_auth_user = await get_better_auth_user(user_id)

    # Try to find user in application database
    try:
        from app.db.user import get_user_by_auth_id

        user = await get_user_by_auth_id(user_id)
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {e}",
        )

    # Auto-create user if they have a valid session but no backend record
    if not user:
        if not better_auth_user:
            logger.error(f"User {user_id} not found in better-auth or application database")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found. Please sign up again."
            )

        logger.info(
            f"User {user_id} authenticated with valid session but not found in backend. "
            "Auto-creating user record from better-auth data."
        )

        try:
            from app.db.user import create_user
            from datetime import datetime, timezone

            # Extract user info from better-auth user
            email = better_auth_user.get("email")
            name = better_auth_user.get("name", "")

            if not email:
                logger.error(f"Better-auth user {user_id} has no email")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid user: missing email. Please sign up again."
                )

            # Split name into first/last (fallback to email username if no name)
            name_parts = name.split(" ", 1) if name else [email.split("@")[0]]
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            # Create user in backend database
            user_data = {
                "auth_id": user_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": "user",
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "metadata": {}
            }

            user = await create_user(user_data)
            logger.info(f"Successfully created backend user record for {email} (auth_id: {user_id})")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to auto-create user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user account. Please try signing in again or contact support."
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
