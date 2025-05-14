from datetime import datetime
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


class UserBase(BaseModel):
    """Base user model with common fields"""

    clerk_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    role: str = "user"  # Default role


class UserCreate(UserBase):
    """Model used for creating a new user"""

    pass


class UserDB(UserBase):
    """User model as stored in the database"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    books: List[str] = Field(default_factory=list)
    is_active: bool = True

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class UserRead(UserBase):
    """Model for returning user data to the client"""

    id: str
    created_at: datetime
    updated_at: datetime
    books: List[str] = []

    class Config:
        orm_mode = True
