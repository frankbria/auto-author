# Error Handling Enhancement for Question API Endpoints

## Overview

Enhanced error handling for all question-related API endpoints in `/backend/app/api/endpoints/books.py` with detailed error messages, specific error codes, and consistent response formats.

## Implementation Date

2025-12-22

## Changes Summary

### 1. New Error Schemas (`/backend/app/schemas/errors.py`)

Created comprehensive error response schemas with:
- **ErrorCode Enum**: 25+ specific error codes for different failure scenarios
- **ErrorDetail Model**: Field-level error information with context
- **ErrorResponse Model**: Standardized error response structure
- **Specialized Error Responses**: ValidationError, AuthorizationError, ResourceNotFound, RateLimitError

#### Key Error Codes Added:
- `BOOK_NOT_FOUND`, `CHAPTER_NOT_FOUND`, `QUESTION_NOT_FOUND`
- `UNAUTHORIZED_ACCESS`, `FORBIDDEN_OPERATION`
- `VALIDATION_FAILED`, `INVALID_PARAMETER`
- `QUESTION_GENERATION_FAILED`, `QUESTION_LIMIT_EXCEEDED`
- `RESPONSE_SAVE_FAILED`, `RATING_SAVE_FAILED`
- `DATABASE_ERROR`, `RATE_LIMIT_EXCEEDED`

### 2. Error Handler Utilities (`/backend/app/utils/error_handlers.py`)

Created reusable error handling functions:

#### General Handlers:
- `handle_book_not_found()` - 404 errors for missing books
- `handle_unauthorized_access()` - 403 errors for permission issues
- `handle_validation_error()` - 422 errors for invalid input
- `handle_generic_error()` - 500 errors for unexpected failures

#### Question-Specific Handlers:
- `handle_question_generation_error()` - AI service errors with retry information
- `handle_question_not_found()` - Missing question errors
- `handle_response_save_error()` - Response save failures
- `handle_rating_save_error()` - Rating save failures

#### Features:
- **Request ID Generation**: Unique correlation IDs for error tracking
- **Detailed Context**: Includes relevant IDs, parameters, and values
- **Structured Logging**: Consistent logging format for debugging
- **AI Service Integration**: Special handling for AIServiceError with retry information

### 3. Enhanced Question Endpoints

Updated 7 question-related endpoints in `books.py`:

#### 1. `POST /{book_id}/chapters/{chapter_id}/generate-questions`
- Validates request parameters (count: 1-50)
- Handles book not found, unauthorized access
- Catches AIServiceError for retryable failures
- Returns specific error codes for debugging

#### 2. `GET /{book_id}/chapters/{chapter_id}/questions`
- Validates pagination parameters (page ≥ 1, limit: 1-50)
- Handles filter validation errors
- Includes context in error responses

#### 3. `PUT /{book_id}/chapters/{chapter_id}/questions/{question_id}/response`
- Validates response text (non-empty)
- Handles question not found
- Distinguishes between validation and save errors

#### 4. `GET /{book_id}/chapters/{chapter_id}/questions/{question_id}/response`
- Handles missing question gracefully
- Returns null for missing responses (not an error)
- Includes full context in error responses

#### 5. `POST /{book_id}/chapters/{chapter_id}/questions/{question_id}/rating`
- Validates rating value (1-5)
- Includes rating value in error details
- Handles duplicate rating updates

#### 6. `GET /{book_id}/chapters/{chapter_id}/question-progress`
- Handles missing chapter errors
- Validates chapter exists in book
- Returns progress stats or detailed error

#### 7. `POST /{book_id}/chapters/{chapter_id}/regenerate-questions`
- Validates regeneration parameters
- Handles preserve_responses flag
- Includes regeneration context (preserved/new counts)

### 4. Common Error Handling Pattern

All endpoints now follow this pattern:

```python
def endpoint_function(...):
    """
    Endpoint documentation...

    Error Codes:
        - ERROR_CODE_1 (status): Description
        - ERROR_CODE_2 (status): Description
        ...
    """
    request_id = generate_request_id()

    # Validate input parameters
    if invalid_param:
        raise handle_validation_error(...)

    # Get resource and verify access
    resource = get_resource(id)
    if not resource:
        raise handle_resource_not_found(id, request_id)

    if not authorized:
        raise handle_unauthorized_access(..., request_id)

    # Perform operation with try/catch
    try:
        result = service.perform_operation(...)

        # Log success with request_id
        await audit_request(..., request_id=request_id)

        return result

    except ValueError as e:
        # Handle validation errors
        raise handle_validation_error(..., request_id)
    except Exception as e:
        # Handle all other errors
        raise handle_specific_error(..., request_id)
```

### 5. Error Response Format

All errors now return consistent JSON:

```json
{
  "error": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "status_code": 404,
  "details": [
    {
      "field": "book_id",
      "message": "No book exists with ID: invalid-id",
      "code": "BOOK_NOT_FOUND",
      "value": "invalid-id"
    }
  ],
  "timestamp": "2025-12-22T10:30:00Z",
  "request_id": "req_abc123def456"
}
```

### 6. Unit Tests (`/backend/tests/test_error_handlers.py`)

Created comprehensive test suite with 28 tests:

#### Test Coverage:
- Request ID generation and uniqueness
- All error handler functions
- HTTP status codes (404, 403, 422, 500, 503)
- Error code inclusion
- Context and details inclusion
- AI service error handling (retryable/non-retryable)
- Error response structure consistency

#### Test Results:
- **28 tests passing** (100% pass rate)
- Tests verify error structure, codes, messages, and context
- Validates special handling for AIServiceError

## Benefits

### For Developers:
1. **Easier Debugging**: Request IDs for tracking errors across logs
2. **Specific Error Codes**: Machine-readable codes for programmatic handling
3. **Detailed Context**: All relevant IDs and parameters in error response
4. **Consistent Format**: Same error structure across all endpoints
5. **Type Safety**: Pydantic models for error responses

### For Users:
1. **Clear Error Messages**: Human-readable explanations
2. **Actionable Feedback**: Specific field errors with invalid values
3. **Better UX**: Distinguish between user errors and system failures
4. **Retry Information**: Know when to retry (rate limits, service unavailable)

### For Operations:
1. **Correlation IDs**: Track requests across microservices
2. **Structured Logging**: Consistent log format for analysis
3. **Error Categorization**: Easy filtering by error type
4. **Monitoring**: Can alert on specific error codes

## Example Error Responses

### Book Not Found (404)
```json
{
  "error": "Book not found",
  "error_code": "BOOK_NOT_FOUND",
  "status_code": 404,
  "details": [
    {
      "field": "book_id",
      "message": "No book exists with ID: invalid-book-123",
      "code": "BOOK_NOT_FOUND",
      "value": "invalid-book-123"
    }
  ],
  "timestamp": "2025-12-22T10:30:00.000Z",
  "request_id": "req_a1b2c3d4e5f6"
}
```

### Validation Error (422)
```json
{
  "error": "Request validation failed",
  "error_code": "VALIDATION_FAILED",
  "status_code": 422,
  "details": [
    {
      "field": "count",
      "message": "Question count must be between 1 and 50",
      "code": "VALIDATION_FAILED",
      "value": 100
    }
  ],
  "timestamp": "2025-12-22T10:30:00.000Z",
  "request_id": "req_a1b2c3d4e5f6"
}
```

### Unauthorized Access (403)
```json
{
  "error": "Not authorized to access this book",
  "error_code": "FORBIDDEN_OPERATION",
  "status_code": 403,
  "details": [
    {
      "field": "book_id",
      "message": "You must be the book owner to perform this operation",
      "code": "UNAUTHORIZED_ACCESS",
      "value": "book-123"
    }
  ],
  "timestamp": "2025-12-22T10:30:00.000Z",
  "request_id": "req_a1b2c3d4e5f6"
}
```

### AI Service Error - Retryable (503)
```json
{
  "error": "Question generation failed: AI service rate limit exceeded",
  "error_code": "QUESTION_GENERATION_FAILED",
  "status_code": 503,
  "details": [
    {
      "message": "AI service rate limit exceeded",
      "code": "AI_RATE_LIMIT"
    },
    {
      "field": "retryable",
      "message": "This error is retryable",
      "value": true
    }
  ],
  "timestamp": "2025-12-22T10:30:00.000Z",
  "request_id": "req_a1b2c3d4e5f6"
}
```

## Files Modified

1. **New Files**:
   - `/backend/app/schemas/errors.py` - Error schemas and codes
   - `/backend/app/utils/error_handlers.py` - Error handler utilities
   - `/backend/tests/test_error_handlers.py` - Unit tests (28 tests)

2. **Modified Files**:
   - `/backend/app/api/endpoints/books.py` - Enhanced 7 question endpoints

## Testing

Run tests with:
```bash
cd /home/frankbria/projects/auto-author/backend
uv run pytest tests/test_error_handlers.py -v
```

**Test Results**: 28/28 tests passing (100% pass rate)

## Next Steps (Recommendations)

1. **Frontend Integration**:
   - Update API client to handle new error format
   - Display field-specific errors in forms
   - Show retry buttons for retryable errors
   - Log request_id for support requests

2. **Monitoring**:
   - Set up alerts for specific error codes
   - Track error rates by endpoint
   - Monitor retry patterns for AI service errors

3. **Documentation**:
   - Update API documentation with error codes
   - Create error handling guide for frontend developers
   - Document retry strategies for each error type

4. **Apply to Other Endpoints**:
   - Consider applying same pattern to other endpoint groups
   - Create reusable handlers for common patterns
   - Standardize error responses across entire API

## Breaking Changes

**None** - This is backward compatible. The error response structure is additive:
- Old clients still get `detail` field (FastAPI default)
- New clients get enhanced error structure in `detail` field
- No changes to request/response models

## Notes

- Request IDs are generated for every request, enabling end-to-end tracing
- AIServiceError integration allows intelligent retry logic
- All error handlers include structured logging for operations
- Error responses are Pydantic models for type safety
- Tests cover all error scenarios including edge cases
