from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.core.security import get_current_user, RoleChecker, get_clerk_user
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserPreferences
from app.db.database import (
    get_user_by_clerk_id,
    get_user_by_email,
    create_user,
    update_user,
    delete_user,
    get_collection,  # Added missing import
)
from app.api.dependencies import (
    rate_limit,
    audit_request,
    sanitize_input,
    get_rate_limiter,
)

router = APIRouter()
security = HTTPBearer()

# Role-based access controls
allow_admins = RoleChecker(["admin"])
allow_users_and_admins = RoleChecker(["user", "admin"])


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    request: Request,
    current_user: Dict = Depends(get_current_user),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=20, window=60)),
):
    """Get the current authenticated user's information"""
    try:
        # Log the profile view as an audit event
        await audit_request(
            request=request,
            current_user=current_user,
            action="profile_view",
            resource_type="user",
            target_id=current_user.get("clerk_id", "unknown"),  # Use get() with default
        )

        # Extract preferences or use defaults
        preferences = current_user.get("preferences", {})
        if not preferences:
            preferences = {
                "theme": "dark",
                "email_notifications": True,
                "marketing_emails": False,
            }

        # Convert MongoDB _id to string id if present
        user_id = ""
        if "_id" in current_user:
            user_id = str(current_user["_id"])
        elif "id" in current_user:
            user_id = current_user["id"]

        # Ensure the user object has all required fields for UserResponse schema
        user_response = UserResponse(
            id=user_id,
            clerk_id=current_user.get("clerk_id", ""),
            email=current_user.get("email", ""),
            first_name=current_user.get("first_name", None),
            last_name=current_user.get("last_name", None),
            display_name=current_user.get("display_name", None),
            avatar_url=current_user.get("avatar_url", None),
            bio=current_user.get("bio", None),
            role=current_user.get("role", "user"),
            created_at=current_user.get("created_at"),
            updated_at=current_user.get("updated_at"),
            books=current_user.get("books", []),
            preferences=preferences,
        )

        return user_response
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error in read_users_me: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user profile: {str(e)}",
        )


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


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: Request,
    user_update: UserUpdate,
    current_user: Dict = Depends(get_current_user),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=5, window=60)),
):
    """Update the current user's profile information"""
    # Sanitize input data
    sanitized_data = {
        k: sanitize_input(v) if isinstance(v, str) else v
        for k, v in user_update.model_dump(exclude_unset=True).items()
    }

    # Add updated_at timestamp
    sanitized_data["updated_at"] = datetime.now(timezone.utc)

    # Update user in database
    try:
        updated_user = await update_user(
            clerk_id=current_user["clerk_id"],
            user_data=sanitized_data,
            actor_id=current_user["clerk_id"],
        )
    except Exception as e:
        msg = str(e).lower()
        print(f"Error updating user: {msg}")
        if "duplicate key error" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )
        elif "operation timed out" in msg:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Database operation timed out",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating user: {e}",
            )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Log the profile update
    await audit_request(
        request=request,
        current_user=current_user,
        action="profile_update",
        resource_type="user",
        target_id=current_user["clerk_id"],
    )

    return updated_user


@router.delete("/me")
async def delete_profile(
    request: Request,
    current_user: Dict = Depends(get_current_user),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=3, window=300)),
):
    """Delete the current user's account"""
    # Delete user (soft delete by default)
    success = await delete_user(
        clerk_id=current_user["clerk_id"], actor_id=current_user["clerk_id"]
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or already deleted",
        )

    # Log the account deletion
    await audit_request(
        request=request,
        current_user=current_user,
        action="account_delete",
        resource_type="user",
        target_id=current_user["clerk_id"],
    )

    return {"message": "Account successfully deleted"}


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
    now = datetime.now(timezone.utc)
    user_data = user.model_dump()
    user_data.update(
        {
            "created_at": now,
            "updated_at": now,
            "books": [],
            "is_active": True,
            "role": "user",  # Default role for new users
        }
    )

    try:
        created_user = await create_user(user_data)
        return created_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {e}",
        )


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
    try:
        existing_user = await get_user_by_clerk_id(clerk_id)
    except Exception as e:
        msg = str(e).lower()

        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Database operation timed out: {e}",
        )
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
        k: v
        for k, v in user_update.model_dump(exclude_unset=True).items()
        if v is not None
    }
    update_data["updated_at"] = datetime.now(datetime.timezone.utc)

    try:
        updated_user = await update_user(clerk_id, update_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return updated_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {e}",
        )


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
    try:
        result = await delete_user(clerk_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Error deleting user: {e}",
        )
