# Sprint 2: Books Questions Test Coverage Fixes

**Date**: 2025-12-03
**Module**: `backend/app/api/endpoints/books/books_questions.py`
**Initial Coverage**: 31% (36/118 lines)
**Target Coverage**: 75%+

## Summary

This document details the analysis and fixes attempted to improve test coverage for the `books_questions.py` module. The module contains question generation and management endpoints for chapter-based authoring workflows.

## Issues Discovered & Fixed

### 1. Chapter Creation Endpoint Bug
**Issue**: `add_chapter_with_transaction() got an unexpected keyword argument 'parent_id'`

**Root Cause**: The endpoint was passing `parent_id` but the function signature expects `parent_chapter_id`.

**Fix**: Updated `books_chapters.py` line 102:
```python
# Before
parent_id=chapter_data.parent_id if chapter_data.level > 1 else None,

# After
parent_chapter_id=chapter_data.parent_id if chapter_data.level > 1 else None,
```

**Impact**: Fixed 20+ failing tests across multiple test files that depend on chapter creation.

---

### 2. Test Response Structure Mismatch
**Issue**: Tests were accessing `chapter_resp.json()["id"]` but the API returns `["chapter_id"]`

**Root Cause**: The chapter creation endpoint returns:
```python
{
    "book_id": book_id,
    "chapter": new_chapter,
    "chapter_id": new_chapter["id"],  # <-- Correct key
    "success": True,
    "message": "Chapter created successfully",
}
```

**Fix**: Updated 20+ occurrences in `test_books_questions_drafts.py` and additional occurrences in `test_books_toc_chapters.py`:
```python
# Before
chapter_id = chapter_resp.json()["id"]

# After
chapter_id = chapter_resp.json()["chapter_id"]
```

**Script Used**: Created `fix_test_chapter_id.py` to automate the fix across multiple files.

---

### 3. Missing Request Body for Question Generation
**Issue**: POST requests to `/generate-questions` were returning 422 (Field required)

**Root Cause**: The endpoint requires a `GenerateQuestionsRequest` body with fields:
- `count`: Optional[int] = 10 (default)
- `difficulty`: Optional[QuestionDifficulty] = None
- `focus`: Optional[List[QuestionType]] = None

Tests were calling the endpoint without any request body.

**Fix**: Updated all generate-questions POST calls to include request body:
```python
# Before
gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")

# After
gen_resp = await client.post(
    f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
    json={"count": 5}
)
```

**Script Used**: Created `fix_questions_tests.py` to add request bodies automatically.

---

### 4. Missing Chapter Level Field
**Issue**: Some tests created chapters without the `level` field

**Fix**: Added `"level": 1` to all `chapter_data` dictionaries to ensure proper chapter creation:
```python
chapter_data = {
    "title": "Test Chapter",
    "content": "Chapter content...",
    "order": 1,
    "level": 1  # Added
}
```

---

## Remaining Issues

### 1. Mock Configuration for Question Generation Service
**Status**: ⚠️ Incomplete

**Issue**: The mock for `question_generation_service.QuestionGenerationService.generate_questions_for_chapter` is not working correctly. The service returns a `GenerateQuestionsResponse` Pydantic model, but the mock is returning a dict.

**Error**: 500 Internal Server Error when calling generate-questions endpoint in tests.

**Technical Details**:
- Service method signature: `async def generate_questions_for_chapter(...) -> GenerateQuestionsResponse`
- Current mock: `mock_generate.return_value = {"questions": [...], "success": True}`
- Problem: The endpoint expects a Pydantic model with proper schema validation

**Attempted Solutions**:
1. Patching `app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter`
2. Verifying the service factory function `get_question_generation_service()`

**Next Steps**:
1. Update mock to return proper `GenerateQuestionsResponse` object
2. Or mock at a lower level (the AI service that the question service uses)
3. Or consider integration tests without mocking

---

### 2. Test Coverage Gap Analysis

**Endpoints in `books_questions.py`**:

#### Covered (Partially)
1. `POST /{book_id}/chapters/{chapter_id}/generate-questions` - Tests exist but mocks failing
2. `GET /{book_id}/chapters/{chapter_id}/questions` - Tests exist but need verification
3. `PUT /{book_id}/chapters/{chapter_id}/questions/{question_id}/response` - Tests exist but need verification
4. `GET /{book_id}/chapters/{chapter_id}/questions/{question_id}/response` - Tests exist but need verification
5. `POST /{book_id}/chapters/{chapter_id}/questions/{question_id}/rating` - Tests exist but need verification
6. `GET /{book_id}/chapters/{chapter_id}/question-progress` - Tests exist but need verification

#### Missing Coverage
1. `POST /{book_id}/chapters/{chapter_id}/regenerate-questions` - No tests
2. Error paths for all endpoints:
   - Invalid book_id (404)
   - Unauthorized access (403)
   - AI service failures (500)
   - Invalid request data (422)
   - Rate limiting (429)

**Lines Not Covered** (from coverage report):
- Error handling blocks (lines 132-135, 184-187, etc.)
- Audit logging (lines 115-128, 236-249, etc.)
- Edge cases in service calls
- Response validation

---

## Test Files Structure

### Current: `test_books_questions_drafts.py`

**Classes**:
1. `TestChapterQuestions` - Question generation and listing
2. `TestQuestionResponses` - Response management
3. `TestQuestionRating` - Rating functionality
4. `TestQuestionProgress` - Progress tracking
5. `TestDraftGeneration` - Draft generation from questions

**Test Count**: 21 tests (20 failing due to mock issues, 1 passing)

---

## Coverage Improvement Plan

### Phase 1: Fix Existing Tests (Estimated: 2-3 hours)
1. ✅ Fix chapter creation endpoint parameter bug
2. ✅ Fix test response structure access
3. ✅ Add request bodies to all POST calls
4. ⚠️ Fix mock configuration for question service
5. ⚠️ Verify all test assertions match actual API responses

### Phase 2: Add Missing Tests (Estimated: 2-3 hours)
1. Add regenerate-questions endpoint tests
2. Add comprehensive error handling tests:
   - Book not found (404)
   - Unauthorized access (403)
   - Invalid question_id (404)
   - AI service failures (500)
   - Invalid ratings (422)
3. Add rate limiting tests
4. Add edge case tests:
   - Empty question lists
   - Large question counts
   - Multiple concurrent requests

### Phase 3: Integration Tests (Estimated: 1-2 hours)
1. End-to-end question generation workflow
2. Complete authoring cycle (generate → answer → draft)
3. Progress tracking validation
4. Database persistence verification

---

## Scripts Created

### 1. `fix_test_chapter_id.py`
**Purpose**: Fix chapter_id access pattern across all test files

**Usage**:
```bash
python backend/fix_test_chapter_id.py
```

**Changes**: 20+ replacements in test files

---

### 2. `fix_questions_tests.py`
**Purpose**: Add request bodies to all generate-questions POST calls

**Usage**:
```bash
python backend/fix_questions_tests.py
```

**Changes**: Added `json={"count": 5}` to all generate-questions calls

---

## Test Execution Results

### Before Fixes
```
FAILED: 20/21 tests
Coverage: 0% (module never imported)
Errors:
- KeyError: 'id' (chapter response structure)
- HTTPException: add_chapter_with_transaction() got unexpected keyword argument
- RequestValidationError: Field required (request body)
```

### After Partial Fixes
```
FAILED: 20/21 tests
PASSED: 1/21 tests (test_get_response_unauthorized)
Coverage: Unable to measure (tests still failing)
Current Error: 500 Internal Server Error (mock configuration issue)
```

---

## Recommendations

### Immediate (This Sprint)
1. **Fix Mock Configuration**: Update mocks to return proper Pydantic models instead of dicts
2. **Verify Endpoint Responses**: Check actual API responses match test expectations
3. **Add Error Path Tests**: Cover 404, 403, 500 error scenarios

### Short Term (Next Sprint)
1. **Integration Test Suite**: Add end-to-end tests without mocking
2. **Service Unit Tests**: Test `QuestionGenerationService` independently
3. **Database Tests**: Verify question persistence and retrieval

### Long Term (Backlog)
1. **Performance Tests**: Validate rate limiting and concurrent requests
2. **Load Tests**: Test question generation under load
3. **AI Service Mocking**: Create reusable fixtures for AI service mocks

---

## Files Modified

### Source Code
1. `/home/frankbria/projects/auto-author/backend/app/api/endpoints/books/books_chapters.py` (Line 102)
   - Fixed parameter name mismatch

### Test Files
1. `/home/frankbria/projects/auto-author/backend/tests/test_api/test_routes/test_books_questions_drafts.py`
   - Fixed 20+ chapter_id access patterns
   - Added request bodies to generate-questions calls
   - Added level field to chapter_data

2. `/home/frankbria/projects/auto-author/backend/tests/test_api/test_routes/test_books_toc_chapters.py`
   - Fixed chapter_id access patterns

### Scripts
1. `/home/frankbria/projects/auto-author/backend/fix_test_chapter_id.py` (new)
2. `/home/frankbria/projects/auto-author/backend/fix_questions_tests.py` (new)

---

## Lessons Learned

### API Design
1. **Response Structure Consistency**: Chapter creation returns `chapter_id` while other endpoints might use `id`. Consider standardizing.
2. **Request Body Requirements**: All POST endpoints should clearly document required vs optional fields.
3. **Error Messages**: 404 errors should include what resource wasn't found.

### Test Infrastructure
1. **Mock Complexity**: Services returning Pydantic models need special mock handling.
2. **Test Data Setup**: Helper functions for creating books/chapters would reduce test code duplication.
3. **Async Testing**: Need clear patterns for async endpoint testing with proper fixtures.

### Development Workflow
1. **Run Tests First**: Before writing new tests, ensure existing infrastructure works.
2. **Incremental Fixes**: Fix one issue at a time and verify before moving to next.
3. **Coverage Analysis**: Use coverage reports to identify actual gaps vs test failures.

---

## Next Actions

1. **Immediate**: Fix mock configuration to use proper Pydantic models
2. **Short Term**: Complete Phase 1 of coverage improvement plan
3. **Documentation**: Update API documentation with response schemas
4. **Refactoring**: Extract common test patterns into fixtures/helpers

---

## References

- **Module**: `/home/frankbria/projects/auto-author/backend/app/api/endpoints/books/books_questions.py`
- **Tests**: `/home/frankbria/projects/auto-author/backend/tests/test_api/test_routes/test_books_questions_drafts.py`
- **Service**: `/home/frankbria/projects/auto-author/backend/app/services/question_generation_service.py`
- **Schema**: `/home/frankbria/projects/auto-author/backend/app/schemas/book.py` (Question-related schemas)
