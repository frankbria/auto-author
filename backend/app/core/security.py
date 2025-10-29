from passlib.context import CryptContext
import requests
import json
from jose import jwt, jwk
from jose.exceptions import JWTError
from typing import Optional, Dict, Any, List, Union
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.db.database import get_user_by_clerk_id
from functools import lru_cache

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


async def get_clerk_user(clerk_id: str) -> Optional[Dict]:
    """Fetch user information from Clerk API"""
    url = f"https://api.clerk.dev/v1/users/{clerk_id}"
    headers = {"Authorization": f"Bearer {settings.CLERK_API_KEY}"}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None


@lru_cache(maxsize=1)
def get_clerk_jwks() -> Dict[str, Any]:
    """Fetch JWKS from Clerk (cached)"""
    jwks_uri = f"https://{settings.CLERK_FRONTEND_API.replace('https://', '')}/.well-known/jwks.json"
    response = requests.get(jwks_uri)
    response.raise_for_status()
    return response.json()


async def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify a JWT token from Clerk."""
    try:
        # Decode header to get the key ID (kid)
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')

        # If JWT public key is provided, use it directly
        if settings.clerk_jwt_public_key_pem:
            key = settings.clerk_jwt_public_key_pem
        else:
            # Otherwise, fetch from JWKS endpoint
            jwks = get_clerk_jwks()
            # Find the key with matching kid
            key_data = None
            for key in jwks['keys']:
                if key.get('kid') == kid:
                    key_data = key
                    break

            if not key_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to find appropriate key in JWKS",
                )

            # Construct the key from JWKS
            key = jwk.construct(key_data)

        payload = jwt.decode(
            token,
            key,
            algorithms=[settings.CLERK_JWT_ALGORITHM],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": False,
                "leeway": 300,
            },
        )
        return payload
    except JWTError as e:
        # Log the specific error for debugging
        print(f"JWT verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
        )


class RoleChecker:
    """Dependency for role-based access control"""

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        token = credentials.credentials
        payload = await verify_jwt_token(token)

        # Get user from database based on Clerk ID
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID in token",
            )

        user = await get_user_by_clerk_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        # Check if user has one of the allowed roles
        if user["role"] not in self.allowed_roles:
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
    """Get the current authenticated user

    For E2E testing, set BYPASS_AUTH=true to bypass authentication and return a test user.
    """
    from app.core.config import settings

    # E2E Test Mode: Bypass authentication
    if settings.BYPASS_AUTH:
        # Return a test user for E2E tests
        return {
            "id": "test-user-id",
            "clerk_id": "test-clerk-id",
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

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token"
        )

    try:
        user = await get_user_by_clerk_id(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {e}",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user
