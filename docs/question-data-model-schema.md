# Question Data Model and Database Schema

## Overview
This document describes the data models, database schema, and relationships for the question generation and management system.

## Core Data Models

### Question Model
The primary entity representing a generated question for a chapter.

```python
class Question(BaseModel):
    id: str                    # Unique identifier (UUID)
    book_id: str              # Foreign key to book
    chapter_id: str           # Foreign key to chapter
    question_text: str        # The actual question content
    question_type: QuestionType # Enum: character, plot, setting, theme, research
    difficulty: QuestionDifficulty # Enum: easy, medium, hard
    category: str             # Descriptive category label
    order: int                # Display order within chapter
    generated_at: datetime    # Timestamp of creation
    metadata: QuestionMetadata # Additional question data
```

### Question Types Enum
```python
class QuestionType(str, Enum):
    CHARACTER = "character"   # Character development, relationships, motivation
    PLOT = "plot"            # Story structure, events, conflicts
    SETTING = "setting"      # Location, time, atmosphere, world-building
    THEME = "theme"          # Messages, meanings, philosophical elements
    RESEARCH = "research"    # Factual accuracy, background information
```

### Question Difficulty Enum
```python
class QuestionDifficulty(str, Enum):
    EASY = "easy"           # Simple, straightforward questions
    MEDIUM = "medium"       # Moderate complexity requiring thought
    HARD = "hard"          # Complex, analytical questions
```

### Question Metadata
```python
class QuestionMetadata(BaseModel):
    suggested_response_length: str    # e.g., "150-300 words"
    help_text: Optional[str]         # Guidance for answering
    examples: Optional[List[str]]    # Example responses or ideas
    generation_context: Dict[str, Any] # AI generation parameters used
    quality_score: Optional[float]   # Calculated quality rating (0.0-1.0)
    user_feedback: Dict[str, Any]    # Aggregated user feedback data
```

### Question Response Model
Represents a user's answer to a specific question.

```python
class QuestionResponse(BaseModel):
    id: str                   # Unique identifier
    question_id: str          # Foreign key to question
    user_id: str             # User who created the response
    response_text: str       # The actual response content
    word_count: int          # Calculated word count
    status: ResponseStatus   # Enum: draft, completed
    created_at: datetime     # Initial creation timestamp
    updated_at: datetime     # Last modification timestamp
    last_edited_at: datetime # Last user edit timestamp
    metadata: QuestionResponseMetadata # Response tracking data
```

### Response Status Enum
```python
class ResponseStatus(str, Enum):
    DRAFT = "draft"         # Work in progress
    COMPLETED = "completed" # Finalized response
```

### Question Response Metadata
```python
class QuestionResponseMetadata(BaseModel):
    edit_history: List[Dict[str, Any]]  # History of edits
    time_spent: Optional[int]           # Seconds spent writing
    revision_count: int                 # Number of edits made
    auto_save_count: int               # Auto-save occurrences
    export_history: List[Dict[str, Any]] # Export events
```

### Question Rating Model
User feedback and rating for question quality.

```python
class QuestionRating(BaseModel):
    id: str              # Unique identifier
    question_id: str     # Foreign key to question
    user_id: str        # User providing the rating
    rating: int         # 1-5 star rating
    feedback: Optional[str] # Written feedback
    created_at: datetime # Rating timestamp
    helpful_count: int   # How many found this rating helpful
```

## Database Schema

### Questions Table
```sql
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL CHECK (length(question_text) >= 10),
    question_type VARCHAR(20) NOT NULL CHECK (question_type IN ('character', 'plot', 'setting', 'theme', 'research')),
    difficulty VARCHAR(10) NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    category VARCHAR(100) NOT NULL,
    order_index INTEGER NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    -- Indexes
    CONSTRAINT questions_order_unique UNIQUE (chapter_id, order_index),
    INDEX idx_questions_chapter (chapter_id),
    INDEX idx_questions_type (question_type),
    INDEX idx_questions_difficulty (difficulty),
    INDEX idx_questions_user (user_id),
    INDEX idx_questions_metadata_gin (metadata) USING GIN
);
```

### Question Responses Table
```sql
CREATE TABLE question_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    response_text TEXT NOT NULL CHECK (length(response_text) >= 1),
    word_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'completed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_edited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT question_responses_user_question_unique UNIQUE (question_id, user_id),
    
    -- Indexes
    INDEX idx_responses_question (question_id),
    INDEX idx_responses_user (user_id),
    INDEX idx_responses_status (status),
    INDEX idx_responses_updated (updated_at),
    INDEX idx_responses_metadata_gin (metadata) USING GIN
);
```

### Question Ratings Table
```sql
CREATE TABLE question_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    feedback TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    helpful_count INTEGER DEFAULT 0,
    
    -- Constraints
    CONSTRAINT question_ratings_user_question_unique UNIQUE (question_id, user_id),
    
    -- Indexes
    INDEX idx_ratings_question (question_id),
    INDEX idx_ratings_user (user_id),
    INDEX idx_ratings_rating (rating),
    INDEX idx_ratings_created (created_at)
);
```

### Question Generation Log Table
Tracks generation requests for analytics and debugging.

```sql
CREATE TABLE question_generation_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    generation_id VARCHAR(50) NOT NULL,
    request_params JSONB NOT NULL,
    questions_generated INTEGER DEFAULT 0,
    generation_time_ms INTEGER,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_generation_log_user (user_id),
    INDEX idx_generation_log_chapter (chapter_id),
    INDEX idx_generation_log_status (status),
    INDEX idx_generation_log_created (created_at),
    INDEX idx_generation_log_params_gin (request_params) USING GIN
);
```

## Relationships

### Entity Relationship Diagram
```
Books (1) ----< Chapters (1) ----< Questions (1) ----< QuestionResponses
                                       |
                                       ----< QuestionRatings
                                       |
                                       ----< QuestionGenerationLog
```

### Key Relationships

1. **Book → Chapters → Questions**
   - Each book contains multiple chapters
   - Each chapter can have multiple questions
   - Questions are automatically deleted when chapters are deleted (CASCADE)

2. **Questions → Question Responses**
   - One question can have one response per user
   - Responses are deleted when questions are deleted (CASCADE)

3. **Questions → Question Ratings**
   - One question can have one rating per user
   - Ratings are deleted when questions are deleted (CASCADE)

4. **User Associations**
   - Users own questions through book/chapter ownership
   - Users create responses to questions
   - Users provide ratings for questions

## Data Validation Rules

### Question Text Validation
```python
def validate_question_text(text: str) -> bool:
    """Validate question text meets requirements."""
    if len(text) < 10:
        raise ValueError("Question text must be at least 10 characters")
    if len(text) > 1000:
        raise ValueError("Question text cannot exceed 1000 characters")
    if not text.strip().endswith('?'):
        raise ValueError("Question text must end with a question mark")
    return True
```

### Response Text Validation
```python
def validate_response_text(text: str) -> bool:
    """Validate response text meets requirements."""
    if len(text.strip()) < 1:
        raise ValueError("Response text cannot be empty")
    if len(text) > 50000:  # 50k character limit
        raise ValueError("Response text cannot exceed 50,000 characters")
    return True
```

### Content Safety Validation
```python
def validate_content_safety(text: str) -> bool:
    """Check content for safety and appropriateness."""
    # Implementation would include:
    # - Profanity filtering
    # - Inappropriate content detection
    # - Spam detection
    # - Length validation
    return content_safety_service.is_safe(text)
```

## Database Migrations

### Initial Schema Creation
```sql
-- Migration: 001_create_questions_schema.sql
-- Create questions table and basic indexes
-- Add foreign key constraints
-- Set up basic validation rules
```

### Question Metadata Enhancement
```sql
-- Migration: 002_add_question_metadata.sql
-- Add metadata JSONB column
-- Create GIN index for metadata queries
-- Add quality scoring fields
```

### Response Tracking
```sql
-- Migration: 003_add_response_tracking.sql
-- Create question_responses table
-- Add edit history tracking
-- Set up cascade delete rules
```

### Rating System
```sql
-- Migration: 004_add_rating_system.sql
-- Create question_ratings table
-- Add helpful_count tracking
-- Set up rating constraints
```

## Indexing Strategy

### Performance Indexes
```sql
-- Chapter-based queries (most common)
CREATE INDEX CONCURRENTLY idx_questions_chapter_order 
ON questions (chapter_id, order_index);

-- User activity queries
CREATE INDEX CONCURRENTLY idx_responses_user_updated 
ON question_responses (user_id, updated_at DESC);

-- Question filtering
CREATE INDEX CONCURRENTLY idx_questions_type_difficulty 
ON questions (question_type, difficulty);

-- Rating aggregation
CREATE INDEX CONCURRENTLY idx_ratings_question_rating 
ON question_ratings (question_id, rating);
```

### Composite Indexes
```sql
-- Question progress queries
CREATE INDEX CONCURRENTLY idx_questions_chapter_user_status 
ON questions (chapter_id, user_id) 
INCLUDE (id, question_type, difficulty);

-- Response completion tracking
CREATE INDEX CONCURRENTLY idx_responses_chapter_status 
ON question_responses (chapter_id, status) 
WHERE status = 'completed';
```

## Query Patterns

### Common Query Examples

#### Get Questions for Chapter
```sql
SELECT q.*, qr.status as response_status
FROM questions q
LEFT JOIN question_responses qr ON q.id = qr.question_id AND qr.user_id = $1
WHERE q.chapter_id = $2
ORDER BY q.order_index;
```

#### Calculate Chapter Progress
```sql
SELECT 
    COUNT(*) as total_questions,
    COUNT(qr.id) as answered_questions,
    COUNT(CASE WHEN qr.status = 'completed' THEN 1 END) as completed_questions
FROM questions q
LEFT JOIN question_responses qr ON q.id = qr.question_id AND qr.user_id = $1
WHERE q.chapter_id = $2;
```

#### Question Quality Analytics
```sql
SELECT 
    q.question_type,
    q.difficulty,
    AVG(qrat.rating) as avg_rating,
    COUNT(qrat.id) as rating_count,
    COUNT(qr.id) as response_count
FROM questions q
LEFT JOIN question_ratings qrat ON q.id = qrat.question_id
LEFT JOIN question_responses qr ON q.id = qr.question_id
WHERE q.book_id = $1
GROUP BY q.question_type, q.difficulty;
```

## Data Lifecycle Management

### Automatic Cleanup
```sql
-- Clean up old generation logs (older than 90 days)
DELETE FROM question_generation_log 
WHERE created_at < NOW() - INTERVAL '90 days';

-- Archive completed responses older than 1 year
-- (Implementation would move to archive table)
```

### Backup Strategy
- Full database backup daily
- Transaction log backup every 15 minutes
- Point-in-time recovery capability
- Cross-region backup replication

## Performance Considerations

### Read Optimization
- Denormalize frequently accessed data
- Use materialized views for analytics
- Implement query result caching
- Optimize JOIN operations with proper indexes

### Write Optimization
- Batch insert operations for bulk generation
- Use prepared statements for repeated queries
- Implement connection pooling
- Monitor and optimize slow queries

### Scaling Strategies
- Partition large tables by book_id or date
- Implement read replicas for query distribution
- Use connection pooling and query optimization
- Consider sharding for very large datasets

---

*For implementation details, see [Developer Guide for Extending Question Functionality](developer-guide-question-system.md).*
