# Sprint 2 Test Coverage Plan: P1 Business Logic Modules

**Report Date:** 2025-12-03
**Sprint:** Sprint 2 (P1 Business Logic)
**Current Branch:** feature/p0-blockers-quick-wins
**Current Coverage:** ~41% → Sprint 1 target ~55%
**Sprint 2 Target:** ~55% → ~73% (18 percentage point gain)
**Duration:** 2 weeks
**Estimated New Tests:** 92-113 tests

---

## Executive Summary

Sprint 1 achieved **182 new tests** for P0 security modules (security.py, dependencies.py, webhooks.py, book_cover_upload.py, transcription.py), raising coverage from 41% to ~55%.

Sprint 2 focuses on **P1 business logic modules** - the core application features that power the Auto-Author product:

1. **Books Endpoints** (`books.py`) - 46% → 80%+ coverage (50-60 tests)
2. **TOC Transactions** (`toc_transactions.py`) - 15% → 85%+ coverage (15-20 tests)
3. **Questions Database** (`questions.py`) - 30% → 85%+ coverage (12-15 tests)
4. **Users Endpoints** (`users.py`) - 47% → 85%+ coverage (15-18 tests)

**Risk Assessment:**
- **HIGH:** books.py is 2674 lines (massive file) with 44 endpoints
- **MEDIUM:** TOC transactions have complex atomic operations
- **MEDIUM:** Questions database lacks integration test coverage
- **LOW:** Users endpoints are well-structured

**Success Criteria:**
- All 92-113 new tests passing (100% pass rate)
- Module coverage: 80-85%+ for each target module
- No regressions in existing 189 tests
- Test execution time < 5 minutes total

---

## Module Analysis

### 1. Books Endpoints (`app/api/endpoints/books.py`)

**Current State:**
- **Coverage:** 46% (405/878 statements covered, 473 missing)
- **Lines:** 2674 (MASSIVE FILE - needs refactoring consideration)
- **Endpoints:** 44 total (see endpoint inventory below)
- **Existing Tests:** 3 tests in `test_books_metadata.py`, 2 tests in `test_toc_generation.py`

**Endpoint Inventory:**

| Endpoint | Method | Function | Lines | Priority | Test Coverage |
|----------|--------|----------|-------|----------|---------------|
| `/` | POST | create_new_book | 81-136 | Critical | ✅ Covered |
| `/` | GET | get_user_books | 138-167 | Critical | ✅ Covered |
| `/{book_id}` | GET | get_book | 169-229 | Critical | ✅ Covered |
| `/{book_id}` | PUT | update_book_details | 231-320 | Critical | ⚠️ Partial |
| `/{book_id}` | PATCH | patch_book_details | 322-406 | Critical | ⚠️ Partial |
| `/{book_id}` | DELETE | delete_book_endpoint | 408-473 | Critical | ❌ Missing |
| `/{book_id}/cover-image` | POST | upload_book_cover_image | 475-549 | High | ❌ Missing |
| `/{book_id}/summary` | GET | get_book_summary | 551-572 | High | ❌ Missing |
| `/{book_id}/summary` | PUT | update_book_summary | 574-634 | High | ❌ Missing |
| `/{book_id}/summary` | PATCH | patch_book_summary | 636-688 | High | ❌ Missing |
| `/{book_id}/analyze-summary` | POST | analyze_book_summary | 690-747 | High | ❌ Missing |
| `/{book_id}/generate-questions` | POST | generate_clarifying_questions | 749-818 | High | ❌ Missing |
| `/{book_id}/question-responses` | GET | get_question_responses | 820-849 | High | ❌ Missing |
| `/{book_id}/question-responses` | PUT | save_question_responses | 851-918 | High | ❌ Missing |
| `/{book_id}/toc-readiness` | GET | check_toc_generation_readiness | 920-1018 | High | ❌ Missing |
| `/{book_id}/generate-toc` | POST | generate_table_of_contents | 1020-1095 | Critical | ⚠️ Partial |
| `/{book_id}/toc` | GET | get_book_toc | 1097-1148 | Critical | ❌ Missing |
| `/{book_id}/toc` | PUT | update_book_toc | 1150-1225 | Critical | ❌ Missing |
| `/{book_id}/chapters` | POST | create_chapter | 1227-1291 | Critical | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}` | GET | get_chapter | 1293-1338 | Critical | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}` | PUT | update_chapter | 1340-1416 | Critical | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}` | DELETE | delete_chapter | 1418-1466 | Critical | ❌ Missing |
| `/{book_id}/chapters` | GET | list_chapters | 1468-1532 | Critical | ❌ Missing |
| `/{book_id}/chapters/metadata` | GET | get_chapters_metadata | 1534-1609 | High | ❌ Missing |
| `/{book_id}/chapters/bulk-status` | PATCH | update_chapter_status_bulk | 1611-1703 | Medium | ❌ Missing |
| `/{book_id}/chapters/tab-state` | POST | save_tab_state | 1705-1741 | Medium | ❌ Missing |
| `/{book_id}/chapters/tab-state` | GET | get_tab_state | 1743-1786 | Medium | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}/content` | GET | get_chapter_content | 1788-1871 | Critical | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}/content` | PATCH | update_chapter_content | 1873-1971 | Critical | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}/analytics` | GET | get_chapter_analytics | 1973-2015 | Low | ❌ Missing |
| `/{book_id}/chapters/batch-content` | POST | batch_get_chapter_content | 2017-2113 | Medium | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}/generate-questions` | POST | generate_chapter_questions | 2115-2179 | High | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}/questions` | GET | list_chapter_questions | 2181-2231 | High | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}/questions/{question_id}/response` | PUT | save_question_response | 2233-2306 | High | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}/questions/{question_id}/response` | GET | get_question_response | 2308-2353 | High | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}/questions/{question_id}/rating` | POST | rate_question | 2355-2421 | Medium | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}/questions/progress` | GET | get_chapter_question_progress | 2423-2469 | Medium | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}/regenerate-questions` | POST | regenerate_chapter_questions | 2471-2541 | Medium | ❌ Missing |
| `/{book_id}/chapters/{chapter_id}/generate-draft` | POST | generate_chapter_draft | 2543-2674 | Critical | ❌ Missing |

**Coverage Gaps:**
- **Chapter CRUD:** 0% coverage on create, update, delete (lines 1227-1466)
- **Chapter Content:** 0% coverage on content read/write (lines 1788-1971)
- **Chapter Questions:** 0% coverage on question generation/response (lines 2115-2541)
- **Draft Generation:** 0% coverage on AI draft generation (lines 2543-2674)
- **TOC Management:** 0% coverage on TOC read/update (lines 1097-1225)
- **Bulk Operations:** 0% coverage on batch operations (lines 1611-1703, 2017-2113)

---

### 2. TOC Transactions (`app/db/toc_transactions.py`)

**Current State:**
- **Coverage:** 15% (32/214 statements covered, 182 missing)
- **Lines:** 491
- **Functions:** 10 (5 public, 5 internal)
- **Existing Tests:** 0 dedicated tests

**Function Inventory:**

| Function | Lines | Type | Current Coverage | Priority | Missing Test Cases |
|----------|-------|------|------------------|----------|--------------------|
| `update_toc_with_transaction` | 16-42 | Public | ⚠️ Partial | Critical | Transaction rollback, version conflicts, concurrent updates |
| `_update_toc_internal` | 44-151 | Internal | ⚠️ Partial | Critical | Optimistic locking failures, authorization checks |
| `add_chapter_with_transaction` | 154-176 | Public | ❌ None | Critical | Subchapter insertion, transaction failures |
| `_add_chapter_internal` | 179-241 | Internal | ❌ None | Critical | Parent chapter not found, duplicate IDs |
| `update_chapter_with_transaction` | 244-266 | Public | ❌ None | High | Recursive update failures, nested subchapters |
| `_update_chapter_internal` | 269-328 | Internal | ❌ None | High | Chapter not found, partial updates |
| `delete_chapter_with_transaction` | 331-352 | Public | ❌ None | High | Cascade delete, subchapter orphaning |
| `_delete_chapter_internal` | 355-409 | Internal | ❌ None | High | Recursive deletion failures |
| `reorder_chapters_with_transaction` | 412-434 | Public | ❌ None | Medium | Invalid order values, missing chapters |
| `_reorder_chapters_internal` | 437-491 | Internal | ❌ None | Medium | Order conflicts, partial reordering |

**Coverage Gaps:**
- **Transaction Support:** Test both transaction mode (replica set) and fallback mode (standalone)
- **Optimistic Locking:** Version conflict scenarios (lines 81-84)
- **Atomic Operations:** Rollback on failure, isolation testing
- **Concurrent Updates:** Multiple users editing same TOC
- **Error Handling:** Book not found, authorization failures, database errors
- **Edge Cases:** Empty chapters, deeply nested subchapters, reordering with gaps

---

### 3. Questions Database (`app/db/questions.py`)

**Current State:**
- **Coverage:** 30% (38/128 statements covered, 90 missing)
- **Lines:** 354
- **Functions:** 7
- **Existing Tests:** 0 dedicated tests

**Function Inventory:**

| Function | Lines | Current Coverage | Priority | Missing Test Cases |
|----------|-------|------------------|----------|--------------------|
| `create_question` | 19-39 | ✅ Covered | High | None - well tested |
| `get_questions_for_chapter` | 42-113 | ⚠️ Partial | Critical | Filtering by status/category/type, pagination, response status aggregation |
| `save_question_response` | 116-174 | ❌ None | Critical | Create new response, update existing, edit history tracking, word count calculation |
| `get_question_response` | 177-190 | ❌ None | High | Response not found, invalid question ID |
| `save_question_rating` | 193-235 | ❌ None | Medium | Create rating, update rating, validation |
| `get_chapter_question_progress` | 238-289 | ❌ None | High | Progress calculation, status determination (not-started, in-progress, completed) |
| `delete_questions_for_chapter` | 292-332 | ❌ None | Medium | Preserve responses, cascade delete, bulk deletion |
| `get_question_by_id` | 335-353 | ❌ None | High | Question not found, invalid ObjectId |

**Coverage Gaps:**
- **Question Retrieval:** Filtering logic (lines 62-106)
- **Response Storage:** Create vs update logic, edit history (lines 143-161)
- **Progress Tracking:** Status calculation algorithm (lines 258-281)
- **Deletion Logic:** Conditional deletion with response preservation (lines 311-330)
- **Error Handling:** Invalid IDs, database failures, data validation

---

### 4. Users Endpoints (`app/api/endpoints/users.py`)

**Current State:**
- **Coverage:** 47% (56/118 statements covered, 62 missing)
- **Lines:** 349
- **Endpoints:** 8
- **Existing Tests:** 3 tests in `test_users.py`

**Endpoint Inventory:**

| Endpoint | Method | Function | Lines | Priority | Current Coverage | Missing Test Cases |
|----------|--------|----------|-------|----------|------------------|-------------------|
| `/me` | GET | read_users_me | 31-91 | Critical | ✅ Covered | Preferences defaults, audit logging |
| `/clerk/{clerk_id}` | GET | get_clerk_user_data | 93-110 | Medium | ⚠️ Partial | Authorization checks, admin access |
| `/me` | PATCH | update_profile | 113-170 | Critical | ❌ None | Input sanitization, duplicate email, timeout errors |
| `/me` | DELETE | delete_profile | 173-200 | Critical | ❌ None | Soft delete, audit logging, user not found |
| `/` | POST | create_new_user | 203-245 | High | ❌ None | Duplicate clerk_id, duplicate email, default values |
| `/{clerk_id}` | PUT | update_user_data | 248-308 | High | ❌ None | Authorization, role updates, admin restrictions |
| `/admin/users` | GET | get_all_users | 311-316 | Medium | ❌ None | Admin-only access, pagination |
| `/{clerk_id}` | DELETE | delete_user_account | 319-348 | High | ❌ None | Authorization, admin delete, user not found |

**Coverage Gaps:**
- **Profile Updates:** Input sanitization, error handling (lines 122-154)
- **Account Deletion:** Soft delete workflow, audit logging (lines 180-198)
- **User Creation:** Duplicate detection, default values (lines 210-244)
- **Authorization:** Role-based access, admin permissions (lines 259-286)
- **Error Handling:** Database timeouts, conflicts, not found scenarios

---

## Sprint 2 Test Matrices

### Matrix 1: Books Endpoints (Agent 1 - fastapi-expert)

| Function | Current Coverage | Missing Test Cases | Estimated Tests | Priority |
|----------|------------------|-------------------|-----------------|----------|
| **Book CRUD** |
| `delete_book_endpoint` | 0% | Delete success, not found, cascade delete, unauthorized | 4 | Critical |
| `update_book_details` (PUT) | Partial | Full update, validation errors, concurrent updates | 3 | Critical |
| `patch_book_details` (PATCH) | Partial | Partial update, field validation, unchanged fields | 3 | Critical |
| **Summary Management** |
| `get_book_summary` | 0% | Get success, book not found, empty summary | 3 | High |
| `update_book_summary` | 0% | Update success, validation (min length), offensive words | 3 | High |
| `patch_book_summary` | 0% | Patch success, empty summary validation | 2 | High |
| `analyze_book_summary` | 0% | AI analysis success, empty summary, analysis failure | 3 | High |
| **Question Workflow** |
| `generate_clarifying_questions` | 0% | Generate success, no summary, genre-specific, AI failure | 4 | High |
| `get_question_responses` | 0% | Get responses, empty responses, invalid book | 3 | High |
| `save_question_responses` | 0% | Save new, update existing, validation errors | 3 | High |
| **TOC Generation** |
| `check_toc_generation_readiness` | 0% | Ready state, missing summary, missing responses | 3 | High |
| `generate_table_of_contents` | Partial | Full workflow, no summary, no responses, AI failure | 4 | Critical |
| `get_book_toc` | 0% | Get success, no TOC, book not found | 3 | Critical |
| `update_book_toc` | 0% | Update success, version conflict, validation errors | 3 | Critical |
| **Chapter CRUD** |
| `create_chapter` | 0% | Create top-level, create subchapter, validation errors | 3 | Critical |
| `get_chapter` | 0% | Get success, chapter not found, unauthorized | 3 | Critical |
| `update_chapter` | 0% | Update success, not found, validation errors | 3 | Critical |
| `delete_chapter` | 0% | Delete success, cascade subchapters, not found | 3 | Critical |
| `list_chapters` | 0% | List all, filter by status, pagination | 3 | Critical |
| **Chapter Content** |
| `get_chapter_content` | 0% | Get content, access tracking, unauthorized | 3 | Critical |
| `update_chapter_content` | 0% | Update content, auto-save, conflict resolution | 4 | Critical |
| **Bulk Operations** |
| `get_chapters_metadata` | 0% | Get metadata, empty chapters, status aggregation | 3 | High |
| `update_chapter_status_bulk` | 0% | Bulk update, partial success, validation errors | 3 | Medium |
| `batch_get_chapter_content` | 0% | Batch get, invalid IDs, authorization | 3 | Medium |
| **Tab State** |
| `save_tab_state` | 0% | Save state, update existing, validation | 2 | Medium |
| `get_tab_state` | 0% | Get state, no state found, defaults | 2 | Medium |
| **Questions Integration** |
| `generate_chapter_questions` | 0% | Generate success, no content, genre-specific | 3 | High |
| `list_chapter_questions` | 0% | List all, filter by status, pagination | 3 | High |
| `save_question_response` | 0% | Save response, update existing, validation | 3 | High |
| `get_question_response` | 0% | Get response, not found, unauthorized | 2 | High |
| `rate_question` | 0% | Rate question, update rating, validation | 2 | Medium |
| `get_chapter_question_progress` | 0% | Progress calculation, no questions, all completed | 2 | Medium |
| `regenerate_chapter_questions` | 0% | Regenerate success, preserve responses, AI failure | 2 | Medium |
| **Draft Generation** |
| `generate_chapter_draft` | 0% | Generate draft, no responses, style variations, AI failure | 4 | Critical |
| **Analytics** |
| `get_chapter_analytics` | 0% | Get analytics, access tracking, time aggregation | 2 | Low |

**Subtotal:** 50-60 tests

---

### Matrix 2: TOC Transactions (Agent 2 - mongodb-expert)

| Function | Current Coverage | Missing Test Cases | Estimated Tests | Priority |
|----------|------------------|-------------------|-----------------|----------|
| **TOC Update** |
| `update_toc_with_transaction` | Partial | Transaction mode, fallback mode, replica set detection | 3 | Critical |
| `_update_toc_internal` | Partial | Success path, version conflict, book not found, unauthorized | 4 | Critical |
| **Chapter Add** |
| `add_chapter_with_transaction` | None | Transaction mode, fallback mode | 2 | Critical |
| `_add_chapter_internal` | None | Add top-level, add subchapter, parent not found, duplicate ID | 4 | Critical |
| **Chapter Update** |
| `update_chapter_with_transaction` | None | Transaction mode, fallback mode | 2 | High |
| `_update_chapter_internal` | None | Update success, chapter not found, nested subchapter update | 3 | High |
| **Chapter Delete** |
| `delete_chapter_with_transaction` | None | Transaction mode, fallback mode | 2 | High |
| `_delete_chapter_internal` | None | Delete top-level, delete subchapter, cascade delete, not found | 4 | High |
| **Chapter Reorder** |
| `reorder_chapters_with_transaction` | None | Transaction mode, fallback mode | 2 | Medium |
| `_reorder_chapters_internal` | None | Reorder success, partial list, invalid order values | 3 | Medium |
| **Concurrency & Isolation** |
| Transaction isolation | None | Concurrent TOC updates, rollback on failure, deadlock handling | 3 | Critical |
| Optimistic locking | None | Version mismatch detection, retry logic | 2 | Critical |

**Subtotal:** 15-20 tests

---

### Matrix 3: Questions Database (Agent 3 - python-expert)

| Function | Current Coverage | Missing Test Cases | Estimated Tests | Priority |
|----------|------------------|-------------------|-----------------|----------|
| **Question Retrieval** |
| `get_questions_for_chapter` | Partial | Filter by status (completed, draft, not_answered) | 3 | Critical |
| | | Filter by category and type | 2 | High |
| | | Pagination (first page, middle page, last page) | 3 | High |
| | | Response status aggregation | 2 | Critical |
| **Response Storage** |
| `save_question_response` | None | Create new response with word count | 2 | Critical |
| | | Update existing response with edit history | 2 | Critical |
| | | Status validation (draft vs completed) | 2 | High |
| **Response Retrieval** |
| `get_question_response` | None | Get existing response | 1 | High |
| | | Response not found (returns None) | 1 | High |
| **Rating System** |
| `save_question_rating` | None | Create new rating (1-5 scale) | 2 | Medium |
| | | Update existing rating | 2 | Medium |
| **Progress Tracking** |
| `get_chapter_question_progress` | None | All questions completed (100% progress) | 1 | High |
| | | Some in progress (partial progress) | 1 | High |
| | | None answered (0% progress) | 1 | High |
| | | No questions (0 total) | 1 | High |
| **Deletion Logic** |
| `delete_questions_for_chapter` | None | Delete all (preserve_with_responses=False) | 2 | Medium |
| | | Preserve questions with responses | 2 | Medium |
| **Question Lookup** |
| `get_question_by_id` | None | Get by valid ID | 1 | High |
| | | Invalid ObjectId (returns None) | 1 | High |
| | | Question not found | 1 | High |

**Subtotal:** 12-15 tests

---

### Matrix 4: Users Endpoints (Agent 4 - fastapi-expert)

| Function | Current Coverage | Missing Test Cases | Estimated Tests | Priority |
|----------|------------------|-------------------|-----------------|----------|
| **Profile Management** |
| `read_users_me` | Covered | Preferences defaults when missing | 1 | Medium |
| | | Audit logging verification | 1 | Low |
| **Clerk Integration** |
| `get_clerk_user_data` | Partial | Self-access success | 1 | Medium |
| | | Admin access to other users | 1 | Medium |
| | | Non-admin forbidden (403) | 1 | High |
| | | User not found in Clerk (404) | 1 | High |
| **Profile Updates** |
| `update_profile` | None | Update success with sanitized input | 2 | Critical |
| | | Duplicate email conflict (409) | 1 | Critical |
| | | Database timeout (504) | 1 | High |
| | | Audit logging verification | 1 | Medium |
| **Account Deletion** |
| `delete_profile` | None | Soft delete success | 1 | Critical |
| | | User not found (404) | 1 | High |
| | | Audit logging verification | 1 | Medium |
| **User Creation** |
| `create_new_user` | None | Create success with defaults (role=user, is_active=true) | 2 | High |
| | | Duplicate clerk_id conflict (409) | 1 | Critical |
| | | Duplicate email conflict (409) | 1 | Critical |
| | | Database error (500) | 1 | High |
| **User Updates** |
| `update_user_data` | None | Self-update success | 1 | High |
| | | Admin update other user | 1 | High |
| | | Non-admin forbidden (403) | 1 | Critical |
| | | Role update by non-admin forbidden | 1 | Critical |
| | | User not found (404) | 1 | High |
| | | Database timeout (504) | 1 | High |
| **Admin Operations** |
| `get_all_users` | None | Admin access success | 1 | Medium |
| | | Non-admin forbidden (403) | 1 | High |
| **User Deletion** |
| `delete_user_account` | None | Self-delete success | 1 | High |
| | | Admin delete other user | 1 | High |
| | | Non-admin forbidden (403) | 1 | Critical |
| | | User not found (404) | 1 | High |

**Subtotal:** 15-18 tests

---

## Agent Assignments

### Agent 1: FastAPI Expert - Books Endpoints (50-60 tests)

**Responsibility:** Test all 44 endpoints in `app/api/endpoints/books.py`

**Focus Areas:**
1. **Book CRUD** (10 tests)
   - Delete book with cascade cleanup
   - PUT vs PATCH update semantics
   - Concurrent update handling

2. **Summary & Questions Workflow** (13 tests)
   - Summary CRUD operations
   - AI summary analysis
   - Clarifying question generation
   - Question response storage

3. **TOC Generation** (13 tests)
   - Readiness checks
   - TOC generation with AI
   - TOC retrieval and updates
   - Version conflict handling

4. **Chapter Management** (24 tests)
   - Chapter CRUD (create, read, update, delete, list)
   - Chapter content read/write
   - Chapter questions integration
   - Draft generation with AI
   - Bulk operations
   - Tab state management

**Testing Patterns to Follow:**

```python
# Example from existing test_books_metadata.py
@pytest.mark.asyncio
async def test_book_metadata_retrieval_and_update(auth_client_factory, test_book):
    api_client = await auth_client_factory()

    # Create book
    payload = test_book.copy()
    payload["owner_id"] = str(test_book["owner_id"])
    del payload["_id"]
    del payload["id"]
    del payload["toc_items"]
    del payload["published"]
    payload_book = jsonable_encoder(payload)

    response = await api_client.post(f"/api/v1/books/", json=payload_book)
    assert response.status_code == 201
    new_id = response.json()["id"]

    # Test GET
    response = await api_client.get(f"/api/v1/books/{new_id}")
    assert response.status_code == 200
    assert response.json()["title"] == test_book["title"]

    # Test PATCH
    patch_data = {"title": "Updated Title"}
    response = await api_client.patch(f"/api/v1/books/{new_id}", json=patch_data)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"
```

**Mock AI Services:**

```python
# Example from existing test_toc_generation.py
@pytest.mark.asyncio
@patch("app.services.ai_service.AIService.generate_toc_from_summary_and_responses")
async def test_generate_toc_endpoint(mock_generate_toc, async_client_factory):
    mock_generate_toc.return_value = {
        "toc": {
            "chapters": [
                {"id": "ch1", "title": "Introduction", "level": 1, "order": 1}
            ]
        },
        "success": True
    }

    client = await async_client_factory()
    # ... test TOC generation ...
```

**Key Test Files:**
- `backend/tests/test_api/test_routes/test_books_crud.py` (NEW)
- `backend/tests/test_api/test_routes/test_books_summary.py` (NEW)
- `backend/tests/test_api/test_routes/test_books_chapters.py` (NEW)
- `backend/tests/test_api/test_routes/test_books_questions.py` (NEW)
- `backend/tests/test_api/test_routes/test_books_draft_generation.py` (NEW)

---

### Agent 2: MongoDB Expert - TOC Transactions (15-20 tests)

**Responsibility:** Test atomic TOC operations in `app/db/toc_transactions.py`

**Focus Areas:**
1. **Transaction Support** (6 tests)
   - Replica set transaction mode
   - Standalone fallback mode
   - Transaction rollback on failure

2. **Chapter Operations** (14 tests)
   - Add chapter (top-level and subchapter)
   - Update chapter (with recursive search)
   - Delete chapter (with cascade)
   - Reorder chapters (with partial lists)

3. **Concurrency & Isolation** (5 tests)
   - Optimistic locking (version conflicts)
   - Concurrent updates
   - Deadlock prevention

**Testing Patterns to Follow:**

```python
# Example transaction test pattern
@pytest.mark.asyncio
async def test_update_toc_with_version_conflict(motor_reinit_db):
    """Test optimistic locking - version conflict detection"""
    from app.db.toc_transactions import update_toc_with_transaction
    from app.db.database import create_book

    # Create test book
    book_data = {
        "title": "Test Book",
        "owner_id": "test_clerk_id",
        "table_of_contents": {
            "chapters": [],
            "version": 1
        }
    }
    book = await create_book(book_data, "test_clerk_id")
    book_id = book["id"]

    # Update TOC with version 1 (should succeed)
    toc_data = {
        "chapters": [{"id": "ch1", "title": "Chapter 1"}],
        "expected_version": 1
    }
    updated_toc = await update_toc_with_transaction(
        book_id, toc_data, "test_clerk_id"
    )
    assert updated_toc["version"] == 2

    # Try to update with stale version (should fail)
    stale_toc_data = {
        "chapters": [{"id": "ch2", "title": "Chapter 2"}],
        "expected_version": 1  # Stale version!
    }

    with pytest.raises(ValueError, match="Version conflict"):
        await update_toc_with_transaction(
            book_id, stale_toc_data, "test_clerk_id"
        )
```

**Concurrent Update Test:**

```python
@pytest.mark.asyncio
async def test_concurrent_toc_updates(motor_reinit_db):
    """Test concurrent updates - one should succeed, one should fail"""
    import asyncio
    from app.db.toc_transactions import update_toc_with_transaction

    # Create book with TOC
    # ...

    # Simulate concurrent updates
    async def update_with_version(chapter_title, expected_version):
        try:
            toc_data = {
                "chapters": [{"id": f"ch-{chapter_title}", "title": chapter_title}],
                "expected_version": expected_version
            }
            return await update_toc_with_transaction(
                book_id, toc_data, "test_clerk_id"
            )
        except ValueError as e:
            return e

    # Both updates expect version 1
    results = await asyncio.gather(
        update_with_version("Update A", 1),
        update_with_version("Update B", 1),
        return_exceptions=True
    )

    # One should succeed (version 2), one should fail (version conflict)
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert successes[0]["version"] == 2
    assert "Version conflict" in str(failures[0])
```

**Key Test Files:**
- `backend/tests/test_db/test_toc_transactions.py` (NEW)
- `backend/tests/test_db/test_toc_concurrency.py` (NEW)

---

### Agent 3: Python Expert - Questions Database (12-15 tests)

**Responsibility:** Test question database operations in `app/db/questions.py`

**Focus Areas:**
1. **Question Retrieval** (10 tests)
   - Filter by status (completed, draft, not_answered)
   - Filter by category and type
   - Pagination (edge cases: first page, last page)
   - Response status aggregation

2. **Response Storage** (6 tests)
   - Create new response with word count
   - Update existing response with edit history
   - Status validation

3. **Progress Tracking** (4 tests)
   - Progress calculation algorithm
   - Status determination (not-started, in-progress, completed)

4. **Deletion Logic** (4 tests)
   - Delete all vs preserve responses
   - Cascade delete responses

**Testing Patterns to Follow:**

```python
@pytest.mark.asyncio
async def test_get_questions_with_status_filter(motor_reinit_db):
    """Test filtering questions by response status"""
    from app.db.questions import (
        create_question, save_question_response, get_questions_for_chapter
    )
    from app.schemas.book import QuestionCreate, QuestionResponseCreate

    book_id = "book123"
    chapter_id = "ch1"
    user_id = "user123"

    # Create 3 questions
    for i in range(3):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Question {i+1}",
            question_type="text",
            category="character",
            order=i+1
        )
        await create_question(question, user_id)

    # Get all questions
    all_questions = await get_questions_for_chapter(
        book_id, chapter_id, user_id, limit=10
    )
    assert all_questions.total == 3

    # Answer first question (completed)
    q1_id = all_questions.questions[0]["id"]
    response1 = QuestionResponseCreate(
        response_text="Answer 1",
        status="completed"
    )
    await save_question_response(q1_id, response1, user_id)

    # Answer second question (draft)
    q2_id = all_questions.questions[1]["id"]
    response2 = QuestionResponseCreate(
        response_text="Draft answer",
        status="draft"
    )
    await save_question_response(q2_id, response2, user_id)

    # Leave third question unanswered

    # Filter by completed
    completed = await get_questions_for_chapter(
        book_id, chapter_id, user_id, status="completed", limit=10
    )
    assert len(completed.questions) == 1
    assert completed.questions[0]["id"] == q1_id

    # Filter by draft
    draft = await get_questions_for_chapter(
        book_id, chapter_id, user_id, status="draft", limit=10
    )
    assert len(draft.questions) == 1
    assert draft.questions[0]["id"] == q2_id

    # Filter by not_answered
    not_answered = await get_questions_for_chapter(
        book_id, chapter_id, user_id, status="not_answered", limit=10
    )
    assert len(not_answered.questions) == 1
```

**Progress Tracking Test:**

```python
@pytest.mark.asyncio
async def test_chapter_question_progress_calculation(motor_reinit_db):
    """Test progress calculation with various completion states"""
    from app.db.questions import (
        create_question, save_question_response,
        get_chapter_question_progress
    )

    book_id = "book123"
    chapter_id = "ch1"
    user_id = "user123"

    # Create 10 questions
    question_ids = []
    for i in range(10):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Question {i+1}",
            question_type="text",
            category="plot",
            order=i+1
        )
        q = await create_question(question, user_id)
        question_ids.append(q["id"])

    # Initial progress: 0%
    progress = await get_chapter_question_progress(book_id, chapter_id, user_id)
    assert progress.total == 10
    assert progress.completed == 0
    assert progress.in_progress == 0
    assert progress.progress == 0.0
    assert progress.status == "not-started"

    # Complete 5 questions
    for qid in question_ids[:5]:
        response = QuestionResponseCreate(
            response_text="Completed answer",
            status="completed"
        )
        await save_question_response(qid, response, user_id)

    # Progress: 50%
    progress = await get_chapter_question_progress(book_id, chapter_id, user_id)
    assert progress.completed == 5
    assert progress.in_progress == 0
    assert progress.progress == 0.5
    assert progress.status == "in-progress"

    # Draft 3 more questions
    for qid in question_ids[5:8]:
        response = QuestionResponseCreate(
            response_text="Draft answer",
            status="draft"
        )
        await save_question_response(qid, response, user_id)

    # Progress: 50% (draft doesn't count as completed)
    progress = await get_chapter_question_progress(book_id, chapter_id, user_id)
    assert progress.completed == 5
    assert progress.in_progress == 3
    assert progress.progress == 0.5
    assert progress.status == "in-progress"

    # Complete remaining questions
    for qid in question_ids[5:]:
        response = QuestionResponseCreate(
            response_text="Completed answer",
            status="completed"
        )
        await save_question_response(qid, response, user_id)

    # Progress: 100%
    progress = await get_chapter_question_progress(book_id, chapter_id, user_id)
    assert progress.completed == 10
    assert progress.in_progress == 0
    assert progress.progress == 1.0
    assert progress.status == "completed"
```

**Key Test Files:**
- `backend/tests/test_db/test_questions.py` (NEW)
- `backend/tests/test_db/test_question_responses.py` (NEW)
- `backend/tests/test_db/test_question_progress.py` (NEW)

---

### Agent 4: FastAPI Expert - Users Endpoints (15-18 tests)

**Responsibility:** Test all user endpoints in `app/api/endpoints/users.py`

**Focus Areas:**
1. **Profile Management** (5 tests)
   - Read user profile with defaults
   - Update profile with sanitization
   - Duplicate email handling

2. **Authorization** (8 tests)
   - Self vs admin access
   - Role update restrictions
   - Forbidden operations (403)

3. **Account Operations** (5 tests)
   - Account deletion (soft delete)
   - User creation with defaults
   - Duplicate detection

**Testing Patterns to Follow:**

```python
# Example from existing test_users.py (expand on this)
@pytest.mark.asyncio
async def test_read_users_me(auth_client_factory, test_user):
    """Test /users/me endpoint returns current user's information"""
    client = await auth_client_factory()
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["clerk_id"] == test_user["clerk_id"]

    # Test preferences defaults
    assert "preferences" in data
    assert data["preferences"]["theme"] in ["light", "dark"]
```

**Authorization Test Pattern:**

```python
@pytest.mark.asyncio
async def test_update_other_user_forbidden(auth_client_factory, test_user):
    """Test non-admin cannot update other users"""
    client = await auth_client_factory()  # Regular user

    other_clerk_id = "other_clerk_id"
    update_data = {"first_name": "Hacker"}

    response = await client.put(
        f"/api/v1/users/{other_clerk_id}",
        json=update_data
    )

    assert response.status_code == 403
    assert "not enough permissions" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_can_update_other_user(admin_auth_client_factory, test_user):
    """Test admin can update other users"""
    # Create target user
    target_user_data = {
        "clerk_id": "target_user",
        "email": "target@example.com",
        "first_name": "Target",
        "last_name": "User"
    }
    client = await admin_auth_client_factory()  # Admin user
    create_resp = await client.post("/api/v1/users/", json=target_user_data)
    assert create_resp.status_code == 201

    # Admin updates target user
    update_data = {"first_name": "Updated"}
    response = await client.put(
        f"/api/v1/users/{target_user_data['clerk_id']}",
        json=update_data
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"
```

**Account Deletion Test:**

```python
@pytest.mark.asyncio
async def test_delete_profile_soft_delete(auth_client_factory, motor_reinit_db):
    """Test account deletion performs soft delete"""
    client = await auth_client_factory()

    # Delete account
    response = await client.delete("/api/v1/users/me")
    assert response.status_code == 200
    assert "successfully deleted" in response.json()["message"].lower()

    # Verify user can no longer access their profile
    response = await client.get("/api/v1/users/me")
    assert response.status_code in [401, 404]  # Depending on implementation

    # Verify audit log was created
    from app.db.base import audit_logs_collection
    audit_log = await audit_logs_collection.find_one({"action": "account_delete"})
    assert audit_log is not None
```

**Key Test Files:**
- `backend/tests/test_api/test_routes/test_users_profile.py` (NEW)
- `backend/tests/test_api/test_routes/test_users_authorization.py` (NEW)
- `backend/tests/test_api/test_routes/test_users_admin.py` (NEW)

---

## Test Infrastructure Requirements

### Fixtures Needed (add to conftest.py)

```python
@pytest.fixture
async def test_book_with_chapters(motor_reinit_db, test_user):
    """Create a test book with TOC and chapters"""
    from app.db.database import create_book

    book_data = {
        "title": "Test Book with Chapters",
        "owner_id": test_user["clerk_id"],
        "table_of_contents": {
            "chapters": [
                {
                    "id": "ch1",
                    "title": "Chapter 1",
                    "level": 1,
                    "order": 1,
                    "subchapters": [
                        {
                            "id": "ch1-1",
                            "title": "Subchapter 1.1",
                            "level": 2,
                            "order": 1
                        }
                    ]
                },
                {
                    "id": "ch2",
                    "title": "Chapter 2",
                    "level": 1,
                    "order": 2
                }
            ],
            "version": 1
        }
    }

    book = await create_book(book_data, test_user["clerk_id"])
    return book


@pytest.fixture
async def test_chapter_with_questions(motor_reinit_db, test_user):
    """Create test questions for a chapter"""
    from app.db.questions import create_question
    from app.schemas.book import QuestionCreate

    book_id = "test_book_id"
    chapter_id = "test_chapter_id"

    questions = []
    for i in range(5):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Test Question {i+1}?",
            question_type="text",
            category="plot" if i % 2 == 0 else "character",
            order=i+1
        )
        q = await create_question(question, test_user["clerk_id"])
        questions.append(q)

    return {
        "book_id": book_id,
        "chapter_id": chapter_id,
        "questions": questions
    }


@pytest.fixture
def admin_user():
    """Test admin user"""
    return {
        "_id": "admin_id",
        "id": "admin_id",
        "clerk_id": "admin_clerk_id",
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }


@pytest_asyncio.fixture
async def admin_auth_client_factory(admin_user, motor_reinit_db):
    """Create authenticated admin client"""
    from app.db.base import users_collection

    async def _factory():
        # Insert admin user
        await users_collection.insert_one(admin_user)

        # Override get_current_user to return admin
        async def mock_get_current_user():
            return admin_user

        app.dependency_overrides[get_current_user] = mock_get_current_user

        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test")
        return client

    return _factory
```

---

## Go/No-Go Criteria

### Sprint 2 Completion Checklist

**✅ MUST HAVE (Go Criteria):**
1. All 92-113 new tests implemented and passing (100% pass rate)
2. Module coverage targets met:
   - books.py: ≥80% (up from 46%)
   - toc_transactions.py: ≥85% (up from 15%)
   - questions.py: ≥85% (up from 30%)
   - users.py: ≥85% (up from 47%)
3. No regressions (all existing 189 tests still passing)
4. Overall backend coverage: ≥73% (up from ~55%)
5. Test execution time: <5 minutes total
6. All critical endpoints tested (CRUD operations, TOC generation, draft generation)

**⚠️ SHOULD HAVE (Quality Gates):**
1. All high-priority test cases implemented (90%+ of matrix)
2. Concurrency tests for TOC transactions passing
3. Authorization tests covering admin vs user roles
4. AI service mocks working correctly (no flaky tests)
5. Test isolation verified (tests can run in any order)

**🚫 BLOCKER (No-Go Criteria):**
1. Critical endpoint missing test coverage (e.g., delete_book, generate_chapter_draft)
2. Test pass rate <95%
3. Concurrency tests failing (indicates transaction bugs)
4. Module coverage below 75% (insufficient improvement)
5. Test execution time >10 minutes (too slow for CI/CD)

---

## Risk Assessment

### High Risk Areas

**1. Books.py Massive Size (2674 lines)**
- **Risk:** File too large to test efficiently, refactoring during testing will cause delays
- **Mitigation:**
  - Split tests across 5 files (CRUD, Summary, Chapters, Questions, Draft)
  - Consider creating separate test plan for books.py refactoring (Sprint 3?)
  - Use parametrized tests to reduce duplication

**2. TOC Transaction Concurrency**
- **Risk:** Race conditions and deadlocks in production if tests don't catch them
- **Mitigation:**
  - Dedicated concurrency test suite with asyncio.gather()
  - Test both transaction mode (replica set) and fallback mode (standalone)
  - Use real MongoDB (not mocks) for transaction tests

**3. AI Service Mocking Complexity**
- **Risk:** Tests become flaky if AI mocks don't match production behavior
- **Mitigation:**
  - Use consistent mock responses across all tests
  - Document AI service contracts (input/output schemas)
  - Consider creating ai_service_mocks.py helper module

### Medium Risk Areas

**1. Questions Progress Calculation Logic**
- **Risk:** Complex status aggregation logic (lines 258-281) is untested
- **Mitigation:**
  - Write property-based tests (hypothesis library) for progress calculation
  - Test all edge cases: 0%, 50%, 100%, with in_progress vs completed

**2. Authorization Edge Cases**
- **Risk:** Missing authorization tests could allow privilege escalation
- **Mitigation:**
  - Systematic testing: self vs other vs admin for every endpoint
  - Use parametrized tests to cover all role combinations

### Low Risk Areas

**1. User Profile Management**
- **Risk:** Straightforward CRUD, well-tested patterns
- **Mitigation:** Follow existing test_users.py patterns

**2. Chapter Tab State**
- **Risk:** Non-critical feature, low business impact
- **Mitigation:** Medium priority, can defer if time-constrained

---

## Sprint 2 Timeline (2 Weeks)

### Week 1: Critical & High Priority Tests

**Day 1-2: Setup & Books CRUD (Agent 1)**
- Create test file structure
- Implement fixtures (test_book_with_chapters, etc.)
- Test book CRUD: delete, PUT, PATCH (10 tests)
- Test summary management (8 tests)

**Day 3-4: TOC Transactions (Agent 2)**
- Test TOC update with transactions (7 tests)
- Test chapter add/update/delete (11 tests)
- Start concurrency tests

**Day 5: Questions Database (Agent 3)**
- Test question retrieval with filters (10 tests)
- Test response storage (6 tests)

**Day 1-5: Users Endpoints (Agent 4)**
- Test profile management (5 tests)
- Test authorization (8 tests)
- Test account operations (5 tests)

**Week 1 Target:** 60-70 tests implemented, 65-70% coverage

---

### Week 2: Remaining Tests & Refinement

**Day 6-7: Books Chapters (Agent 1)**
- Test chapter CRUD endpoints (12 tests)
- Test chapter content read/write (7 tests)
- Test chapter questions integration (10 tests)

**Day 8: TOC Concurrency & Books Draft (Agents 1 & 2)**
- Finish concurrency tests (Agent 2, 5 tests)
- Test draft generation (Agent 1, 4 tests)

**Day 9: Questions Progress & Bulk Ops (Agents 1 & 3)**
- Test progress tracking (Agent 3, 4 tests)
- Test bulk operations (Agent 1, 6 tests)

**Day 10: Testing, Documentation, & Buffer**
- Run full test suite (100% pass rate verification)
- Fix flaky tests
- Update TEST_COVERAGE_REPORT.md
- Buffer for unexpected issues

**Week 2 Target:** 92-113 tests total, 73%+ coverage

---

## Test Execution Strategy

### Parallel Execution (CI/CD)

```bash
# Run all tests in parallel (pytest-xdist)
uv run pytest -n auto --cov=app tests/ --cov-report=term-missing

# Run specific modules in parallel
uv run pytest -n 4 tests/test_api/test_routes/test_books_*.py
uv run pytest -n 2 tests/test_db/test_toc_*.py
uv run pytest -n 2 tests/test_db/test_questions*.py
uv run pytest -n 2 tests/test_api/test_routes/test_users*.py
```

### Test Organization

```
backend/tests/
├── test_api/
│   └── test_routes/
│       ├── test_books_crud.py (NEW - 10 tests)
│       ├── test_books_summary.py (NEW - 13 tests)
│       ├── test_books_chapters.py (NEW - 24 tests)
│       ├── test_books_questions.py (NEW - 10 tests)
│       ├── test_books_draft_generation.py (NEW - 4 tests)
│       ├── test_users_profile.py (NEW - 5 tests)
│       ├── test_users_authorization.py (NEW - 8 tests)
│       └── test_users_admin.py (NEW - 5 tests)
├── test_db/
│   ├── test_toc_transactions.py (NEW - 12 tests)
│   ├── test_toc_concurrency.py (NEW - 5 tests)
│   ├── test_questions.py (NEW - 10 tests)
│   ├── test_question_responses.py (NEW - 6 tests)
│   └── test_question_progress.py (NEW - 4 tests)
└── conftest.py (UPDATE - add new fixtures)
```

---

## Success Metrics

### Coverage Goals

| Module | Current | Sprint 2 Target | Tests Added | Pass Rate |
|--------|---------|-----------------|-------------|-----------|
| books.py | 46% | 80%+ | 50-60 | 100% |
| toc_transactions.py | 15% | 85%+ | 15-20 | 100% |
| questions.py | 30% | 85%+ | 12-15 | 100% |
| users.py | 47% | 85%+ | 15-18 | 100% |
| **Overall Backend** | **~55%** | **~73%** | **92-113** | **100%** |

### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test Pass Rate | 100% | All tests green in CI/CD |
| Test Execution Time | <5 minutes | pytest duration report |
| Test Isolation | 100% | Tests pass in any order |
| Mock Coverage | 100% | All AI calls mocked |
| Authorization Coverage | 100% | All endpoints tested for self/other/admin |
| Concurrency Coverage | 80% | TOC transactions tested with concurrent updates |
| Error Path Coverage | 80% | Not found, unauthorized, validation errors |

---

## Agent Coordination

### Communication Protocol

**Daily Standup (Async):**
- Each agent reports: tests completed, tests remaining, blockers
- Coordinate on shared fixtures (conftest.py updates)
- Resolve test failures immediately

**Shared Resources:**
- `conftest.py` - coordinate fixture additions
- `backend/TEST_COVERAGE_REPORT.md` - update after each day
- Test naming convention: `test_<module>_<function>_<scenario>`

**Merge Strategy:**
- Each agent works in separate test files (no conflicts)
- Daily commits to feature/p0-blockers-quick-wins
- Run full test suite before merge
- Update coverage report together on Day 10

---

## Appendix: Testing Best Practices

### 1. Async Test Lifecycle Management

```python
@pytest_asyncio.fixture(scope="function")
def event_loop():
    """Create a new event loop for each test function"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
```

### 2. Database Transaction Rollback

```python
@pytest.fixture(autouse=True)
async def motor_reinit_db():
    """Drop database before & after each test"""
    _sync_client.drop_database("auto-author-test")

    base._client = motor.motor_asyncio.AsyncIOMotorClient(TEST_MONGO_URI)
    base._db = base._client.get_default_database()

    # Set up collections
    base.users_collection = base._db.get_collection("users")
    base.books_collection = base._db.get_collection("books")
    # ...

    yield

    _sync_client.drop_database("auto-author-test")
    base._client.close()
```

### 3. Mock External Services

```python
@pytest.fixture
def mock_ai_service():
    """Mock AI service for all tests"""
    with patch("app.services.ai_service.AIService.generate_toc") as mock:
        mock.return_value = {
            "toc": {"chapters": [{"id": "ch1", "title": "Test"}]},
            "success": True
        }
        yield mock
```

### 4. Authentication Test Helpers

```python
@pytest_asyncio.fixture
async def auth_client_factory(test_user, motor_reinit_db):
    """Create authenticated test client"""
    async def _factory():
        await users_collection.insert_one(test_user)

        async def mock_get_current_user():
            return test_user

        app.dependency_overrides[get_current_user] = mock_get_current_user

        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    return _factory
```

### 5. Parametrized Tests for Role Combinations

```python
@pytest.mark.parametrize("role,expected_status", [
    ("admin", 200),  # Admin can access
    ("user", 403),   # User forbidden
])
@pytest.mark.asyncio
async def test_admin_endpoint_authorization(role, expected_status, auth_client_factory):
    """Test admin endpoint access for different roles"""
    # Create client with specified role
    client = await auth_client_factory(role=role)

    response = await client.get("/api/v1/users/admin/users")
    assert response.status_code == expected_status
```

---

## Conclusion

Sprint 2 represents a **major leap forward** in test coverage for Auto-Author's core business logic. By focusing on books endpoints, TOC transactions, questions database, and users endpoints, we address the heart of the application's functionality.

**Key Takeaways:**
1. **Books.py is massive (2674 lines, 44 endpoints)** - consider refactoring in Sprint 3
2. **Concurrency testing is critical** for TOC transactions to prevent data corruption
3. **Authorization testing is systematic** - test self/other/admin for every endpoint
4. **Progress tracking logic is complex** - use property-based testing (hypothesis)

**Next Steps After Sprint 2:**
- **Sprint 3 (P2):** Service layer tests (question_generation_service, chapter_cache_service, etc.)
- **Sprint 4 (Refactoring):** Break up books.py into smaller modules
- **Sprint 5 (Integration):** End-to-end workflow tests

**Success Definition:**
Sprint 2 is successful when we achieve **73%+ backend coverage** with **100% test pass rate**, focusing on the core business logic that powers Auto-Author's book creation workflow.

---

**Report Generated By:** Claude Code (Quality Engineer)
**Report Location:** `/home/frankbria/projects/auto-author/claudedocs/sprint2-test-plan.md`
**Next Review:** End of Week 1 (coverage check: 65-70% target)
