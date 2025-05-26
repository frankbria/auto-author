# API: Table of Contents Endpoints

This document describes the API endpoints used for Table of Contents (TOC) generation and management in Auto Author.

## Base URL

All API endpoints are prefixed with: `/api/v1`

## Authentication

All endpoints require authentication via Clerk JWT token in the Authorization header:

```
Authorization: Bearer <clerk_jwt_token>
```

## Endpoints

### Check TOC Readiness

Checks if a book's summary is ready for TOC generation.

```
GET /books/{book_id}/toc-readiness
```

#### Parameters

| Name | Type | In | Description |
|------|------|-------|------------|
| book_id | string | path | The ID of the book to check |

#### Response

**200 OK**

```json
{
  "is_ready_for_toc": true,
  "confidence_score": 0.85,
  "analysis": "Your summary has sufficient detail to generate a comprehensive TOC.",
  "suggestions": [],
  "word_count": 320,
  "character_count": 1950,
  "meets_minimum_requirements": true
}
```

**200 OK** (Not Ready)

```json
{
  "is_ready_for_toc": false,
  "confidence_score": 0.42,
  "analysis": "Your summary lacks clear thematic structure and sufficient detail.",
  "suggestions": [
    "Add more details about key topics",
    "Clarify the main themes or arguments",
    "Include information about the intended audience",
    "Specify the overall approach or structure"
  ],
  "word_count": 65,
  "character_count": 380,
  "meets_minimum_requirements": false
}
```

**404 Not Found**

```json
{
  "detail": "Book not found"
}
```

**403 Forbidden**

```json
{
  "detail": "Not authorized to access this book"
}
```

---

### Generate Clarifying Questions

Generates questions to clarify aspects of the book summary for better TOC generation.

```
GET /books/{book_id}/generate-questions
```

#### Parameters

| Name | Type | In | Description |
|------|------|-------|------------|
| book_id | string | path | The ID of the book |

#### Response

**200 OK**

```json
{
  "book_id": "book_12345",
  "questions": [
    "What genre best describes your book?",
    "Who is the primary audience for your book?",
    "Would you prefer a chronological or thematic organization?",
    "Are there specific key topics that must be included as chapters?"
  ]
}
```

**400 Bad Request**

```json
{
  "detail": "Summary is too short to generate questions"
}
```

**404 Not Found**

```json
{
  "detail": "Book not found"
}
```

---

### Save Question Responses

Saves user responses to clarifying questions for use in TOC generation.

```
PUT /books/{book_id}/question-responses
```

#### Parameters

| Name | Type | In | Description |
|------|------|-------|------------|
| book_id | string | path | The ID of the book |
| responses | array | body | Array of question-response pairs |

#### Request Body

```json
{
  "responses": [
    {
      "question": "What genre best describes your book?",
      "answer": "Business / Professional Development"
    },
    {
      "question": "Who is the primary audience for your book?",
      "answer": "Mid-career professionals looking to advance to leadership positions"
    },
    {
      "question": "Would you prefer a chronological or thematic organization?",
      "answer": "Thematic, organized around key skills and concepts"
    },
    {
      "question": "Are there specific key topics that must be included as chapters?",
      "answer": "Communication skills, strategic thinking, team management, and conflict resolution"
    }
  ]
}
```

#### Response

**200 OK**

```json
{
  "book_id": "book_12345",
  "saved": true,
  "response_count": 4
}
```

**400 Bad Request**

```json
{
  "detail": "Invalid question response format"
}
```

---

### Generate Table of Contents

Generates a TOC based on the book summary and question responses.

```
POST /books/{book_id}/generate-toc
```

#### Parameters

| Name | Type | In | Description |
|------|------|-------|------------|
| book_id | string | path | The ID of the book |

#### Response

**200 OK**

```json
{
  "book_id": "book_12345",
  "toc": {
    "chapters": [
      {
        "id": "ch1",
        "title": "Foundations of Leadership",
        "description": "Core concepts and principles of effective leadership",
        "level": 1,
        "order": 1,
        "subchapters": [
          {
            "id": "ch1-1",
            "title": "Leadership Styles and Approaches",
            "description": "Overview of different leadership philosophies and when to apply them",
            "level": 2,
            "order": 1
          },
          {
            "id": "ch1-2",
            "title": "Leadership vs. Management",
            "description": "Distinguishing between leadership and management roles",
            "level": 2,
            "order": 2
          }
        ]
      },
      {
        "id": "ch2",
        "title": "Strategic Communication Skills",
        "description": "Developing advanced communication abilities for leadership contexts",
        "level": 1,
        "order": 2,
        "subchapters": []
      }
    ],
    "total_chapters": 8,
    "estimated_pages": 240,
    "structure_notes": "This TOC is organized thematically around key leadership competencies, starting with foundations and progressing to advanced concepts. The structure addresses the target audience of mid-career professionals by focusing on practical skills and real-world applications."
  },
  "generated_at": "2023-08-10T15:22:43.511Z",
  "chapters_count": 8,
  "has_subchapters": true,
  "success": true
}
```

**429 Too Many Requests**

```json
{
  "detail": "Rate limit exceeded: 2 requests per 5 minutes"
}
```

**500 Internal Server Error**

```json
{
  "detail": "Error generating TOC: AI service timeout"
}
```

---

### Get Current TOC

Retrieves the current TOC for a book.

```
GET /books/{book_id}/toc
```

#### Parameters

| Name | Type | In | Description |
|------|------|-------|------------|
| book_id | string | path | The ID of the book |

#### Response

**200 OK**

```json
{
  "book_id": "book_12345",
  "toc": {
    "chapters": [...],
    "total_chapters": 8,
    "estimated_pages": 240,
    "structure_notes": "...",
    "generated_at": "2023-08-10T15:22:43.511Z",
    "status": "generated",
    "version": 1
  }
}
```

**404 Not Found**

```json
{
  "detail": "TOC not found for this book"
}
```

---

### Update TOC

Updates an existing TOC structure.

```
PUT /books/{book_id}/toc
```

#### Parameters

| Name | Type | In | Description |
|------|------|-------|------------|
| book_id | string | path | The ID of the book |
| toc | object | body | The updated TOC structure |

#### Request Body

```json
{
  "chapters": [
    {
      "id": "ch1",
      "title": "Updated Chapter Title",
      "description": "Updated chapter description",
      "level": 1,
      "order": 1,
      "subchapters": [...]
    },
    ...
  ],
  "total_chapters": 8,
  "estimated_pages": 240,
  "structure_notes": "Updated structure notes"
}
```

#### Response

**200 OK**

```json
{
  "book_id": "book_12345",
  "toc": {
    "chapters": [...],
    "total_chapters": 8,
    "estimated_pages": 240,
    "structure_notes": "Updated structure notes",
    "generated_at": "2023-08-10T15:22:43.511Z",
    "updated_at": "2023-08-11T09:14:22.104Z",
    "status": "edited",
    "version": 2
  },
  "success": true
}
```

**400 Bad Request**

```json
{
  "detail": "Invalid TOC structure"
}
```

## Rate Limiting

TOC generation is rate-limited to prevent abuse:

- 2 TOC generation requests per 5 minutes per user
- Clarifying questions generation: 5 requests per minute per user
- TOC readiness checks: 10 requests per minute per user

## Error Codes

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| 400 | Bad Request | Invalid input parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authenticated but not authorized for this resource |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error processing request |

## Related Documentation

- [TOC Generation Requirements](toc-generation-requirements.md)
- [User Guide for TOC Generation](user-guide-toc-generation.md)
- [Troubleshooting TOC Generation](troubleshooting-toc-generation.md)
