from passlib.context import CryptContext
from jose import jwt
from jose.exceptions import JWTError
from typing import Optional, Dict, Any, List, Union
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
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
    """Dependency for role-based access control"""

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
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
