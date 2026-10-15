from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId


class TocItem(BaseModel):
    """Table of Contents item model"""

    id: str
    title: str
    level: int = 1  # 1 = chapter, 2 = section, etc.
    description: Optional[str] = None
    parent_id: Optional[str] = None
    order: int
    content_id: Optional[str] = None  # Reference to content collection if needed

    # NEW FIELDS FOR CHAPTER TABS
    status: str = "draft"  # draft, in-progress, completed, published
    word_count: int = 0
    last_modified: Optional[datetime] = None
    estimated_reading_time: int = 0  # minutes
    is_active_tab: bool = False  # For tab persistence

    metadata: Dict[str, Any] = Field(default_factory=dict)


class BookBase(BaseModel):
    """Base book model with common fields"""

    title: str = Field(..., min_length=1, max_length=100)
    subtitle: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    genre: Optional[str] = Field(None, max_length=100)
    target_audience: Optional[str] = Field(None, max_length=100)
    cover_image_url: Optional[str] = Field(None, max_length=2083)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    owner_id: str  # Reference to the user's auth_id (better-auth user ID)


class BookDB(BookBase):
    """Book model as stored in the database"""

    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    toc_items: List[TocItem] = Field(default_factory=list)
    published: bool = False
    collaborators: List[Dict[str, str]] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
