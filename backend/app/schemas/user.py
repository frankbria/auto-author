from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UserPreferences(BaseModel):
    """User preferences schema"""

    theme: str = "dark"  # light, dark, system
    email_notifications: bool = True
    marketing_emails: bool = False


class UserBase(BaseModel):
    """Base Pydantic schema for user data"""

    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    preferences: Optional[UserPreferences] = None


class UserResponse(UserBase):
    """Schema for user data returned from API"""

    id: Optional[str] = None
    auth_id: str  # better-auth user ID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    role: str = "user"
    book_ids: List[str] = []
    preferences: Optional[UserPreferences] = Field(default_factory=UserPreferences)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class UserCreate(UserBase):
    """Schema for creating a new user"""

    auth_id: str  # better-auth user ID
    email: Optional[EmailStr] = None  # Override to make optional for webhooks
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "auth_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "display_name": "John Doe",
                "avatar_url": "https://example.com/avatar.jpg",
                "metadata": {},
            }
        }
    )


class UserUpdate(BaseModel):
    """Schema for updating an existing user"""

    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    preferences: Optional[UserPreferences] = None
    metadata: Optional[Dict[str, Any]] = None
    role: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "updated@example.com",
                "first_name": "Updated",
                "last_name": "Name",
                "display_name": "Updated Name",
                "avatar_url": "https://example.com/new-avatar.jpg",
                "bio": "Author and educator with 10+ years experience",
                "preferences": {
                    "theme": "dark",
                    "email_notifications": True,
                    "marketing_emails": False,
                },
                "metadata": {"preferences": {"theme": "dark"}},
                "role": "admin",
            }
        }
    )


class UserInDB(UserResponse):
    """Internal schema for user data in database"""

    is_active: bool = True
