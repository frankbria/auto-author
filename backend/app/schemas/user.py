from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


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
    clerk_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    role: str = "user"
    book_ids: List[str] = []
    preferences: Optional[UserPreferences] = Field(default_factory=UserPreferences)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class UserCreate(UserBase):
    """Schema for creating a new user"""

    clerk_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        schema_extra = {
            "example": {
                "clerk_id": "user_2NxAa1pyy8THf937QUAhKR2tXCI",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "display_name": "John Doe",
                "avatar_url": "https://example.com/avatar.jpg",
                "metadata": {},
            }
        }


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

    class Config:
        schema_extra = {
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


class UserInDB(UserResponse):
    """Internal schema for user data in database"""

    is_active: bool = True
