from passlib.context import CryptContext
from jose import jwt
from jose.exceptions import JWTError
from typing import Optional, Dict, Any, List, Union
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.better_auth_session import (
    validate_better_auth_session,
    get_better_auth_user,
    get_session_token_from_cookies,
)
import logging

logger = logging.getLogger(__name__)

# Create a password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Set up the HTTP Bearer auth scheme
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a stored password against one provided by user."""
    return pwd_context.verify(plain_password, hashed_password)


async def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify a JWT token from better-auth.

    Better-auth uses HS256 algorithm with a shared secret,
    unlike Clerk which used RS256 with public key verification.

    Args:
        token: JWT token string from Authorization header

    Returns:
        Dict containing token payload with user claims

    Raises:
        HTTPException: If token is invalid, expired, or malformed
    """
    try:
        # Decode and verify the token using shared secret
        payload = jwt.decode(
            token,
            settings.BETTER_AUTH_SECRET,  # Shared secret, not public key
            algorithms=["HS256"],           # HS256 for better-auth (not RS256)
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": False,        # Better-auth doesn't use audience claim by default
                "leeway": 60,               # 60 seconds leeway for clock skew
            },
        )

        logger.debug(f"JWT token verified successfully for user: {payload.get('sub')}")
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please sign in again.",
        )
    except jwt.JWTClaimsError as e:
        logger.warning(f"JWT claims validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token claims: {str(e)}",
        )
    except JWTError as e:
        logger.error(f"JWT verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
        )


class RoleChecker:
    """Dependency for role-based access control using JWT tokens.

    DEPRECATED: Use SessionRoleChecker for cookie-based authentication instead.
    This class is maintained for backward compatibility but will be removed
    in a future version.
    """

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        import warnings
        warnings.warn(
            "RoleChecker is deprecated. Use SessionRoleChecker instead.",
            DeprecationWarning,
            stacklevel=2
        )

        from app.db.user import get_user_by_auth_id

        token = credentials.credentials
        payload = await verify_jwt_token(token)

        # Get user from database based on better-auth user ID
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID in token",
            )

        user = await get_user_by_auth_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        # Check if user has one of the allowed roles
        if user.get("role") not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
            )

        return user


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


async def optional_security(request: Request) -> Union[HTTPAuthorizationCredentials, None]:
    """Optional security dependency that doesn't auto-error"""
    from app.core.config import settings

    if settings.BYPASS_AUTH:
        return None

    bearer = HTTPBearer(auto_error=False)
    return await bearer(request)


async def get_current_user(
    credentials: Union[HTTPAuthorizationCredentials, None] = Depends(optional_security),
) -> Dict:
    """Get the current authenticated user from better-auth JWT token.

    For E2E testing, set BYPASS_AUTH=true to bypass authentication and return a test user.

    Args:
        credentials: HTTP Authorization credentials containing JWT token

    Returns:
        Dict containing user data from database

    Raises:
        HTTPException: If authentication fails or user not found
    """
    from app.core.config import settings

    # E2E Test Mode: Bypass authentication
    if settings.BYPASS_AUTH:
        # Return a test user for E2E tests
        return {
            "id": "test-user-id",
            "auth_id": "test-auth-id",  # better-auth user ID
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "user",
            "metadata": {}
        }

    # Normal authentication flow - require credentials
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials"
        )

    token = credentials.credentials
    payload = await verify_jwt_token(token)

    # Extract user ID from better-auth token (sub claim)
    user_id = payload.get("sub")
    if not user_id:
        logger.error("JWT token missing 'sub' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token"
        )

    try:
        from app.db.user import get_user_by_auth_id

        user = await get_user_by_auth_id(user_id)
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {e}",
        )

    # Auto-create user if they have a valid JWT but no backend record
    # This happens when users sign up via better-auth but haven't been synced to backend yet
    if not user:
        logger.info(
            f"User {user_id} authenticated with valid JWT but not found in backend. "
            "Auto-creating user record from JWT claims."
        )

        try:
            from app.db.user import create_user
            from datetime import datetime, timezone

            # Extract user info from JWT payload
            email = payload.get("email")
            name = payload.get("name", "")

            if not email:
                logger.error(f"JWT payload missing email for user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token: missing email claim. Please sign up again."
                )

            # Split name into first/last (fallback to email username if no name)
            name_parts = name.split(" ", 1) if name else [email.split("@")[0]]
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            # Create user in backend database
            user_data = {
                "auth_id": user_id,  # better-auth user ID
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": "user",  # Default role
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "metadata": {}
            }

            user = await create_user(user_data)
            logger.info(f"Successfully created backend user record for {email} (auth_id: {user_id})")

        except HTTPException:
            # Re-raise HTTP exceptions (like missing email)
            raise
        except Exception as e:
            logger.error(f"Failed to auto-create user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user account. Please try signing in again or contact support."
            )

    return user
