# API Endpoints: Summary Operations

This document provides complete API documentation for summary-related endpoints in Auto Author.

## Overview

The summary API endpoints handle creating, retrieving, updating, and managing book summaries that are used for TOC generation. All endpoints require authentication and follow RESTful conventions.

## Base URL

```
{API_BASE_URL}/api/v1
```

## Authentication

All summary endpoints require authentication via JWT token in the Authorization header:

```http
Authorization: Bearer {jwt_token}
```

## Endpoints

### Get Book Summary

Retrieves the current summary for a specific book.

#### Request

```http
GET /books/{book_id}/summary
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| book_id | string | Yes | Unique identifier for the book |

#### Response

**Success (200 OK)**

```json
{
  "id": "summary_123",
  "book_id": "book_456",
  "content": "This book is a comprehensive guide to sustainable gardening...",
  "word_count": 156,
  "character_count": 987,
  "created_at": "2025-05-17T10:30:00Z",
  "updated_at": "2025-05-17T14:22:00Z",
  "revision_number": 3,
  "is_valid_for_toc": true
}
```

**Not Found (404)**

```json
{
  "detail": "Summary not found for book {book_id}"
}
```

**Unauthorized (401)**

```json
{
  "detail": "Authentication required"
}
```

#### Example

```bash
curl -X GET \
  "{API_BASE_URL}/api/v1/books/book_456/summary" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Create/Update Book Summary

Creates a new summary or updates an existing one for a book.

#### Request

```http
POST /books/{book_id}/summary
PUT /books/{book_id}/summary
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| book_id | string | Yes | Unique identifier for the book |

#### Request Body

```json
{
  "content": "This book is a comprehensive guide to sustainable gardening practices for urban environments. It teaches readers how to create productive gardens in small spaces using organic methods, composting, and water conservation techniques."
}
```

#### Validation Rules

| Field | Requirements |
|-------|-------------|
| content | Required, min 1 character, max 5000 characters |
| word_count | Automatically calculated, min 30 words for TOC generation |
| character_count | Automatically calculated |

#### Response

**Success (200 OK for update, 201 Created for new)**

```json
{
  "id": "summary_123",
  "book_id": "book_456",
  "content": "This book is a comprehensive guide to sustainable gardening practices...",
  "word_count": 156,
  "character_count": 987,
  "created_at": "2025-05-17T10:30:00Z",
  "updated_at": "2025-05-17T14:22:00Z",
  "revision_number": 4,
  "is_valid_for_toc": true,
  "meets_minimum_requirements": true
}
```

**Validation Error (422)**

```json
{
  "detail": [
    {
      "loc": ["body", "content"],
      "msg": "Content cannot be empty",
      "type": "value_error"
    }
  ]
}
```

**Bad Request (400)**

```json
{
  "detail": "Content exceeds maximum length of 5000 characters"
}
```

#### Example

```bash
curl -X POST \
  "{API_BASE_URL}/api/v1/books/book_456/summary" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This book is a comprehensive guide to sustainable gardening practices for urban environments..."
  }'
```

### Delete Book Summary

Removes the summary for a specific book.

#### Request

```http
DELETE /books/{book_id}/summary
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| book_id | string | Yes | Unique identifier for the book |

#### Response

**Success (204 No Content)**

```
(Empty response body)
```

**Not Found (404)**

```json
{
  "detail": "Summary not found for book {book_id}"
}
```

#### Example

```bash
curl -X DELETE \
  "{API_BASE_URL}/api/v1/books/book_456/summary" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Get Summary Revision History

Retrieves the revision history for a book's summary.

#### Request

```http
GET /books/{book_id}/summary/revisions
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| book_id | string | Yes | Unique identifier for the book |
| limit | integer | No | Number of revisions to return (default: 10, max: 50) |
| offset | integer | No | Number of revisions to skip (default: 0) |

#### Response

**Success (200 OK)**

```json
{
  "total_revisions": 5,
  "revisions": [
    {
      "revision_number": 5,
      "content": "This book is a comprehensive guide to sustainable gardening practices...",
      "word_count": 156,
      "character_count": 987,
      "created_at": "2025-05-17T14:22:00Z",
      "is_current": true
    },
    {
      "revision_number": 4,
      "content": "This book covers sustainable gardening practices...",
      "word_count": 134,
      "character_count": 845,
      "created_at": "2025-05-17T13:15:00Z",
      "is_current": false
    }
  ]
}
```

#### Example

```bash
curl -X GET \
  "{API_BASE_URL}/api/v1/books/book_456/summary/revisions?limit=5" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Restore Summary Revision

Restores a specific revision of a summary as the current version.

#### Request

```http
POST /books/{book_id}/summary/revisions/{revision_number}/restore
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| book_id | string | Yes | Unique identifier for the book |
| revision_number | integer | Yes | Revision number to restore |

#### Response

**Success (200 OK)**

```json
{
  "id": "summary_123",
  "book_id": "book_456",
  "content": "This book covers sustainable gardening practices...",
  "word_count": 134,
  "character_count": 845,
  "created_at": "2025-05-17T10:30:00Z",
  "updated_at": "2025-05-17T15:45:00Z",
  "revision_number": 6,
  "restored_from_revision": 4,
  "is_valid_for_toc": true
}
```

**Not Found (404)**

```json
{
  "detail": "Revision {revision_number} not found for book {book_id}"
}
```

#### Example

```bash
curl -X POST \
  "{API_BASE_URL}/api/v1/books/book_456/summary/revisions/4/restore" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Validate Summary for TOC Generation

Checks if a summary meets the requirements for TOC generation.

#### Request

```http
GET /books/{book_id}/summary/validate
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| book_id | string | Yes | Unique identifier for the book |

#### Response

**Success (200 OK)**

```json
{
  "is_valid": true,
  "meets_minimum_length": true,
  "word_count": 156,
  "minimum_required_words": 30,
  "character_count": 987,
  "maximum_allowed_characters": 5000,
  "validation_messages": [],
  "can_generate_toc": true
}
```

**Validation Failed (200 OK with validation errors)**

```json
{
  "is_valid": false,
  "meets_minimum_length": false,
  "word_count": 15,
  "minimum_required_words": 30,
  "character_count": 87,
  "maximum_allowed_characters": 5000,
  "validation_messages": [
    "Summary must contain at least 30 words for TOC generation",
    "Consider adding more detail about your book's content and target audience"
  ],
  "can_generate_toc": false
}
```

#### Example

```bash
curl -X GET \
  "{API_BASE_URL}/api/v1/books/book_456/summary/validate" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Data Models

### Summary Object

```typescript
interface Summary {
  id: string;
  book_id: string;
  content: string;
  word_count: number;
  character_count: number;
  created_at: string; // ISO 8601 datetime
  updated_at: string; // ISO 8601 datetime
  revision_number: number;
  is_valid_for_toc: boolean;
  meets_minimum_requirements?: boolean;
  restored_from_revision?: number;
}
```

### Summary Revision Object

```typescript
interface SummaryRevision {
  revision_number: number;
  content: string;
  word_count: number;
  character_count: number;
  created_at: string; // ISO 8601 datetime
  is_current: boolean;
}
```

### Validation Response Object

```typescript
interface SummaryValidation {
  is_valid: boolean;
  meets_minimum_length: boolean;
  word_count: number;
  minimum_required_words: number;
  character_count: number;
  maximum_allowed_characters: number;
  validation_messages: string[];
  can_generate_toc: boolean;
}
```

## Error Handling

### Common Error Responses

#### 400 Bad Request
- Invalid request format
- Content too long
- Missing required fields

#### 401 Unauthorized
- Missing or invalid authentication token
- Expired token

#### 403 Forbidden
- User doesn't own the book
- Insufficient permissions

#### 404 Not Found
- Book not found
- Summary not found
- Revision not found

#### 422 Unprocessable Entity
- Validation errors
- Invalid field values

#### 500 Internal Server Error
- Database connection issues
- Unexpected server errors

### Error Response Format

All error responses follow this structure:

```json
{
  "detail": "Error message describing what went wrong",
  "error_code": "OPTIONAL_ERROR_CODE",
  "timestamp": "2025-05-17T15:45:00Z"
}
```

## Rate Limiting

Summary endpoints are subject to rate limiting:

- **GET requests**: 100 requests per minute per user
- **POST/PUT requests**: 30 requests per minute per user
- **DELETE requests**: 10 requests per minute per user

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1621267200
```

## Best Practices

### API Usage
1. **Use appropriate HTTP methods**: GET for retrieval, POST for creation, PUT for updates
2. **Handle errors gracefully**: Always check response status codes
3. **Implement retry logic**: For temporary failures (5xx errors)
4. **Cache responses**: When appropriate to reduce API calls
5. **Validate before sending**: Check content length client-side first

### Content Management
1. **Auto-save implementation**: Use debouncing to avoid excessive API calls
2. **Revision tracking**: Leverage revision history for undo functionality
3. **Validation feedback**: Use validation endpoint for real-time feedback
4. **Offline support**: Cache content locally when possible

### Security
1. **Token management**: Securely store and refresh JWT tokens
2. **Content sanitization**: Sanitize user input before sending
3. **Rate limit awareness**: Implement client-side rate limiting
4. **Error information**: Don't expose sensitive data in error messages

## Integration Examples

### Frontend Auto-save Implementation

```javascript
// Auto-save with debouncing
let saveTimeout;
const autoSave = (bookId, content) => {
  clearTimeout(saveTimeout);
  saveTimeout = setTimeout(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/books/${bookId}/summary`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content })
      });
      
      if (response.ok) {
        console.log('Summary auto-saved');
      }
    } catch (error) {
      console.error('Auto-save failed:', error);
    }
  }, 600); // 600ms debounce
};
```

### Real-time Validation

```javascript
// Validate summary for TOC generation
const validateSummary = async (bookId) => {
  try {
    const response = await fetch(`${API_BASE}/api/v1/books/${bookId}/summary/validate`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    const validation = await response.json();
    return validation.can_generate_toc;
  } catch (error) {
    console.error('Validation failed:', error);
    return false;
  }
};
```

## Related Documentation

- [Summary Input Requirements and Best Practices](summary-input-requirements.md)
- [User Guide: Summary Input and Voice-to-Text](user-guide-summary-input.md)
- [Troubleshooting: Summary Input Issues](troubleshooting-summary-input.md)
- [API Authentication Guide](api-auth-endpoints.md)

---

Last updated: May 17, 2025
