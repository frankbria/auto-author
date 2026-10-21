# API Endpoints for Question Generation and Management

## Overview
These endpoints provide comprehensive question generation and management capabilities for chapter development, including AI-powered question generation, response tracking, and progress monitoring.

## Base URL
All endpoints are prefixed with `/api/v1/books/{book_id}/chapters/{chapter_id}/`

## Authentication
All endpoints require a signed-in user. The backend reads the better-auth session cookie; it does not read an `Authorization` header.

## Endpoints

### Generate Questions
Generate AI-powered questions for a specific chapter.

**POST** `/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions`

#### Request Body
```json
{
  "count": 10,
  "difficulty": "medium",
  "focus": ["character", "plot"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| count | integer | No | Number of questions to generate (1-50, default: 10) |
| difficulty | string | No | Question difficulty: "easy", "medium", "hard" |
| focus | array | No | Question types to focus on: ["character", "plot", "setting", "theme", "research"] |

#### Response
```json
{
  "questions": [
    {
      "id": "q-12345",
      "chapter_id": "ch-67890",
      "question_text": "How does the protagonist's internal conflict manifest in this chapter?",
      "question_type": "character",
      "difficulty": "medium",
      "category": "character development",
      "order": 1,
      "generated_at": "2024-01-15T10:30:00Z",
      "metadata": {
        "suggested_response_length": "150-300 words",
        "help_text": "Consider the character's emotional state and decision-making process.",
        "examples": ["Fear of commitment", "Moral dilemma"]
      }
    }
  ],
  "generation_id": "gen-abc123",
  "total": 10
}
```

#### Status Codes
- `200` - Success
- `400` - Invalid request parameters
- `401` - Unauthorized
- `404` - Book or chapter not found
- `500` - Server error

### List Questions
Retrieve questions for a chapter with optional filtering.

**GET** `/api/v1/books/{book_id}/chapters/{chapter_id}/questions`

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| status | string | No | Filter by response status: "not_answered", "draft", "completed" |
| category | string | No | Filter by question category |
| question_type | string | No | Filter by type: "character", "plot", "setting", "theme", "research" |
| page | integer | No | Page number (default: 1) |
| limit | integer | No | Items per page (default: 10, max: 50) |

#### Response
```json
{
  "questions": [
    {
      "id": "q-12345",
      "chapter_id": "ch-67890",
      "question_text": "How does the protagonist's internal conflict manifest in this chapter?",
      "question_type": "character",
      "difficulty": "medium",
      "category": "character development",
      "order": 1,
      "generated_at": "2024-01-15T10:30:00Z",
      "metadata": {
        "suggested_response_length": "150-300 words",
        "help_text": "Consider the character's emotional state.",
        "examples": []
      },
      "has_response": true,
      "response_status": "completed"
    }
  ],
  "total": 15,
  "page": 1,
  "pages": 2
}
```

### Save Question Response
Save or update a response to a specific question.

**PUT** `/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response`

#### Request Body
```json
{
  "response_text": "The protagonist struggles with self-doubt throughout this chapter...",
  "status": "draft"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| response_text | string | Yes | The response content (minimum 1 character) |
| status | string | No | Response status: "draft" or "completed" (default: "draft") |

#### Response
```json
{
  "success": true,
  "message": "Response saved successfully",
  "response": {
    "id": "resp-54321",
    "question_id": "q-12345",
    "response_text": "The protagonist struggles with self-doubt...",
    "word_count": 47,
    "status": "draft",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T11:15:00Z",
    "last_edited_at": "2024-01-15T11:15:00Z",
    "metadata": {
      "edit_history": [
        {
          "timestamp": "2024-01-15T11:15:00Z",
          "word_count": 47
        }
      ]
    }
  }
}
```

### Get Question Response
Retrieve the response for a specific question.

**GET** `/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response`

#### Response
```json
{
  "success": true,
  "has_response": true,
  "response": {
    "id": "resp-54321",
    "question_id": "q-12345",
    "response_text": "The protagonist struggles with self-doubt...",
    "word_count": 47,
    "status": "completed",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T11:15:00Z",
    "last_edited_at": "2024-01-15T11:15:00Z",
    "metadata": {
      "edit_history": [
        {
          "timestamp": "2024-01-15T11:15:00Z",
          "word_count": 47
        }
      ]
    }
  }
}
```

### Rate Question
Provide feedback and rating for a question's relevance and quality.

**POST** `/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/rating`

#### Request Body
```json
{
  "question_id": "<question_id>",
  "user_id": "<any string>",
  "rating": 4,
  "feedback": "Very helpful question that sparked new ideas."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| question_id | string | Yes | Required by the schema; the path's `question_id` is the one used |
| user_id | string | Yes | Required by the schema; the signed-in user is the one used |
| rating | integer | Yes | Rating from 1-5 stars |
| feedback | string | No | Optional written feedback |

The editor currently sends only `rating`, so its ratings are refused with `422` (#1117).

#### Response
```json
{
  "rating": { "id": "...", "question_id": "...", "rating": 4, "feedback": "...", "created_at": "..." },
  "success": true,
  "message": "Question rated successfully"
}
```

### Get Question Progress
Get progress statistics for questions in a chapter.

**GET** `/api/v1/books/{book_id}/chapters/{chapter_id}/question-progress`

#### Response
```json
{
  "total": 15,
  "completed": 8,
  "in_progress": 3,
  "progress": 0.53,
  "status": "in-progress"
}
```

| Field | Type | Description |
|-------|------|-------------|
| total | integer | Total number of questions |
| completed | integer | Questions with completed responses |
| in_progress | integer | Questions with draft responses |
| progress | float | Completion percentage (0.0 - 1.0) |
| status | string | Overall status: "not-started", "in-progress", "completed" |

### Regenerate Questions
Replace existing questions with newly generated ones.

**POST** `/api/v1/books/{book_id}/chapters/{chapter_id}/regenerate-questions`

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| preserve_responses | boolean | No | Keep questions that have responses (default: true) |

#### Request Body
```json
{
  "count": 12,
  "difficulty": "hard",
  "focus": ["theme", "research"]
}
```

#### Response
```json
{
  "questions": [
    {
      "id": "q-new123",
      "chapter_id": "ch-67890",
      "question_text": "What philosophical themes emerge from this chapter?",
      "question_type": "theme",
      "difficulty": "hard",
      "category": "thematic analysis",
      "order": 1,
      "generated_at": "2024-01-15T12:00:00Z",
      "metadata": {
        "suggested_response_length": "300+ words",
        "help_text": "Consider universal truths and deeper meanings.",
        "examples": []
      }
    }
  ],
  "generation_id": "gen-xyz789",
  "total": 12
}
```

## Error Responses

Errors use FastAPI's shape, `{"detail": ...}`. `detail` is a string, or for AI failures and conflicts an object with a `message`. Common statuses: 400 invalid input, 401 not signed in, 403 not your book, 404 book, chapter or question not found, 422 request body failed validation (for example `count` outside 1 to 50), 429 rate limit exceeded.

## Rate Limiting
Limits are per user and per route (`backend/app/api/endpoints/books.py`):

| Route | Limit |
|-------|-------|
| `POST .../generate-questions` | 3 per 2 minutes |
| `POST .../regenerate-questions` | 2 per 3 minutes |
| `POST .../questions/{question_id}/regenerate` | 2 per 3 minutes |
| Other question routes | none |

A limited request gets 429 with a `Retry-After` header.

## Best Practices

### Question Generation
- Start with smaller counts (5-10) to test relevance
- Use specific focus types for targeted questions
- Regenerate if questions don't match your needs

### Response Management
- Save responses as drafts while working
- Use auto-save functionality for data safety
- Mark as completed only when satisfied

### Performance
- Implement pagination for large question sets
- Cache question lists on the client side
- Use batch operations when possible

## SDK Examples

### JavaScript/TypeScript
```typescript
// Generate questions
const response = await fetch(`/api/v1/books/${bookId}/chapters/${chapterId}/generate-questions`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  credentials: 'include', // sends the session cookie
  body: JSON.stringify({
    count: 10,
    difficulty: 'medium',
    focus: ['character', 'plot']
  })
});

const { questions } = await response.json();
```

### Python
```python
import requests

# Save question response
response = requests.put(
    f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response",
    cookies=session_cookies,  # the better-auth session cookie
    json={
        "response_text": "My detailed response...",
        "status": "completed"
    }
)

result = response.json()
```

---

