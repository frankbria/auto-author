from passlib.context import CryptContext
import requests
import json
from jose import jwt
from jose.exceptions import JWTError
from typing import Optional, Dict, Any, List, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.db.database import get_user_by_clerk_id

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


async def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify a JWT token from Clerk."""
    try:
        # Use the JWKS (JSON Web Key Set) to verify the signature
        # Add leeway for clock skew and extend expiration tolerance
        payload = jwt.decode(
            token,
            settings.clerk_jwt_public_key_pem,
            algorithms=[settings.CLERK_JWT_ALGORITHM],
            audience="example.com",  # Update with your domain
            options={
                "verify_signature": True,
                "verify_exp": True,  # Still verify expiration but with leeway
                "leeway": 300,  # 5 minutes leeway for clock skew
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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict:
    """Get the current authenticated user"""
    print("In the actual get_current_user function")
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
