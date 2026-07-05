import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.security import HTTPBearer
from pymongo.errors import DuplicateKeyError
from typing import List, Dict
from datetime import datetime, timezone

from app.core.security import get_current_user_from_session, SessionRoleChecker
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.db.database import (
    get_user_by_auth_id,
    get_user_by_email,
    create_user,
    update_user,
    delete_user,
    get_collection,  # Added missing import
)
from app.api.dependencies import (
    audit_request,
    sanitize_input,
    get_rate_limiter,
)

router = APIRouter()
security = HTTPBearer()

logger = logging.getLogger(__name__)

# Role-based access controls
allow_admins = SessionRoleChecker(["admin"])
allow_users_and_admins = SessionRoleChecker(["user", "admin"])


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    request: Request,
    current_user: Dict = Depends(get_current_user_from_session),
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
            target_id=current_user.get("auth_id", "unknown"),  # Use get() with default
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
            auth_id=current_user.get("auth_id", ""),
            email=current_user.get("email", ""),
            first_name=current_user.get("first_name", None),
            last_name=current_user.get("last_name", None),
            display_name=current_user.get("display_name", None),
            avatar_url=current_user.get("avatar_url", None),
            bio=current_user.get("bio", None),
            role=current_user.get("role", "user"),
            plan=current_user.get("plan", "free"),
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
            detail="Error retrieving user profile",
        )




@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: Request,
    user_update: UserUpdate,
    current_user: Dict = Depends(get_current_user_from_session),
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
            auth_id=current_user["auth_id"],
            user_data=sanitized_data,
            actor_id=current_user["auth_id"],
        )
    except Exception as e:
        msg = str(e).lower()
        logger.error("Failed to update user", exc_info=True)
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
                detail="Error updating user",
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
        target_id=current_user["auth_id"],
    )

    return updated_user


@router.delete("/me")
async def delete_profile(
    request: Request,
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=3, window=300)),
):
    """Delete the current user's account"""
    # Delete user (soft delete by default)
    success = await delete_user(
        auth_id=current_user["auth_id"], actor_id=current_user["auth_id"]
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
        target_id=current_user["auth_id"],
    )

    return {"message": "Account successfully deleted"}


@router.post("/me/avatar", status_code=status.HTTP_200_OK)
async def upload_profile_picture(
    file: UploadFile = File(...),
    request: Request = None,
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=5, window=60)),
):
    """Upload a profile picture (avatar) for the current user.

    Processes the image, stores it (cloud or local), replaces any previous
    avatar, and persists the new ``avatar_url`` on the user record.
    """
    from app.services.file_upload_service import FileUploadService

    try:
        upload_service = FileUploadService()
        avatar_url = await upload_service.process_and_save_profile_picture(
            file, current_user["auth_id"]
        )

        # Persist first; only remove the previous avatar once the new URL is
        # safely stored. If persistence fails, clean up the just-saved file so
        # we don't leak an orphan or point the record at a deleted image.
        try:
            updated_user = await update_user(
                auth_id=current_user["auth_id"],
                user_data={
                    "avatar_url": avatar_url,
                    "updated_at": datetime.now(timezone.utc),
                },
                actor_id=current_user["auth_id"],
            )
        except Exception:
            await upload_service.delete_profile_picture(avatar_url)
            raise
        if not updated_user:
            await upload_service.delete_profile_picture(avatar_url)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        old_avatar = current_user.get("avatar_url")
        if old_avatar and old_avatar != avatar_url:
            await upload_service.delete_profile_picture(old_avatar)

        if request:
            await audit_request(
                request=request,
                current_user=current_user,
                action="avatar_upload",
                resource_type="user",
                target_id=current_user["auth_id"],
                metadata={"filename": file.filename, "avatar_url": avatar_url},
            )

        return {"message": "Profile picture updated", "avatar_url": avatar_url}

    except HTTPException:
        raise
    except Exception:
        logger.error("Failed to upload profile picture", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload profile picture",
        )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(user: UserCreate):
    """Create a new user mapping in the database

    This endpoint is typically called when a user signs up via better-auth
    """
    # Check if user with this auth_id already exists
    existing_user = await get_user_by_auth_id(user.auth_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this auth ID already exists",
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
            "plan": "free",  # Entitlement default (issue #174)
        }
    )

    try:
        created_user = await create_user(user_data)
        return created_user
    except DuplicateKeyError:
        # Concurrent insert slipped past the pre-checks and hit the unique index
        # (issue #178) — surface the intended conflict, not a 500.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this auth ID or email already exists",
        )
    except Exception:
        logger.error("Error creating user", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user",
        )


@router.put("/{auth_id}", response_model=UserResponse)
async def update_user_data(
    auth_id: str,
    user_update: UserUpdate,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """Update a user's information

    Regular users can only update their own information
    Admin users can update any user's information
    """
    # Check permissions - users can only update their own data unless they're admins
    if current_user["auth_id"] != auth_id and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to update this user",
        )

    # Check if user exists
    try:
        existing_user = await get_user_by_auth_id(auth_id)
    except Exception:
        logger.error("Database operation timed out while fetching user", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Database operation timed out",
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
    update_data["updated_at"] = datetime.now(timezone.utc)

    try:
        updated_user = await update_user(auth_id, update_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return updated_user
    except HTTPException:
        raise
    except Exception:
        logger.error("Error updating user", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user",
        )


@router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(_: Dict = Depends(allow_admins)):
    """Get all users (admin only)"""
    users_collection = await get_collection("users")
    users = await users_collection.find().to_list(length=None)
    return users


@router.delete("/{auth_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    auth_id: str, current_user: Dict = Depends(get_current_user_from_session)
):
    """Delete a user account

    Regular users can only delete their own account
    Admin users can delete any user account
    """
    # Check permissions - users can only delete their own account unless they're admins
    if current_user["auth_id"] != auth_id and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this user",
        )

    # Delete the user
    try:
        result = await delete_user(auth_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return None
    except HTTPException:
        raise
    except Exception:
        logger.error("Error deleting user", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Error deleting user",
        )
