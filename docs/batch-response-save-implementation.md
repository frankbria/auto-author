# Batch Response Save Implementation

## Summary

Implemented efficient batch response save functionality to improve performance and user experience when saving multiple question responses.

## Changes Made

### 1. Backend Database Layer (`backend/app/db/questions.py`)

**Function: `save_question_responses_batch`**

- Accepts a list of response objects and user_id
- Uses MongoDB bulk write operations for efficiency
- Handles partial failures gracefully
- Returns detailed results for each response
- Tracks edit history for updates
- Auto-calculates word counts

**Features:**
- Validates each response (question_id and response_text required)
- Checks for existing responses to determine update vs create
- Executes bulk operations for better performance
- Returns comprehensive result object with:
  - `success`: Overall operation success (false if any failures)
  - `total`: Total responses provided
  - `saved`: Number successfully saved
  - `failed`: Number that failed
  - `results`: Per-response results with status and optional errors
  - `errors`: Detailed error information for failed responses

### 2. Backend API Endpoint (`backend/app/api/endpoints/books.py`)

**Endpoint: `POST /{book_id}/chapters/{chapter_id}/questions/responses/batch`**

- Route: `/api/v1/books/{book_id}/chapters/{chapter_id}/questions/responses/batch`
- Method: POST
- Auth: Required (book owner only)
- Max batch size: 100 responses

**Request Body:**
```json
[
  {
    "question_id": "string",
    "response_text": "string",
    "status": "draft" | "completed"
  }
]
```

**Response:**
```json
{
  "success": boolean,
  "total": number,
  "saved": number,
  "failed": number,
  "results": [
    {
      "index": number,
      "question_id": "string",
      "response_id": "string",
      "success": boolean,
      "is_update": boolean,
      "error": "string" (optional)
    }
  ],
  "errors": [
    {
      "index": number,
      "question_id": "string",
      "error": "string"
    }
  ],
  "message": "string"
}
```

**Validation:**
- Verifies book ownership
- Rejects empty request body (400)
- Enforces 100 response limit (400)
- Returns 404 if book not found
- Returns 403 if user unauthorized

**Audit Logging:**
- Logs batch save operations with metadata:
  - book_id
  - chapter_id
  - total, saved, failed counts
  - overall success status

### 3. Frontend API Client (`frontend/src/lib/api/bookClient.ts`)

**Method: `saveQuestionResponsesBatch`**

```typescript
public async saveQuestionResponsesBatch(
  bookId: string,
  chapterId: string,
  responses: Array<{
    question_id: string;
    response_text: string;
    status?: 'draft' | 'completed';
  }>
): Promise<BatchSaveResult>
```

**Features:**
- Comprehensive JSDoc documentation
- TypeScript type safety
- Automatic error handling
- Example usage in documentation

**Usage Example:**
```typescript
const responses = [
  {
    question_id: 'q1',
    response_text: 'Answer to question 1',
    status: 'completed'
  },
  {
    question_id: 'q2',
    response_text: 'Draft answer to question 2',
    status: 'draft'
  }
];

const result = await bookClient.saveQuestionResponsesBatch(
  bookId,
  chapterId,
  responses
);

console.log(`Saved ${result.saved}/${result.total} responses`);

// Handle partial failures
if (result.failed > 0) {
  result.results.forEach(r => {
    if (!r.success) {
      console.error(`Question ${r.question_id}: ${r.error}`);
    }
  });
}
```

### 4. Comprehensive Test Suite (`backend/tests/test_batch_question_responses.py`)

**Test Coverage:**
1. `test_batch_save_new_responses` - Saving multiple new responses
2. `test_batch_save_update_existing_responses` - Updating existing responses
3. `test_batch_save_partial_failure` - Handling validation failures
4. `test_batch_save_empty_list` - Edge case: empty batch
5. `test_batch_save_word_count_calculation` - Verifying word count accuracy
6. `test_batch_save_edit_history_tracking` - Edit history preservation
7. `test_batch_save_mixed_new_and_updates` - Mixed operations

**Test Results:**
```
7 passed in 0.53s
```

All tests pass successfully, validating:
- Correct response creation
- Proper update handling
- Partial failure recovery
- Edge case handling
- Data integrity (word counts, edit history)
- Mixed operation scenarios

## Benefits

### Performance
- Single API call instead of N calls for N responses
- Bulk database operations reduce network overhead
- Better database connection pooling

### User Experience
- Faster save operations for multiple responses
- Clear feedback on partial failures
- Ability to continue editing even if some responses fail

### Reliability
- Graceful degradation with partial failures
- Detailed error reporting per response
- No data loss - successful saves complete even if others fail
- Edit history preserved for all updates

## Error Handling

### Validation Errors
- Missing `question_id`: Specific error returned for that response
- Missing `response_text`: Specific error returned for that response
- Invalid data types: Caught and reported per response

### Database Errors
- Connection failures: Entire batch fails with 500 error
- Individual save failures: Reported in results array
- Duplicate key errors: Handled gracefully (shouldn't occur due to unique constraint)

### HTTP Status Codes
- 200: Success (even with partial failures - check result.success)
- 400: Bad request (empty body, exceeds limit)
- 403: Unauthorized (not book owner)
- 404: Book not found
- 500: Server error

## Future Enhancements

Potential improvements for future iterations:

1. **Transaction Support**: Wrap batch in MongoDB transaction for all-or-nothing semantics
2. **Progress Callbacks**: Stream progress updates for very large batches
3. **Rate Limiting**: Per-batch rate limiting to prevent abuse
4. **Optimistic Locking**: Add version fields to prevent concurrent update conflicts
5. **Batch Size Optimization**: Dynamic batch size based on response text length
6. **Retry Logic**: Automatic retry for transient failures
7. **Metrics**: Track batch save performance and failure rates

## Files Modified

1. `/backend/app/db/questions.py` - Added `save_question_responses_batch` function
2. `/backend/app/api/endpoints/books.py` - Added batch save endpoint
3. `/frontend/src/lib/api/bookClient.ts` - Added `saveQuestionResponsesBatch` method
4. `/backend/tests/test_batch_question_responses.py` - Created comprehensive test suite

## Integration

To use this feature in the frontend:

1. **Import the client:**
   ```typescript
   import { bookClient } from '@/lib/api/bookClient';
   ```

2. **Collect responses:**
   ```typescript
   const responses = questions.map(q => ({
     question_id: q.id,
     response_text: q.answer,
     status: q.completed ? 'completed' : 'draft'
   }));
   ```

3. **Save batch:**
   ```typescript
   try {
     const result = await bookClient.saveQuestionResponsesBatch(
       bookId,
       chapterId,
       responses
     );

     if (result.success) {
       toast.success('All responses saved successfully');
     } else {
       toast.warning(`Saved ${result.saved}/${result.total} responses`);
       // Handle failed responses
     }
   } catch (error) {
     toast.error('Failed to save responses');
   }
   ```

## Testing

Run the test suite:

```bash
cd backend
uv run pytest tests/test_batch_question_responses.py -v
```

Expected output:
```
7 passed in 0.53s
```

## Conclusion

The batch response save functionality is now fully implemented and tested. It provides significant performance improvements and better user experience when saving multiple question responses simultaneously, while maintaining data integrity and providing detailed error feedback.
