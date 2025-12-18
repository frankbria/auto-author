from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId
from app.models.user import PyObjectId


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


class QuestionMetadata(BaseModel):
    """Metadata for questions"""

    suggested_response_length: str
    help_text: Optional[str] = None
    examples: Optional[List[str]] = None


class Question(BaseModel):
    """Database model for chapter questions"""

    id: str
    chapter_id: str
    question_text: str
    question_type: str  # character, plot, setting, theme, research
    difficulty: str  # easy, medium, hard
    category: str
    order: int
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: QuestionMetadata


class QuestionResponseEditHistory(BaseModel):
    """Model for tracking edits to question responses"""

    timestamp: datetime
    word_count: int


class QuestionResponseMetadata(BaseModel):
    """Metadata for question responses"""

    edit_history: List[QuestionResponseEditHistory] = Field(default_factory=list)


class QuestionResponse(BaseModel):
    """Database model for question responses"""

    id: str
    question_id: str
    user_id: str
    response_text: str
    word_count: int = 0
    status: str = "draft"  # draft or completed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_edited_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: QuestionResponseMetadata = Field(default_factory=QuestionResponseMetadata)


class QuestionRating(BaseModel):
    """Database model for question ratings"""

    id: str
    question_id: str
    user_id: str
    rating: int  # 1-5 star rating
    feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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


class BookCreate(BookBase):
    """Model used for creating a new book"""

    pass


class BookDB(BookBase):
    """Book model as stored in the database"""

    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    toc_items: List[TocItem] = Field(default_factory=list)
    published: bool = False
    collaborators: List[Dict[str, str]] = Field(default_factory=list)

    class Config:
        from_attributes = True
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class BookRead(BookBase):
    """Model for returning book data to the client"""

    id: str
    created_at: datetime
    updated_at: datetime
    toc_items: List[TocItem] = []
    published: bool = False

    class Config:
        from_attributes = True
