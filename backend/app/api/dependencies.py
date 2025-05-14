from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Optional

from app.core.security import get_current_user, verify_jwt_token
from app.db.database import get_collection

security = HTTPBearer()


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

    # Verify the token
    payload = await verify_jwt_token(token)

    # Get the user ID from the token
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token"
        )

    # At this point, we've validated the token
    # We could get the user from the database if needed
    return payload
