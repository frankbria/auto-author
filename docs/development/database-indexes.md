# Database Indexes Documentation

## Overview

This document describes the database indexes implemented for the question collections in the Auto Author application. These indexes optimize query performance for common access patterns.

## Index Creation

Indexes are automatically created during application startup via the `ensure_question_indexes()` function in `/home/frankbria/projects/auto-author/backend/app/db/questions.py`.

### Startup Integration

The indexes are created using FastAPI's lifespan event handler in `/home/frankbria/projects/auto-author/backend/app/main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events (startup and shutdown)."""
    # Startup tasks
    logger.info("Running startup tasks...")

    from app.db.questions import ensure_question_indexes
    await ensure_question_indexes()

    logger.info("Startup tasks completed")
    yield
```

## Collections and Indexes

### 1. Questions Collection (`questions`)

#### Index: `book_chapter_user_idx`
- **Fields**: `(book_id: 1, chapter_id: 1, user_id: 1)`
- **Type**: Compound index
- **Purpose**: Optimize queries for retrieving questions by book, chapter, and user
- **Used in**:
  - `get_questions_for_chapter()`
  - `get_chapter_question_progress()`
  - `delete_questions_for_chapter()`

#### Index: `user_created_idx`
- **Fields**: `(user_id: 1, created_at: -1)`
- **Type**: Compound index (descending on created_at)
- **Purpose**: Optimize queries for user question history in chronological order
- **Used in**: Analytics and user activity tracking

#### Index: `chapter_order_idx`
- **Fields**: `(book_id: 1, chapter_id: 1, order: 1)`
- **Type**: Compound index
- **Purpose**: Optimize sorting questions by order within a chapter
- **Used in**: `get_questions_for_chapter()` with `.sort("order", 1)`

### 2. Question Responses Collection (`question_responses`)

#### Index: `question_user_idx`
- **Fields**: `(question_id: 1, user_id: 1)`
- **Type**: Compound unique index
- **Purpose**: Optimize response lookups and enforce one response per user per question
- **Unique**: Yes (each user can only have one response per question)
- **Used in**:
  - `get_question_response()`
  - `save_question_response()`

#### Index: `user_created_idx`
- **Fields**: `(user_id: 1, created_at: -1)`
- **Type**: Compound index (descending on created_at)
- **Purpose**: Optimize queries for user response history
- **Used in**: Analytics and user activity tracking

### 3. Question Ratings Collection (`question_ratings`)

#### Index: `question_user_idx`
- **Fields**: `(question_id: 1, user_id: 1)`
- **Type**: Compound unique index
- **Purpose**: Optimize rating lookups and enforce one rating per user per question
- **Unique**: Yes (each user can only have one rating per question)
- **Used in**: `save_question_rating()`

## Index Properties

All indexes share these properties:

- **Background Creation**: `background=True` - Indexes are created in the background to avoid blocking database operations
- **Idempotent**: Running `ensure_question_indexes()` multiple times is safe. MongoDB skips creation if the index already exists
- **Error Handling**: Index creation errors are logged but don't prevent application startup. Queries will still work, just potentially slower

## Verification

To verify indexes are properly created, run the verification script:

```bash
cd /home/frankbria/projects/auto-author/backend
uv run python scripts/verify_question_indexes.py
```

Expected output:
```
✅ All expected indexes verified successfully!
```

## Query Performance Impact

### Before Indexes
- Chapter question queries: Full collection scan
- Response lookups: Full collection scan
- User history queries: Full collection scan

### After Indexes
- Chapter question queries: Index scan (O(log n) lookup + result set)
- Response lookups: Index scan (O(log n) lookup)
- User history queries: Index scan with sorted results

### Example Query Patterns

#### 1. Get Questions for Chapter
```python
query = {
    "book_id": book_id,
    "chapter_id": chapter_id,
    "user_id": user_id
}
cursor = questions_collection.find(query).sort("order", 1)
```
**Indexes Used**: `book_chapter_user_idx` for filtering, `chapter_order_idx` for sorting

#### 2. Get Question Response
```python
response = await responses_collection.find_one({
    "question_id": question_id,
    "user_id": user_id
})
```
**Index Used**: `question_user_idx` (compound unique index)

#### 3. User Question History
```python
questions = questions_collection.find({
    "user_id": user_id
}).sort("created_at", -1)
```
**Index Used**: `user_created_idx` (sorted by creation time descending)

## Maintenance

### Viewing Indexes in MongoDB Shell

```javascript
// Connect to MongoDB
mongosh

// Switch to database
use auto_author

// List indexes for questions collection
db.questions.getIndexes()

// List indexes for question_responses collection
db.question_responses.getIndexes()

// List indexes for question_ratings collection
db.question_ratings.getIndexes()
```

### Dropping Indexes (if needed)

```javascript
// Drop a specific index
db.questions.dropIndex("book_chapter_user_idx")

// Drop all indexes except _id (use with caution!)
db.questions.dropIndexes()
```

### Rebuilding Indexes

Indexes are automatically created on application startup. To manually rebuild:

```python
# In Python shell or script
from app.db.questions import ensure_question_indexes
import asyncio

asyncio.run(ensure_question_indexes())
```

## Testing

### Unit Tests

Test file: `/home/frankbria/projects/auto-author/backend/tests/test_question_indexes.py`

Tests verify:
1. All expected indexes are created
2. Index creation is idempotent
3. Queries can use the indexes

Run tests:
```bash
cd /home/frankbria/projects/auto-author/backend
uv run pytest tests/test_question_indexes.py -v
```

### Integration Tests

The existing question-related tests verify the indexes work correctly in real scenarios:

```bash
cd /home/frankbria/projects/auto-author/backend
uv run pytest tests/test_services/run_test_question_responses.py -v
```

## Performance Monitoring

### MongoDB Query Profiling

To monitor query performance and verify index usage:

```javascript
// Enable profiling (level 2 = all operations)
db.setProfilingLevel(2)

// View slow queries
db.system.profile.find().sort({ts: -1}).limit(10)

// Check if a query used an index
db.questions.find({
    book_id: "test",
    chapter_id: "test",
    user_id: "test"
}).explain("executionStats")
```

### Expected Explain Output

For indexed queries, you should see:
- `"stage": "IXSCAN"` (Index Scan, not COLLSCAN)
- `"indexName": "book_chapter_user_idx"` (the index being used)
- Low `docsExamined` relative to `nReturned`

## Troubleshooting

### Issue: Indexes Not Created

**Symptoms**: Verification script shows missing indexes

**Solution**:
1. Check application logs for index creation errors
2. Ensure MongoDB is running and accessible
3. Verify database permissions (user must have createIndex privilege)
4. Manually run `ensure_question_indexes()` and check for errors

### Issue: Slow Query Performance

**Symptoms**: Queries taking longer than expected

**Diagnosis**:
1. Run query with `.explain()` to verify index usage
2. Check index statistics: `db.questions.stats()`
3. Review query patterns in application logs

**Solutions**:
- Ensure indexes exist (run verification script)
- Check for missing index on your specific query pattern
- Consider adding additional indexes for new query patterns

### Issue: Duplicate Key Errors on Responses

**Symptoms**: Error when saving responses: "E11000 duplicate key error"

**Explanation**: The `question_user_idx` unique index prevents duplicate responses

**Solution**: This is expected behavior. Update the existing response instead of creating a new one

## Future Enhancements

Potential index optimizations for future consideration:

1. **Category-based Queries**: If filtering by category becomes common, add:
   ```python
   await questions_collection.create_index([
       ("book_id", 1),
       ("chapter_id", 1),
       ("category", 1),
       ("user_id", 1)
   ])
   ```

2. **Status-based Response Queries**: For filtering responses by status:
   ```python
   await responses_collection.create_index([
       ("user_id", 1),
       ("status", 1),
       ("updated_at", -1)
   ])
   ```

3. **Text Search**: For full-text search on questions/responses:
   ```python
   await questions_collection.create_index([
       ("question_text", "text")
   ])
   ```

## References

- [MongoDB Indexing Strategies](https://www.mongodb.com/docs/manual/indexes/)
- [Compound Indexes in MongoDB](https://www.mongodb.com/docs/manual/core/index-compound/)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- Code: `/home/frankbria/projects/auto-author/backend/app/db/questions.py`
- Tests: `/home/frankbria/projects/auto-author/backend/tests/test_question_indexes.py`
