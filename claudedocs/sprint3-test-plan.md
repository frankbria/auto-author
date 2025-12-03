# Sprint 3 Test Plan - P2 Service Layer Coverage

**Date**: 2025-12-03
**Sprint Duration**: 1 week
**Target**: 45-60 new tests, 80%+ coverage on selected services
**Current Service Layer Coverage**: 34% (2128/3202 lines uncovered)

---

## Service Layer Coverage Analysis

### ✅ Already Well-Covered (>80% - No Action Needed)
| Service | Coverage | Lines | Status |
|---------|----------|-------|--------|
| chapter_access_service | 100% | 32/32 | ✅ Complete |
| chapter_status_service | 99% | 67/68 | ✅ Complete |
| export_service | 95% | 187/196 | ✅ Complete |
| file_upload_service | 95% | 110/116 | ✅ Complete |
| transcription_service | 96% | 54/56 | ✅ Complete |
| transcription_service_aws | 93% | 95/102 | ✅ Complete |
| cloud_storage_service | 91% | 85/93 | ✅ Complete |
| session_service | 83% | 89/107 | ✅ Complete |
| ai_service | 82% | 229/279 | ✅ Complete |

**Total**: 9 services with >80% coverage (948 lines covered)

---

## 🎯 Sprint 3 Target Services

### Priority 1: Question Services (Critical Business Logic)

#### 1. question_generation_service.py
- **Current Coverage**: 51% (126/246 lines covered)
- **File Size**: 30K (large, complex)
- **Priority**: 🔴 CRITICAL - Core authoring workflow
- **Target**: 80% coverage
- **Estimated Tests**: 12-15 tests
- **Complexity**: High (AI integration, workflow orchestration)

**Key Functionalities to Test:**
- `generate_questions()` - Generate questions from book summary
- `generate_followup_questions()` - Context-aware follow-ups
- `validate_question_quality()` - Quality thresholds
- `batch_generate_questions()` - Bulk generation
- `retry_failed_generation()` - Error recovery
- `question_deduplication()` - Duplicate detection
- AI prompt construction and response parsing
- Error handling (AI failures, timeout, rate limits)

#### 2. question_quality_service.py
- **Current Coverage**: 0% (170/170 lines uncovered)
- **File Size**: 15K (medium complexity)
- **Priority**: 🔴 CRITICAL - Quality assurance
- **Target**: 85% coverage
- **Estimated Tests**: 10-12 tests
- **Complexity**: Medium (scoring algorithms)

**Key Functionalities to Test:**
- `assess_question_quality()` - Multi-dimensional quality scoring
- `validate_question_clarity()` - Readability checks
- `check_question_relevance()` - Context alignment
- `detect_ambiguous_questions()` - Ambiguity detection
- `score_question_difficulty()` - Difficulty rating
- `suggest_question_improvements()` - Enhancement recommendations
- Quality thresholds and acceptance criteria

#### 3. question_feedback_service.py
- **Current Coverage**: 0% (266/266 lines uncovered)
- **File Size**: 26K (medium-large complexity)
- **Priority**: 🟡 HIGH - User feedback loop
- **Target**: 85% coverage
- **Estimated Tests**: 8-10 tests
- **Complexity**: Medium (feedback processing)

**Key Functionalities to Test:**
- `submit_question_feedback()` - User feedback submission
- `aggregate_feedback_scores()` - Feedback aggregation
- `identify_problematic_questions()` - Problem detection
- `trigger_question_regeneration()` - Auto-regeneration
- `track_feedback_trends()` - Analytics
- `export_feedback_report()` - Reporting

#### 4. genre_question_templates.py
- **Current Coverage**: 0% (122/122 lines uncovered)
- **File Size**: 24K (medium complexity)
- **Priority**: 🟡 HIGH - Template management
- **Target**: 85% coverage
- **Estimated Tests**: 6-8 tests
- **Complexity**: Low-Medium (template lookups)

**Key Functionalities to Test:**
- `get_genre_templates()` - Template retrieval by genre
- `customize_template_for_book()` - Template customization
- `validate_template_coverage()` - Completeness checks
- `merge_genre_templates()` - Multi-genre support
- Template variable substitution
- Fallback to default templates

---

### Priority 2: Chapter Management Services

#### 5. chapter_cache_service.py
- **Current Coverage**: 0% (198/198 lines uncovered)
- **File Size**: 17K (medium complexity)
- **Priority**: 🟡 HIGH - Performance optimization
- **Target**: 80% coverage
- **Estimated Tests**: 8-10 tests
- **Complexity**: Medium (caching strategies)

**Key Functionalities to Test:**
- `cache_chapter_content()` - Content caching
- `get_cached_chapter()` - Cache retrieval
- `invalidate_chapter_cache()` - Cache invalidation
- `warm_cache_for_book()` - Preloading
- Cache TTL and expiration
- Cache hit/miss ratio tracking
- Memory pressure handling

#### 6. chapter_error_handler.py
- **Current Coverage**: 0% (263/263 lines uncovered)
- **File Size**: 22K (medium-large complexity)
- **Priority**: 🟡 HIGH - Error resilience
- **Target**: 80% coverage
- **Estimated Tests**: 6-8 tests
- **Complexity**: Medium (error classification)

**Key Functionalities to Test:**
- `handle_chapter_error()` - Error routing
- `classify_error_severity()` - Severity categorization
- `retry_failed_operation()` - Retry logic
- `log_chapter_error()` - Error tracking
- `send_error_notification()` - Alert system
- Circuit breaker pattern implementation

---

### Priority 3: Advanced Features (If Time Permits)

#### 7. content_analysis_service.py
- **Current Coverage**: 0% (329/329 lines uncovered)
- **File Size**: 35K (very large complexity)
- **Priority**: 🟢 MEDIUM - Analytics
- **Target**: 75% coverage
- **Estimated Tests**: 6-8 tests
- **Complexity**: High (NLP, analytics)

**Defer to Sprint 4 if time is limited**

#### 8. user_level_adaptation.py
- **Current Coverage**: 0% (178/178 lines uncovered)
- **File Size**: 24K (medium complexity)
- **Priority**: 🟢 MEDIUM - Personalization
- **Target**: 75% coverage
- **Estimated Tests**: 4-6 tests
- **Complexity**: Medium (user modeling)

**Defer to Sprint 4 if time is limited**

---

## Sprint 3 Test Matrix

### Test Distribution

| Service | Current | Target | Gap | Tests | Agent |
|---------|---------|--------|-----|-------|-------|
| question_generation_service | 51% | 80% | +29% | 12-15 | python-expert |
| question_quality_service | 0% | 85% | +85% | 10-12 | python-expert |
| question_feedback_service | 0% | 85% | +85% | 8-10 | fastapi-expert |
| genre_question_templates | 0% | 85% | +85% | 6-8 | python-expert |
| chapter_cache_service | 0% | 80% | +80% | 8-10 | python-expert |
| chapter_error_handler | 0% | 80% | +80% | 6-8 | python-expert |

**Total Target**: 50-63 tests (meets 45-60 target)

---

## Agent Assignments

### Agent 1: python-expert (Question Generation)
**Module**: `app/services/question_generation_service.py`
**Current**: 51% coverage
**Target**: 80% coverage
**Tests**: 12-15 tests

**Test Scenarios**:
1. Generate questions from valid summary (success)
2. Generate follow-up questions (context-aware)
3. Validate question quality thresholds
4. Batch generation (multiple chapters)
5. AI failure handling (timeout, rate limit, invalid response)
6. Question deduplication logic
7. Retry mechanism with exponential backoff
8. Edge cases (empty summary, very long summary, special characters)
9. Prompt construction validation
10. Response parsing (valid/invalid AI responses)
11. Concurrent generation requests
12. Question count validation (min/max)

### Agent 2: python-expert (Question Quality)
**Module**: `app/services/question_quality_service.py`
**Current**: 0% coverage
**Target**: 85% coverage
**Tests**: 10-12 tests

**Test Scenarios**:
1. Assess overall question quality (multi-dimensional scoring)
2. Validate question clarity (readability metrics)
3. Check relevance to book context
4. Detect ambiguous questions
5. Score question difficulty levels
6. Suggest improvements for low-quality questions
7. Quality threshold enforcement
8. Batch quality assessment
9. Edge cases (very short/long questions, special formatting)
10. Language-specific quality checks

### Agent 3: fastapi-expert (Question Feedback)
**Module**: `app/services/question_feedback_service.py`
**Current**: 0% coverage
**Target**: 85% coverage
**Tests**: 8-10 tests

**Test Scenarios**:
1. Submit user feedback (ratings, comments)
2. Aggregate feedback scores across questions
3. Identify problematic questions (low ratings)
4. Trigger auto-regeneration for poor questions
5. Track feedback trends over time
6. Export feedback reports
7. Handle duplicate feedback submissions
8. Validate feedback data schema

### Agent 4: python-expert (Templates + Cache + Error Handler)
**Modules**:
- `app/services/genre_question_templates.py` (6-8 tests)
- `app/services/chapter_cache_service.py` (8-10 tests)
- `app/services/chapter_error_handler.py` (6-8 tests)

**Total Tests**: 20-26 tests

**Test Scenarios**:

**Templates (6-8 tests):**
1. Get templates by genre
2. Customize template for specific book
3. Validate template coverage
4. Multi-genre template merging
5. Template variable substitution
6. Fallback to defaults

**Cache (8-10 tests):**
1. Cache chapter content
2. Retrieve cached chapter
3. Cache invalidation
4. Warm cache for book
5. TTL expiration
6. Cache hit/miss tracking
7. Memory pressure handling
8. Concurrent cache access

**Error Handler (6-8 tests):**
1. Route different error types
2. Classify error severity
3. Retry failed operations
4. Error logging and tracking
5. Alert notifications
6. Circuit breaker activation

---

## Test File Structure

```
tests/test_services/
├── test_question_generation_comprehensive.py      # 12-15 tests (Agent 1)
├── test_question_quality.py                       # 10-12 tests (Agent 2)
├── test_question_feedback.py                      # 8-10 tests (Agent 3)
├── test_genre_templates.py                        # 6-8 tests (Agent 4)
├── test_chapter_cache.py                          # 8-10 tests (Agent 4)
└── test_chapter_error_handler.py                  # 6-8 tests (Agent 4)
```

---

## Test Patterns and Standards

### Required Test Structure
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.question_generation_service import generate_questions
from app.models.questions import QuestionRequest, QuestionResponse

@pytest.mark.asyncio
async def test_generate_questions_success():
    """Test successful question generation from book summary"""
    # Arrange
    book_id = "test_book_123"
    summary = "A compelling story about..."

    # Mock AI service response
    with patch('app.services.ai_service.generate_text') as mock_ai:
        mock_ai.return_value = AsyncMock(return_value={
            "questions": [...]
        })

        # Act
        result = await generate_questions(book_id, summary)

        # Assert
        assert len(result.questions) == 5
        assert all(q.relevance_score >= 0.7 for q in result.questions)
        mock_ai.assert_called_once()
```

### Mock Strategy
- **External APIs**: Mock all AI service calls
- **Database**: Use test fixtures with cleanup
- **Cache**: Mock Redis operations
- **File System**: Use temporary directories
- **Time**: Mock datetime for TTL tests

### Coverage Requirements
- **Minimum**: 80% line coverage per module
- **Target**: 85% line coverage per module
- **Pass Rate**: 100% on implemented features
- **Skipped**: Document unimplemented features

---

## Sprint 3 Execution Plan

### Day 1: Setup & Planning (0.5 day)
- [ ] Analyze service modules in detail
- [ ] Create test plan document (this file)
- [ ] Set up test file structure
- [ ] Configure pytest fixtures

### Day 2-3: Parallel Test Implementation (2 days)
- [ ] Agent 1: Question generation tests (12-15 tests)
- [ ] Agent 2: Question quality tests (10-12 tests)
- [ ] Agent 3: Question feedback tests (8-10 tests)
- [ ] Agent 4: Templates + Cache + Error handler (20-26 tests)

**All agents run in parallel** - spawn in single message

### Day 4: Test Execution & Bug Fixes (1 day)
- [ ] Run full test suite
- [ ] Fix failing tests
- [ ] Achieve 100% pass rate on implemented features
- [ ] Document skipped tests (if any unimplemented features)

### Day 5: Coverage Validation & Documentation (0.5 day)
- [ ] Verify 80%+ coverage achieved
- [ ] Generate coverage reports
- [ ] Create Sprint 3 final report
- [ ] Update SESSION.md

---

## Success Criteria

### Must Have (Sprint 3 Complete)
- ✅ 50-63 new tests created
- ✅ 100% pass rate on implemented features
- ✅ 80%+ coverage on 6 target services
- ✅ All tests follow TDD patterns
- ✅ Comprehensive mocking of external dependencies
- ✅ Documentation of any unimplemented features

### Nice to Have (Stretch Goals)
- 🎯 Cover content_analysis_service (defer to Sprint 4 if time-limited)
- 🎯 Cover user_level_adaptation (defer to Sprint 4 if time-limited)
- 🎯 Achieve 85%+ coverage (exceed 80% target)

---

## Risk Assessment

### Low Risk
- Templates and cache services (straightforward logic)
- Quality service (scoring algorithms well-defined)

### Medium Risk
- Question generation (AI integration complexity)
- Error handler (complex state management)

### High Risk
- Feedback service (depends on analytics infrastructure)

### Mitigation
- Mock all external dependencies
- Use async test patterns consistently
- Document any infrastructure limitations
- Skip tests for truly missing features (with documentation)

---

## Expected Outcomes

### Coverage Improvements
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Service Layer Coverage | 34% | 65-70% | +31-36% |
| Test Count | ~50 | ~110 | +50-63 |
| 0% Coverage Services | 9 | 3-5 | -4-6 |

### Quality Metrics
- 100% pass rate on implemented features
- 0 test failures (except documented unimplemented features)
- 80%+ coverage on all target services
- <5% test flakiness

---

**Last Updated**: 2025-12-03
**Next Review**: After Sprint 3 execution (Day 5)
