from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.security import get_current_user, RoleChecker, get_clerk_user
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.db.database import (
    get_user_by_clerk_id,
    get_user_by_email,
    create_user,
    update_user,
    delete_user,
    get_collection,  # Added missing import
)

router = APIRouter()
security = HTTPBearer()

# Role-based access controls
allow_admins = RoleChecker(["admin"])
allow_users_and_admins = RoleChecker(["user", "admin"])


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Dict = Depends(get_current_user)):
    """Get the current authenticated user's information"""
    return current_user


@router.get("/clerk/{clerk_id}", response_model=Dict)
async def get_clerk_user_data(
    clerk_id: str, current_user: Dict = Depends(get_current_user)
):
    """Fetch a user's data directly from Clerk API"""
    if current_user["clerk_id"] != clerk_id and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this user's data",
        )

    clerk_user = await get_clerk_user(clerk_id)
    if not clerk_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found in Clerk"
        )

    return clerk_user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(user: UserCreate):
    """Create a new user mapping in the database

    This endpoint is typically called by webhooks when a user signs up via Clerk
    """
    # Check if user with this clerk_id already exists
    existing_user = await get_user_by_clerk_id(user.clerk_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this Clerk ID already exists",
        )

    # Check if user with this email already exists
    existing_email = await get_user_by_email(user.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    # Create user with current timestamps
    now = datetime.utcnow()
    user_data = user.dict()
    user_data.update(
        {
            "created_at": now,
            "updated_at": now,
            "books": [],
            "is_active": True,
            "role": "user",  # Default role for new users
        }
    )

    created_user = await create_user(user_data)
    return created_user


@router.put("/{clerk_id}", response_model=UserResponse)
async def update_user_data(
    clerk_id: str,
    user_update: UserUpdate,
    current_user: Dict = Depends(get_current_user),
):
    """Update a user's information

    Regular users can only update their own information
    Admin users can update any user's information
    """
    # Check permissions - users can only update their own data unless they're admins
    if current_user["clerk_id"] != clerk_id and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to update this user",
        )

    # Check if user exists
    existing_user = await get_user_by_clerk_id(clerk_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Prevent non-admin users from changing their role
    if user_update.role and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change user roles",
        )

    # Update with current timestamp
    update_data = {
        k: v for k, v in user_update.dict(exclude_unset=True).items() if v is not None
    }
    update_data["updated_at"] = datetime.utcnow()

    updated_user = await update_user(clerk_id, update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return updated_user


@router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(_: Dict = Depends(allow_admins)):
    """Get all users (admin only)"""
    users_collection = await get_collection("users")
    users = await users_collection.find().to_list(length=None)
    return users


@router.delete("/{clerk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    clerk_id: str, current_user: Dict = Depends(get_current_user)
):
    """Delete a user account

    Regular users can only delete their own account
    Admin users can delete any user account
    """
    # Check permissions - users can only delete their own account unless they're admins
    if current_user["clerk_id"] != clerk_id and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this user",
        )

    # Delete the user
    result = await delete_user(clerk_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return None
