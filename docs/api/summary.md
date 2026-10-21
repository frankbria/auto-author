# API Endpoints: Summary Operations

API documentation for the summary endpoints in Auto Author.

## Overview

The summary endpoints read, save and analyze a book's summary. The summary is the input for TOC generation. All endpoints require authentication and the caller must own the book.

## Base URL

```
{API_BASE_URL}/api/v1
```

## Authentication

Requests are authenticated by the better-auth session cookie. The backend reads no `Authorization` header. A missing or invalid session returns 401.

## Endpoints

### Get Book Summary

```http
GET /books/{book_id}/summary
```

**Success (200 OK)**

```json
{
  "summary": "This book is a comprehensive guide to sustainable gardening...",
  "summary_history": [
    { "summary": "An earlier version of the summary...", "timestamp": "2025-05-17T10:30:00+00:00" }
  ]
}
```

`summary` is an empty string when none is saved yet. `summary_history` holds the previous versions, oldest first, capped at the last 20.

**Errors**: 404 `Book not found`, 403 `Not authorized to access this book`.

```bash
curl -X GET "{API_BASE_URL}/api/v1/books/book_456/summary" -b cookies.txt
```

### Save Book Summary

```http
PUT /books/{book_id}/summary
PATCH /books/{book_id}/summary
```

Request body:

```json
{ "summary": "This book is a comprehensive guide to sustainable gardening practices for urban environments." }
```

**Validation rules**

| Field | Requirements |
|-------|-------------|
| summary | A string, 30 to 2000 characters. `PUT` also rejects inappropriate language. |

`PUT` requires `summary`. `PATCH` with no `summary` field changes nothing and returns the current summary and history.

**Success (200 OK)** returns the same shape as the GET: `summary` and `summary_history`. The previous summary is added to `summary_history` when the new one differs.

**Errors**

| Status | Detail |
|--------|--------|
| 400 | `Summary is required and must be a string.` (`PUT` only) |
| 400 | `Summary must be at least 30 characters.` |
| 400 | `Summary must be at most 2000 characters.` |
| 400 | `Summary contains inappropriate language.` (`PUT` only) |
| 403 | `Not authorized to update this book` |
| 404 | `Book not found` |

```bash
curl -X PUT "{API_BASE_URL}/api/v1/books/book_456/summary" \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"summary": "This book is a comprehensive guide to sustainable gardening practices..."}'
```

### Analyze Summary for TOC Generation

Uses AI to judge whether the summary is ready for TOC generation and stores the result on the book.

```http
POST /books/{book_id}/analyze-summary
```

**Success (200 OK)**

```json
{
  "book_id": "book_456",
  "analysis": {
    "is_ready_for_toc": true,
    "confidence_score": 0.85,
    "analysis": "The summary describes the audience and the main topics.",
    "suggestions": ["Name the main sections you want to cover."],
    "word_count": 156,
    "character_count": 987,
    "meets_minimum_requirements": true
  },
  "analyzed_at": "2025-05-17T14:22:00+00:00"
}
```

`meets_minimum_requirements` is true when the summary has at least 30 words and at least 150 characters. At most 3 suggestions are returned.

**Errors**

| Status | Meaning |
|--------|---------|
| 400 | `Book summary is required for analysis` |
| 403 | You do not own the book |
| 404 | `Book not found` |
| 429 | Rate limit exceeded |
| 503 | `AI_ANALYSIS_FAILED`, retryable. The failed result is not stored. |

Other AI errors are mapped by the shared AI error handler.

### Check TOC Readiness

```http
GET /books/{book_id}/toc-readiness
```

Returns the stored analysis if one exists. Otherwise it returns `is_ready_for_toc: false`, `confidence_score: 0.0` and a basic `meets_minimum_requirements` check (30 words and 150 characters), with the suggestion to run analysis first. The response fields are the same as the `analysis` object above.

## Error Handling

Errors use FastAPI's shape: `{"detail": "message"}`. Some errors, such as the 503 above, carry an object in `detail` with `message`, `error_code` and `retryable`.

## Rate Limiting

Limits are per user and per route, in fixed windows.

| Route | Limit |
|-------|-------|
| `POST /books/{book_id}/analyze-summary` | 5 per 60 seconds |
| `GET`, `PUT`, `PATCH /books/{book_id}/summary` | none |
| `GET /books/{book_id}/toc-readiness` | none |

A limited request gets 429 with `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers. The headers are sent only on the 429 response.

## Related Documentation

- [User Guide: Summary Input and Voice-to-Text](../user-guide/summary-input.md)
- [Troubleshooting: Summary Input Issues](../user-guide/troubleshooting-summary-input.md)
