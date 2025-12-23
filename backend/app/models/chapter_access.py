"""Chapter access logging models for analytics and tab persistence"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId


class ChapterAccessLog(BaseModel):
    """Model for tracking chapter access and tab interactions"""

    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: str  # Clerk user ID
    book_id: str
    chapter_id: str
    access_type: str  # "view", "edit", "create", "delete", "tab_state"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: Optional[str] = None
    tab_order: Optional[int] = None  # For tab ordering persistence
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class ChapterAccessCreate(BaseModel):
    """Schema for creating chapter access logs"""

    user_id: str
    book_id: str
    chapter_id: str
    access_type: str
    session_id: Optional[str] = None
    tab_order: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChapterAccessRead(BaseModel):
    """Schema for reading chapter access logs"""

    id: str
    user_id: str
    book_id: str
    chapter_id: str
    access_type: str
    timestamp: datetime
    session_id: Optional[str] = None
    tab_order: Optional[int] = None
    metadata: Dict[str, Any] = {}

    model_config = ConfigDict(
        from_attributes=True
    )
