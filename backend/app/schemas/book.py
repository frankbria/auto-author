from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from app.schemas.user import UserResponse


class TocItemSchema(BaseModel):
    """Schema for Table of Contents items"""

    id: str
    title: str
    level: int = 1
    description: Optional[str] = None
    parent_id: Optional[str] = None
    order: int
    content_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BookBase(BaseModel):
    """Base schema for book data"""

    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    target_audience: Optional[str] = None
    cover_image_url: Optional[str] = None
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

    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    target_audience: Optional[str] = None
    cover_image_url: Optional[str] = None
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
