# Sprint 2 - Unimplemented Features

**Date**: 2025-12-03
**Status**: Documented for future implementation
**Tests**: 22 tests skipped pending implementation

---

## Overview

During Sprint 2 test coverage implementation, 22 tests were written for features that are not yet implemented. These tests document the expected API behavior and should be implemented in a future sprint.

**Current Test Status:**
- ✅ 142 tests passing (100% of implemented features)
- ⏭️ 22 tests skipped (documented below)
- ❌ 0 tests failing

---

## Unimplemented Features (22 tests)

### 1. Question Response Management (6 tests)

**File**: `tests/test_api/test_routes/test_books_questions_drafts.py`
**Class**: `TestQuestionResponses`

**Missing Endpoints:**
- `POST /api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response` - Save question response
- `PUT /api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response` - Update existing response
- `GET /api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response` - Get question response

**Tests Skipped:**
1. `test_save_question_response_new` - Save new question response
2. `test_save_response_update_existing` - Update existing response
3. `test_save_response_validation_error` - Validation error handling
4. `test_get_question_response_success` - Get response success
5. `test_get_response_not_found` - Handle response not found
6. `test_get_response_unauthorized` - Authorization check

**Expected Behavior:**
- Store user responses to clarifying questions
- Track response history (edits)
- Calculate word count
- Validate required fields
- Authorization: Only book owner can manage responses

**Estimated Effort**: 4-6 hours

---

### 2. Question Rating System (3 tests)

**File**: `tests/test_api/test_routes/test_books_questions_drafts.py`
**Class**: `TestQuestionRating`

**Missing Endpoints:**
- `POST /api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/rating` - Rate question quality
- `PUT /api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/rating` - Update rating

**Tests Skipped:**
1. `test_rate_question_success` - Rate question 1-5 stars
2. `test_update_question_rating` - Update existing rating
3. `test_rate_question_invalid_rating` - Validate rating range

**Expected Behavior:**
- Rate question quality (1-5 scale)
- Update existing ratings
- Validate rating range
- Track rating timestamps
- Authorization: Only book owner can rate

**Estimated Effort**: 2-3 hours

---

### 3. Question Progress Tracking (2 tests)

**File**: `tests/test_api/test_routes/test_books_questions_drafts.py`
**Class**: `TestQuestionProgress`

**Missing Endpoints:**
- `GET /api/v1/books/{book_id}/chapters/{chapter_id}/questions/progress` - Get question progress

**Tests Skipped:**
1. `test_get_progress_all_completed` - All questions answered (100%)
2. `test_get_progress_no_questions` - No questions generated (0%)

**Expected Behavior:**
- Calculate completion percentage
- Return answered vs total questions
- Track by chapter
- Authorization: Only book owner can view

**Estimated Effort**: 2-3 hours

---

### 4. Draft Generation (5 tests)

**File**: `tests/test_api/test_routes/test_books_questions_drafts.py`
**Class**: `TestDraftGeneration`

**Missing Endpoints:**
- `POST /api/v1/books/{book_id}/chapters/{chapter_id}/draft` - Generate chapter draft from responses

**Tests Skipped:**
1. `test_generate_draft_success` - Generate draft with all responses
2. `test_generate_draft_no_responses` - Error when no responses provided
3. `test_generate_draft_style_variations` - Support multiple writing styles
4. `test_generate_draft_ai_failure` - Handle AI service failures

**Expected Behavior:**
- Generate narrative from Q&A responses
- Support writing styles (formal, casual, academic, creative)
- Require all questions answered
- Handle AI service errors gracefully
- Store generated draft
- Authorization: Only book owner can generate

**Estimated Effort**: 6-8 hours (includes AI integration)

---

### 5. Chapter Metadata Endpoints (2 tests)

**File**: `tests/test_api/test_routes/test_books_toc_chapters.py`
**Class**: `TestChapterMetadata`

**Missing Endpoints:**
- `GET /api/v1/books/{book_id}/chapters/metadata` - Get all chapters metadata
- `GET /api/v1/books/{book_id}/chapters/metadata?with_stats=true` - Get metadata with statistics

**Tests Skipped:**
1. `test_get_chapters_metadata` - Get basic metadata
2. `test_get_chapters_metadata_with_stats` - Get metadata with stats

**Expected Behavior:**
- Return chapter metadata (title, order, status, word_count)
- Optional statistics (reading_time, completion_percentage)
- Efficient bulk query (not N+1)
- Authorization: Only book owner can view

**Estimated Effort**: 2-3 hours

---

### 6. Tab State Management (3 tests)

**File**: `tests/test_api/test_routes/test_books_toc_chapters.py`
**Class**: `TestTabState`

**Missing Endpoints:**
- `GET /api/v1/books/{book_id}/chapters/tab-state` - Get user's tab state
- `POST /api/v1/books/{book_id}/chapters/tab-state` - Save tab state

**Tests Skipped:**
1. `test_save_tab_state_success` - Save active tab state
2. `test_get_tab_state_success` - Retrieve saved tab state
3. `test_get_tab_state_not_found` - Default when no state saved

**Expected Behavior:**
- Track which chapter tab is active
- Store per-user, per-book
- Return default if no state saved
- Authorization: User-specific state

**Estimated Effort**: 3-4 hours

---

### 7. Chapter Analytics (2 tests)

**File**: `tests/test_api/test_routes/test_books_toc_chapters.py`
**Class**: `TestChapterAnalytics`

**Missing Endpoints:**
- `GET /api/v1/books/{book_id}/chapters/{chapter_id}/analytics` - Get chapter analytics
- `GET /api/v1/books/{book_id}/chapters/{chapter_id}/analytics?days=14` - Custom time range

**Tests Skipped:**
1. `test_get_chapter_analytics` - Get default 30-day analytics
2. `test_get_chapter_analytics_custom_days` - Get custom time range

**Expected Behavior:**
- Return view count, edit count, time spent
- Support custom time ranges (7, 14, 30, 90 days)
- Track access patterns
- Authorization: Only book owner can view

**Estimated Effort**: 4-5 hours

---

## Total Estimated Effort

**Summary:**
- 22 tests covering 7 feature areas
- Estimated implementation time: **24-32 hours**
- Recommended sprint allocation: **Sprint 3 or Sprint 4**

**Priority Ranking:**
1. **High Priority** (Core Features):
   - Draft Generation (8 hours) - Critical for authoring workflow
   - Question Response Management (6 hours) - Required for draft generation

2. **Medium Priority** (UX Enhancements):
   - Question Progress Tracking (3 hours)
   - Tab State Management (4 hours)
   - Question Rating System (3 hours)

3. **Low Priority** (Analytics):
   - Chapter Analytics (5 hours)
   - Chapter Metadata (3 hours)

---

## Implementation Recommendations

### Sprint 3 Focus
Implement high-priority features to complete the authoring workflow:
1. Question Response Management (6 hours)
2. Draft Generation (8 hours)
3. Question Progress Tracking (3 hours)

**Total Sprint 3**: 17 hours, 11 tests

### Sprint 4 Focus
Complete UX and analytics features:
1. Question Rating System (3 hours)
2. Tab State Management (4 hours)
3. Chapter Metadata (3 hours)
4. Chapter Analytics (5 hours)

**Total Sprint 4**: 15 hours, 11 tests

---

## Test Maintenance

**Current State:**
- All 22 tests use `@pytest.mark.skip(reason="Feature not implemented - Sprint 3/4")`
- Tests are well-written and document expected behavior
- No changes needed until implementation begins

**When Implementing:**
1. Remove `@pytest.mark.skip` decorator from relevant tests
2. Implement the endpoint
3. Run tests to verify behavior matches expectations
4. Fix any discrepancies between test expectations and implementation

**Test Quality:**
- All tests follow existing patterns
- Proper mocking for external services
- Comprehensive coverage (success, errors, edge cases)
- Authorization checks included

---

**Last Updated**: 2025-12-03
**Next Review**: When beginning Sprint 3/4 planning
