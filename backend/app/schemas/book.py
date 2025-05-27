from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from app.schemas.user import UserResponse


class ChapterStatus(str, Enum):
    """Valid chapter status values"""

    DRAFT = "draft"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    PUBLISHED = "published"


class TocItemSchema(BaseModel):
    """Schema for Table of Contents items"""

    id: str
    title: str
    level: int = 1
    description: Optional[str] = None
    parent_id: Optional[str] = None
    order: int
    content_id: Optional[str] = None

    # NEW FIELDS FOR CHAPTER TABS
    status: ChapterStatus = ChapterStatus.DRAFT
    word_count: int = 0
    last_modified: Optional[datetime] = None
    estimated_reading_time: int = 0  # minutes
    is_active_tab: bool = False  # For tab persistence

    metadata: Dict[str, Any] = {}


class BookBase(BaseModel):
    """Base schema for book data"""

    title: str = Field(..., min_length=1, max_length=100)
    subtitle: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    genre: Optional[str] = Field(None, max_length=100)
    target_audience: Optional[str] = Field(None, max_length=100)
    cover_image_url: Optional[str] = Field(None, max_length=2083)
    metadata: Dict[str, Any] = {}


class BookCreate(BookBase):
    """Schema for creating a new book"""

    class Config:
        schema_extra = {
            "example": {
                "title": "My Awesome Book",
                "subtitle": "A Journey Through Words",
                "description": "This book explores the creative writing process",
                "genre": "Non-fiction",
                "target_audience": "Writers and aspiring authors",
                "cover_image_url": "https://example.com/cover.jpg",
                "metadata": {"draft_version": "1.0"},
            }
        }


class BookUpdate(BaseModel):
    """Schema for updating an existing book"""

    title: Optional[str] = Field(..., min_length=1, max_length=100)
    subtitle: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    genre: Optional[str] = Field(None, max_length=100)
    target_audience: Optional[str] = Field(None, max_length=100)
    cover_image_url: Optional[str] = Field(None, max_length=2083)
    metadata: Optional[Dict[str, Any]] = None
    published: Optional[bool] = None

    class Config:
        schema_extra = {
            "example": {
                "title": "Updated Book Title",
                "description": "A revised description of the book",
                "published": True,
            }
        }


class TocItemCreate(BaseModel):
    """Schema for creating a new TOC item"""

    title: str
    level: int = 1
    description: Optional[str] = None
    parent_id: Optional[str] = None
    order: int
    metadata: Dict[str, Any] = {}


class TocItemUpdate(BaseModel):
    """Schema for updating a TOC item"""

    title: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    order: Optional[int] = None
    level: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class CollaboratorSchema(BaseModel):
    """Schema for book collaborators"""

    user_id: str
    role: str = "viewer"  # Options: "viewer", "editor", "co-author"
    added_at: datetime = Field(default_factory=datetime.now(timezone.utc))


class BookResponse(BookBase):
    """Schema for book data returned from API"""

    id: str
    created_at: datetime
    updated_at: datetime
    owner_id: str
    toc_items: List[TocItemSchema] = []
    published: bool = False
    collaborators: List[Dict[str, Any]] = []

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class BookDetailResponse(BookResponse):
    """Schema for detailed book information including owner data"""

    owner: Optional[Dict[str, Any]] = None


class ChapterMetadata(BaseModel):
    """Enhanced chapter metadata for tab functionality"""

    id: str
    title: str
    status: ChapterStatus = ChapterStatus.DRAFT
    word_count: int = 0
    last_modified: Optional[datetime] = None
    estimated_reading_time: int = 0
    order: int
    level: int
    has_content: bool = False
    description: Optional[str] = None
    parent_id: Optional[str] = None


class ChapterMetadataResponse(BaseModel):
    """Response schema for chapter metadata operations"""

    book_id: str
    chapters: List[ChapterMetadata]
    total_chapters: int
    completion_stats: Dict[str, int]
    last_active_chapter: Optional[str] = None


class TabStateRequest(BaseModel):
    """Schema for saving tab state"""

    active_chapter_id: str
    open_tab_ids: List[str] = Field(max_items=20)  # Limit open tabs
    tab_order: List[str]

    @validator("tab_order")
    def validate_tab_order(cls, v, values):
        open_tabs = values.get("open_tab_ids", [])
        if set(v) != set(open_tabs):
            raise ValueError(
                "tab_order must contain exactly the same chapters as open_tab_ids"
            )
        return v


class TabStateResponse(BaseModel):
    """Response schema for tab state operations"""

    active_chapter_id: str
    open_tab_ids: List[str]
    tab_order: List[str]
    last_updated: datetime


class BulkStatusUpdate(BaseModel):
    """Schema for bulk chapter status updates"""

    chapter_ids: List[str]
    status: ChapterStatus
    update_timestamp: bool = True
