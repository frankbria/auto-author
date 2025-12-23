from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Annotated
from pydantic import BaseModel, Field, ConfigDict, PlainValidator
from bson import ObjectId


def validate_object_id(v: Any) -> str:
    """Validate and convert ObjectId to string"""
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return v
    raise ValueError("Invalid ObjectId type")


# Pydantic v2 compatible ObjectId type
PyObjectId = Annotated[str, PlainValidator(validate_object_id)]


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

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class UserRead(UserBase):
    """Model for returning user data to the client"""

    id: str
    created_at: datetime
    updated_at: datetime
    book_ids: List[str] = []

    model_config = ConfigDict(
        from_attributes=True
    )
