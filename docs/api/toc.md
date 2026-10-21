# API: Table of Contents Endpoints

This document describes the API endpoints used for Table of Contents (TOC) generation and management in Auto Author.

## Base URL

All API endpoints are prefixed with: `/api/v1`

## Authentication

All endpoints require a signed-in user (session cookie). See [Authentication](profile.md#authentication).

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
POST /books/{book_id}/generate-questions
```

#### Parameters

| Name | Type | In | Description |
|------|------|-------|------------|
| book_id | string | path | The ID of the book |
| num_questions | integer | body, optional | 3 to 6; any other value falls back to 4 |

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
  ],
  "generated_at": "2025-05-17T14:22:00+00:00",
  "total_questions": 4
}
```

**400 Bad Request**

```json
{
  "detail": "Book summary is required for question generation"
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
  "responses_saved": 4,
  "answered_at": "2025-05-17T14:22:00+00:00",
  "ready_for_toc_generation": true
}
```

**400 Bad Request**

```json
{
  "detail": "Answer for question 0 cannot be empty"
}
```

---

### Generate Table of Contents

Generates a TOC proposal from the book summary and question responses. It does not save the TOC; save it with `PUT /books/{book_id}/toc`.

```
POST /books/{book_id}/generate-toc
```

#### Parameters

| Name | Type | In | Description |
|------|------|-------|------------|
| book_id | string | path | The ID of the book |
| question_responses | array | body, optional | `{question, answer}` pairs. If omitted, the responses saved on the book are used; with neither, the request returns 400. |

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
  "base_version": 1,
  "replaces_drafts": 0,
  "chapters_count": 8,
  "has_subchapters": true,
  "success": true
}
```

**429 Too Many Requests**

```json
{
  "detail": "Rate limit exceeded. Try again in 120 seconds."
}
```

**500 Internal Server Error**

```json
{
  "detail": "Unexpected error generating TOC"
}
```

`base_version` is the stored TOC version read before generation; send it back as `expected_version` when you save. `replaces_drafts` is the number of chapters with written content that saving this proposal would replace.

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
    "structure_notes": "..."
  },
  "status": "generated",
  "version": 1,
  "generated_at": "2023-08-10T15:22:43.511Z",
  "updated_at": null
}
```

A book with no TOC returns 200 with empty `chapters`, `status: "not_generated"` and `version: 1`. Chapter bodies (`content`) are not included. A missing book returns 404 `Book not found`.

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
| toc | object | body | The updated TOC structure. **Required** — see below |

#### Request Body

The TOC must be wrapped in a `toc` key, and `toc.chapters` must be present.
Both are required: the update replaces `table_of_contents` wholesale, so
omitting either used to save an empty TOC over the book's real chapters and
still answer `200` (#492). They are now rejected with `400`.

```json
{
  "toc": {
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
}
```

To clear a TOC deliberately, send `{"toc": {"chapters": []}}` — an explicit
empty list is accepted, an absent one is not.

#### Response

**200 OK**

```json
{
  "book_id": "book_12345",
  "toc": {
    "chapters": [...],
    "total_chapters": 8,
    "estimated_pages": 240,
    "structure_notes": "Updated structure notes"
  },
  "updated_at": "2023-08-11T09:14:22.104Z",
  "version": 2,
  "chapters_count": 8,
  "success": true
}
```

**400 Bad Request**

Returned for a malformed body. `detail` names what is wrong:

| `detail` | Cause |
|---|---|
| `Request body must contain a 'toc' object` | The `toc` wrapper is missing |
| `TOC data must be provided as an object` | `toc` is not an object |
| `TOC must contain a 'chapters' list` | `toc.chapters` is missing |
| `Chapters must be provided as a list` | `toc.chapters` is not a list |
| `Chapter {i} must be an object` | An entry in `chapters` is not an object |
| `Chapter {i} must have a title` | A chapter has no title |
| `Chapter {i} subchapters must be a list of objects` | `subchapters` is malformed |

A TOC body over the size limit returns 413. A `content` field sent on a chapter is dropped; chapter bodies are saved through their own route.

**409 Conflict** — the TOC was modified by another writer since it was read
(optimistic lock; send `expected_version` inside `toc` to opt in).

## Generation Behavior

- **Readiness gate**: `meets_minimum_requirements` is true when the summary has at least 30 words and 150 characters. The TOC wizard checks this flag alone, so a summary below it never reaches generation. `confidence_score` comes from the AI's analysis of the summary.
- **Clarifying questions**: the AI is asked for 4 questions by default about organization, audience, key concepts, applications and depth of coverage (3 to 6 on request). If none can be read from the AI reply the request fails rather than returning placeholders.
- **TOC generation**: the AI receives the summary, the book's title, genre and audience, and the question responses. The prompt asks for 6-12 chapters with 2-4 subchapters each; these are guidance, not enforced limits. Chapters are level 1 and subchapters level 2. The response carries `total_chapters`, `estimated_pages` and `structure_notes`.
- **Failures**: transient AI errors are retried with exponential backoff. If the AI's reply is not valid TOC JSON, chapter titles are extracted from its text; if nothing usable can be recovered, the request fails with a retryable `AI_INVALID_RESPONSE` error (`The AI returned an unusable table of contents. Please try again.`) rather than returning placeholder chapters.

## Rate Limiting

TOC generation is rate-limited to prevent abuse:

- TOC generation: 2 requests per 5 minutes per user (`books.py:1054`)
- Clarifying questions generation: 3 requests per 60 seconds per user (`books.py:811`)
- TOC readiness checks and saving or reading the TOC: no limit

A limited request returns 429 with a `Retry-After` header.

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

- [User Guide for TOC Generation](../user-guide/toc-generation.md)
- [Troubleshooting TOC Generation](../user-guide/troubleshooting-toc-generation.md)
- [Summary API](summary.md)
