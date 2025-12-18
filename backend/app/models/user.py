from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(str):
    """Custom ObjectId type for MongoDB IDs"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)


class UserPreferences(BaseModel):
    """User preferences model"""

    theme: str = "dark"  # light, dark, system
    email_notifications: bool = True
    marketing_emails: bool = False


class UserBase(BaseModel):
    """Base user model with common fields"""

    auth_id: str  # better-auth user ID (UUID from better-auth)
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    role: str = "user"  # Default role


class UserCreate(UserBase):
    """Model used for creating a new user"""

    pass


class UserDB(UserBase):
    """User model as stored in the database"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    book_ids: List[str] = Field(
        default_factory=list
    )  # Store book IDs instead of direct references
    is_active: bool = True

    class Config:
        from_attributes = True
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class UserRead(UserBase):
    """Model for returning user data to the client"""

    id: str
    created_at: datetime
    updated_at: datetime
    book_ids: List[str] = []

    class Config:
        from_attributes = True
