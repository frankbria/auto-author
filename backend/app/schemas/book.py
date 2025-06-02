from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
from app.schemas.user import UserResponse


class ChapterStatus(str, Enum):
    """Valid chapter status values"""

    DRAFT = "draft"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    PUBLISHED = "published"


class QuestionType(str, Enum):
    """Types of questions that can be generated for a chapter"""
    
    CHARACTER = "character"
    PLOT = "plot"
    SETTING = "setting"
    THEME = "theme"
    RESEARCH = "research"


class QuestionDifficulty(str, Enum):
    """Difficulty levels for questions"""
    
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ResponseStatus(str, Enum):
    """Status values for question responses"""
    
    DRAFT = "draft"
    COMPLETED = "completed"


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


class QuestionMetadata(BaseModel):
    """Metadata for questions"""
    
    suggested_response_length: str
    help_text: Optional[str] = None
    examples: Optional[List[str]] = None


class QuestionBase(BaseModel):
    """Base schema for chapter questions"""
    
    question_text: str = Field(..., min_length=10, max_length=1000)
    question_type: QuestionType
    difficulty: QuestionDifficulty
    category: str
    order: int
    metadata: QuestionMetadata


class QuestionCreate(QuestionBase):
    """Schema for creating a new question"""
    
    chapter_id: str


class Question(QuestionBase):
    """Schema for a complete question"""
    
    id: str
    chapter_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QuestionResponseMetadata(BaseModel):
    """Metadata for question responses including edit history"""
    
    edit_history: List[Dict[str, Any]] = Field(default_factory=list)


class QuestionResponseBase(BaseModel):
    """Base schema for question responses"""
    
    response_text: str = Field(..., min_length=1)
    word_count: int = 0
    status: ResponseStatus = ResponseStatus.DRAFT


class QuestionResponseCreate(QuestionResponseBase):
    """Schema for creating a new question response"""
    
    question_id: str


class QuestionResponse(QuestionResponseBase):
    """Schema for a complete question response"""
    
    id: str
    question_id: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_edited_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: QuestionResponseMetadata = Field(default_factory=QuestionResponseMetadata)


class QuestionRating(BaseModel):
    """Schema for rating a question's relevance/quality"""
    
    question_id: str
    user_id: str
    rating: int = Field(..., ge=1, le=5)  # 1-5 star rating
    feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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

    @field_validator("tab_order")
    @classmethod
    def validate_tab_order(cls, v, info):
        # In Pydantic v2, we need to use model_validator for cross-field validation
        # For now, just validate the tab_order itself
        if len(v) != len(set(v)):
            raise ValueError("tab_order contains duplicate entries")
        return v

    @model_validator(mode="after")
    def validate_tab_consistency(self):
        """Validate that open_tab_ids and tab_order are consistent"""
        open_tabs_set = set(self.open_tab_ids)
        tab_order_set = set(self.tab_order)

        # Ensure all open tabs are present in tab_order
        if not open_tabs_set.issubset(tab_order_set):
            missing_tabs = open_tabs_set - tab_order_set
            raise ValueError(
                f"tab_order must contain all chapters from open_tab_ids. Missing: {missing_tabs}"
            )

        # Ensure no duplicates in open_tab_ids
        if len(self.open_tab_ids) != len(open_tabs_set):
            raise ValueError("open_tab_ids contains duplicate entries")

        return self


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


# --- Question API Request/Response Schemas ---

class GenerateQuestionsRequest(BaseModel):
    """Request schema for generating questions for a chapter"""
    
    count: Optional[int] = Field(10, ge=1, le=50)
    difficulty: Optional[QuestionDifficulty] = None
    focus: Optional[List[QuestionType]] = None


class GenerateQuestionsResponse(BaseModel):
    """Response schema for generated questions"""
    
    questions: List[Question]
    generation_id: str
    total: int


class QuestionListParams(BaseModel):
    """Query parameters for listing questions"""
    
    status: Optional[str] = None
    category: Optional[str] = None
    question_type: Optional[QuestionType] = None
    page: int = 1
    limit: int = 10


class QuestionListResponse(BaseModel):
    """Response schema for listing questions"""
    
    questions: List[Question]
    total: int
    page: int
    pages: int


class QuestionProgressResponse(BaseModel):
    """Response schema for chapter question progress"""
    
    total: int
    completed: int
    progress: float  # 0.0 to 1.0
    status: str  # "not-started", "in-progress", "completed"
