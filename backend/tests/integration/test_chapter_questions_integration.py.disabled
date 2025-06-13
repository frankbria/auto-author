"""
Backend Integration Test Suite for User Story 4.2 (Interview-Style Prompts)

This test suite covers end-to-end integration testing for the backend
components of the chapter questions feature, including database operations,
AI service integration, and cross-service communication.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from motor.motor_asyncio import AsyncIOMotorClient

# Import application components
from app.main import app
from app.database import get_database
from app.services.ai_service import AIService, ai_service
from app.services.question_generation_service import QuestionGenerationService
from app.schemas.book import (
    QuestionType,
    QuestionDifficulty,
    ResponseStatus,
    QuestionResponseCreate,
    GenerateQuestionsRequest
)

# Test fixtures
from tests.fixtures.question_generation_fixtures import (
    sample_questions,
    sample_question_responses,
    book_with_questions,
    ai_question_response
)


@pytest.fixture(scope="session")
async def test_db():
    """Create a test database for integration testing."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    test_db = client.test_auto_author_questions
    
    # Clean up any existing test data
    await test_db.questions.delete_many({})
    await test_db.question_responses.delete_many({})
    await test_db.question_ratings.delete_many({})
    await test_db.books.delete_many({})
    await test_db.chapters.delete_many({})
    
    yield test_db
    
    # Cleanup after tests
    await test_db.questions.delete_many({})
    await test_db.question_responses.delete_many({})
    await test_db.question_ratings.delete_many({})
    await test_db.books.delete_many({})
    await test_db.chapters.delete_many({})
    client.close()


@pytest.fixture
async def sample_data(test_db):
    """Insert sample data for integration testing."""
    # Insert test book
    book_data = {
        "_id": "integration-book-id",
        "title": "Integration Test Book",
        "genre": "Technical",
        "target_audience": "Software developers",
        "description": "A book for integration testing",
        "status": "active",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    await test_db.books.insert_one(book_data)
    
    # Insert test chapter
    chapter_data = {
        "_id": "integration-chapter-id",
        "book_id": "integration-book-id",
        "title": "Integration Test Chapter",
        "description": "Chapter for integration testing",
        "order": 1,
        "status": "draft",
        "content": "This is test content for integration testing...",
        "questions_generated": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    await test_db.chapters.insert_one(chapter_data)
    
    return {
        "book_id": "integration-book-id",
        "chapter_id": "integration-chapter-id"
    }


class TestQuestionGenerationIntegration:
    """Integration tests for question generation workflow."""

    @pytest.mark.asyncio
    async def test_full_question_generation_workflow(self, test_db, sample_data):
        """Test complete question generation workflow from request to storage."""
        # Mock AI service response
        mock_ai_response = {
            "questions": [
                {
                    "question_text": "What are the main learning objectives?",
                    "question_type": "educational",
                    "difficulty": "medium",
                    "category": "objectives",
                    "metadata": {
                        "suggested_response_length": "150-200 words",
                        "help_text": "Think about learning goals",
                        "examples": ["Understanding concepts", "Applying skills"]
                    }
                },
                {
                    "question_text": "Who is the target audience?",
                    "question_type": "audience",
                    "difficulty": "easy", 
                    "category": "planning",
                    "metadata": {
                        "suggested_response_length": "100-150 words",
                        "help_text": "Consider experience level",
                        "examples": ["Beginners", "Intermediates"]
                    }
                }
            ],
            "generation_metadata": {
                "processing_time": 2500,
                "ai_model": "gpt-4",
                "total_tokens": 3200
            }
        }

        # Create question generation service with mocked AI
        mock_ai_service = MagicMock(spec=AIService)
        mock_ai_service.generate_chapter_questions = AsyncMock(return_value=mock_ai_response)
        
        generation_service = QuestionGenerationService(mock_ai_service)
        
        # Override database dependency
        app.dependency_overrides[get_database] = lambda: test_db
        
        try:
            # Generate questions
            request_data = GenerateQuestionsRequest(
                question_types=[QuestionType.EDUCATIONAL, QuestionType.AUDIENCE],
                difficulty=QuestionDifficulty.MEDIUM,
                count=2,
                focus_areas="Learning objectives and target audience"
            )
            
            result = await generation_service.generate_questions_for_chapter(
                sample_data["book_id"],
                sample_data["chapter_id"],
                request_data
            )
            
            # Verify questions were generated and stored
            assert len(result.questions) == 2
            assert result.generation_metadata.ai_model == "gpt-4"
            
            # Verify questions in database
            stored_questions = await test_db.questions.find({
                "chapter_id": sample_data["chapter_id"]
            }).to_list(None)
            
            assert len(stored_questions) == 2
            assert stored_questions[0]["question_text"] == "What are the main learning objectives?"
            assert stored_questions[1]["question_text"] == "Who is the target audience?"
            
            # Verify chapter was marked as having questions generated
            chapter = await test_db.chapters.find_one({"_id": sample_data["chapter_id"]})
            assert chapter["questions_generated"] == True
            
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_question_regeneration_with_response_preservation(self, test_db, sample_data):
        """Test question regeneration while preserving existing responses."""
        # First, create initial questions and responses
        initial_questions = [
            {
                "_id": "q1",
                "chapter_id": sample_data["chapter_id"],
                "question_text": "Original question 1",
                "question_type": QuestionType.CONTENT,
                "difficulty": QuestionDifficulty.MEDIUM,
                "category": "content",
                "order": 1,
                "generated_at": datetime.now(timezone.utc),
                "metadata": {}
            },
            {
                "_id": "q2", 
                "chapter_id": sample_data["chapter_id"],
                "question_text": "Original question 2",
                "question_type": QuestionType.AUDIENCE,
                "difficulty": QuestionDifficulty.EASY,
                "category": "audience",
                "order": 2,
                "generated_at": datetime.now(timezone.utc),
                "metadata": {}
            }
        ]
        await test_db.questions.insert_many(initial_questions)
        
        # Add responses to the questions
        responses = [
            {
                "_id": "r1",
                "question_id": "q1",
                "response_text": "This is a response to question 1",
                "status": ResponseStatus.COMPLETE,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            },
            {
                "_id": "r2",
                "question_id": "q2", 
                "response_text": "This is a response to question 2",
                "status": ResponseStatus.DRAFT,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        ]
        await test_db.question_responses.insert_many(responses)
        
        # Mock AI service for regeneration
        mock_ai_response = {
            "questions": [
                {
                    "question_text": "What are the key learning outcomes?",
                    "question_type": "educational",
                    "difficulty": "medium",
                    "category": "objectives",
                    "metadata": {"suggested_response_length": "200 words"}
                },
                {
                    "question_text": "What practical skills will readers gain?",
                    "question_type": "practical",
                    "difficulty": "hard",
                    "category": "skills",
                    "metadata": {"suggested_response_length": "250 words"}
                }
            ],
            "generation_metadata": {
                "processing_time": 2800,
                "ai_model": "gpt-4",
                "total_tokens": 3500
            }
        }
        
        mock_ai_service = MagicMock(spec=AIService)
        mock_ai_service.generate_chapter_questions = AsyncMock(return_value=mock_ai_response)
        
        generation_service = QuestionGenerationService(mock_ai_service)
        app.dependency_overrides[get_database] = lambda: test_db
        
        try:
            # Regenerate questions with response preservation
            request_data = GenerateQuestionsRequest(
                question_types=[QuestionType.EDUCATIONAL, QuestionType.PRACTICAL],
                difficulty=QuestionDifficulty.MEDIUM,
                count=2,
                keep_responses=True
            )
            
            result = await generation_service.regenerate_questions_for_chapter(
                sample_data["chapter_id"],
                request_data
            )
            
            # Verify new questions were generated
            assert len(result.questions) == 2
            assert result.regeneration_metadata.previous_count == 2
            assert result.regeneration_metadata.kept_responses == True
            
            # Verify old questions were removed
            old_questions = await test_db.questions.find({"_id": {"$in": ["q1", "q2"]}}).to_list(None)
            assert len(old_questions) == 0
            
            # Verify responses were preserved (even though questions changed)
            preserved_responses = await test_db.question_responses.find({
                "_id": {"$in": ["r1", "r2"]}
            }).to_list(None)
            assert len(preserved_responses) == 2
            
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ai_service_integration_with_retries(self, test_db, sample_data):
        """Test AI service integration with retry logic for failures."""
        # Create a mock AI service that fails twice then succeeds
        call_count = 0
        
        async def mock_generate_with_retries(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count <= 2:
                raise Exception(f"AI service error {call_count}")
            
            return {
                "questions": [
                    {
                        "question_text": "Retry test question",
                        "question_type": "content",
                        "difficulty": "medium",
                        "category": "test",
                        "metadata": {"test": True}
                    }
                ],
                "generation_metadata": {
                    "processing_time": 3000,
                    "ai_model": "gpt-4",
                    "total_tokens": 2500,
                    "retry_count": call_count - 1
                }
            }
        
        mock_ai_service = MagicMock(spec=AIService)
        mock_ai_service.generate_chapter_questions = AsyncMock(side_effect=mock_generate_with_retries)
        
        generation_service = QuestionGenerationService(mock_ai_service)
        app.dependency_overrides[get_database] = lambda: test_db
        
        try:
            request_data = GenerateQuestionsRequest(count=1)
            
            result = await generation_service.generate_questions_for_chapter(
                sample_data["book_id"],
                sample_data["chapter_id"],
                request_data
            )
            
            # Should succeed after retries
            assert len(result.questions) == 1
            assert result.generation_metadata.retry_count == 2
            assert call_count == 3  # Failed twice, succeeded on third try
            
        finally:
            app.dependency_overrides.clear()


class TestQuestionResponseIntegration:
    """Integration tests for question response handling."""

    @pytest.mark.asyncio
    async def test_full_response_lifecycle(self, test_db, sample_data):
        """Test complete response lifecycle from creation to completion."""
        # Create a test question
        question_data = {
            "_id": "lifecycle-question",
            "chapter_id": sample_data["chapter_id"],
            "question_text": "Lifecycle test question",
            "question_type": QuestionType.CONTENT,
            "difficulty": QuestionDifficulty.MEDIUM,
            "category": "test",
            "order": 1,
            "generated_at": datetime.now(timezone.utc),
            "metadata": {}
        }
        await test_db.questions.insert_one(question_data)
        
        app.dependency_overrides[get_database] = lambda: test_db
        
        try:
            # Create initial draft response
            from app.services.question_response_service import QuestionResponseService
            response_service = QuestionResponseService()
            
            draft_response = QuestionResponseCreate(
                response_text="Initial draft response",
                status=ResponseStatus.DRAFT,
                notes="Work in progress"
            )
            
            result1 = await response_service.save_question_response(
                "lifecycle-question",
                draft_response
            )
            assert result1.success == True
            
            # Update to complete response
            complete_response = QuestionResponseCreate(
                response_text="Final complete response with detailed explanation",
                status=ResponseStatus.COMPLETE,
                notes="Ready for review"
            )
            
            result2 = await response_service.save_question_response(
                "lifecycle-question", 
                complete_response
            )
            assert result2.success == True
            
            # Verify final state in database
            stored_response = await test_db.question_responses.find_one({
                "question_id": "lifecycle-question"
            })
            
            assert stored_response["response_text"] == "Final complete response with detailed explanation"
            assert stored_response["status"] == ResponseStatus.COMPLETE
            assert stored_response["word_count"] > 0
            assert "updated_at" in stored_response
            
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_auto_save_functionality(self, test_db, sample_data):
        """Test auto-save functionality with real database operations."""
        # Create test question
        question_data = {
            "_id": "autosave-question",
            "chapter_id": sample_data["chapter_id"],
            "question_text": "Auto-save test question",
            "question_type": QuestionType.CONTENT,
            "difficulty": QuestionDifficulty.MEDIUM,
            "category": "test",
            "order": 1,
            "generated_at": datetime.now(timezone.utc),
            "metadata": {}
        }
        await test_db.questions.insert_one(question_data)
        
        app.dependency_overrides[get_database] = lambda: test_db
        
        try:
            from app.services.question_response_service import QuestionResponseService
            response_service = QuestionResponseService()
            
            # Simulate auto-save increments
            save_points = [
                "Beginning of response",
                "Beginning of response with more content",
                "Beginning of response with more content and additional details",
                "Beginning of response with more content and additional details leading to conclusion"
            ]
            
            for i, text in enumerate(save_points):
                response = QuestionResponseCreate(
                    response_text=text,
                    status=ResponseStatus.DRAFT if i < len(save_points) - 1 else ResponseStatus.COMPLETE,
                    auto_save=True
                )
                
                result = await response_service.save_question_response(
                    "autosave-question",
                    response
                )
                
                assert result.success == True
                
                # Small delay between auto-saves
                await asyncio.sleep(0.1)
            
            # Verify final auto-saved state
            stored_response = await test_db.question_responses.find_one({
                "question_id": "autosave-question"
            })
            
            assert stored_response["response_text"] == save_points[-1]
            assert stored_response["status"] == ResponseStatus.COMPLETE
            assert stored_response["revision_count"] == len(save_points)
            
        finally:
            app.dependency_overrides.clear()


class TestQuestionProgressIntegration:
    """Integration tests for question progress tracking."""

    @pytest.mark.asyncio
    async def test_progress_calculation_accuracy(self, test_db, sample_data):
        """Test accurate progress calculation with real data."""
        # Create multiple questions
        questions = []
        for i in range(5):
            question = {
                "_id": f"progress-q{i+1}",
                "chapter_id": sample_data["chapter_id"],
                "question_text": f"Progress test question {i+1}",
                "question_type": QuestionType.CONTENT,
                "difficulty": QuestionDifficulty.MEDIUM,
                "category": "test",
                "order": i + 1,
                "generated_at": datetime.now(timezone.utc),
                "metadata": {}
            }
            questions.append(question)
        
        await test_db.questions.insert_many(questions)
        
        # Create responses with different statuses
        responses = [
            {
                "_id": "pr1",
                "question_id": "progress-q1",
                "response_text": "Complete response 1",
                "status": ResponseStatus.COMPLETE,
                "created_at": datetime.now(timezone.utc)
            },
            {
                "_id": "pr2",
                "question_id": "progress-q2", 
                "response_text": "Complete response 2",
                "status": ResponseStatus.COMPLETE,
                "created_at": datetime.now(timezone.utc)
            },
            {
                "_id": "pr3",
                "question_id": "progress-q3",
                "response_text": "Draft response",
                "status": ResponseStatus.DRAFT,
                "created_at": datetime.now(timezone.utc)
            },
            {
                "_id": "pr4",
                "question_id": "progress-q4",
                "response_text": "",
                "status": ResponseStatus.SKIPPED,
                "created_at": datetime.now(timezone.utc)
            }
            # Question 5 has no response
        ]
        
        await test_db.question_responses.insert_many(responses)
        
        app.dependency_overrides[get_database] = lambda: test_db
        
        try:
            from app.services.question_progress_service import QuestionProgressService
            progress_service = QuestionProgressService()
            
            # Get progress calculation
            progress = await progress_service.get_chapter_progress(sample_data["chapter_id"])
            
            assert progress.total_questions == 5
            assert progress.answered_questions == 3  # Complete + Draft + Skipped
            assert progress.completed_questions == 2  # Only Complete
            assert progress.completion_percentage == 40  # 2/5 * 100
            assert progress.response_percentage == 60   # 3/5 * 100
            
            # Get detailed breakdown
            detailed = await progress_service.get_detailed_progress(sample_data["chapter_id"])
            
            assert detailed.by_status[ResponseStatus.COMPLETE] == 2
            assert detailed.by_status[ResponseStatus.DRAFT] == 1
            assert detailed.by_status[ResponseStatus.SKIPPED] == 1
            assert detailed.by_status.get(ResponseStatus.NOT_STARTED, 0) == 0  # Calculated
            
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_real_time_progress_updates(self, test_db, sample_data):
        """Test real-time progress updates as responses are added."""
        # Create questions
        questions = [
            {
                "_id": f"realtime-q{i+1}",
                "chapter_id": sample_data["chapter_id"],
                "question_text": f"Real-time test question {i+1}",
                "question_type": QuestionType.CONTENT,
                "difficulty": QuestionDifficulty.MEDIUM,
                "category": "test",
                "order": i + 1,
                "generated_at": datetime.now(timezone.utc),
                "metadata": {}
            }
            for i in range(3)
        ]
        
        await test_db.questions.insert_many(questions)
        
        app.dependency_overrides[get_database] = lambda: test_db
        
        try:
            from app.services.question_progress_service import QuestionProgressService
            from app.services.question_response_service import QuestionResponseService
            
            progress_service = QuestionProgressService()
            response_service = QuestionResponseService()
            
            # Initial progress (no responses)
            progress1 = await progress_service.get_chapter_progress(sample_data["chapter_id"])
            assert progress1.total_questions == 3
            assert progress1.answered_questions == 0
            assert progress1.completion_percentage == 0
            
            # Add first response
            response1 = QuestionResponseCreate(
                response_text="First response",
                status=ResponseStatus.COMPLETE
            )
            await response_service.save_question_response("realtime-q1", response1)
            
            progress2 = await progress_service.get_chapter_progress(sample_data["chapter_id"])
            assert progress2.answered_questions == 1
            assert progress2.completion_percentage == 33  # 1/3 * 100, rounded
            
            # Add second response (draft)
            response2 = QuestionResponseCreate(
                response_text="Second response draft",
                status=ResponseStatus.DRAFT
            )
            await response_service.save_question_response("realtime-q2", response2)
            
            progress3 = await progress_service.get_chapter_progress(sample_data["chapter_id"])
            assert progress3.answered_questions == 2
            assert progress3.completed_questions == 1  # Only complete responses
            assert progress3.completion_percentage == 33  # Still 1/3 complete
            assert progress3.response_percentage == 67   # 2/3 have responses
            
            # Complete the draft response
            response2_complete = QuestionResponseCreate(
                response_text="Second response completed",
                status=ResponseStatus.COMPLETE
            )
            await response_service.save_question_response("realtime-q2", response2_complete)
            
            progress4 = await progress_service.get_chapter_progress(sample_data["chapter_id"])
            assert progress4.completed_questions == 2
            assert progress4.completion_percentage == 67  # 2/3 * 100, rounded
            
        finally:
            app.dependency_overrides.clear()


class TestCrossServiceIntegration:
    """Integration tests for cross-service communication."""

    @pytest.mark.asyncio
    async def test_question_to_draft_integration(self, test_db, sample_data):
        """Test integration between question responses and draft generation."""
        # Create questions and responses
        questions_with_responses = [
            {
                "question": {
                    "_id": "draft-q1",
                    "chapter_id": sample_data["chapter_id"],
                    "question_text": "What are the key concepts?",
                    "question_type": QuestionType.CONTENT,
                    "difficulty": QuestionDifficulty.MEDIUM,
                    "category": "concepts",
                    "order": 1,
                    "generated_at": datetime.now(timezone.utc),
                    "metadata": {}
                },
                "response": {
                    "_id": "dr1",
                    "question_id": "draft-q1",
                    "response_text": "The key concepts include modularity, abstraction, and encapsulation.",
                    "status": ResponseStatus.COMPLETE,
                    "created_at": datetime.now(timezone.utc)
                }
            },
            {
                "question": {
                    "_id": "draft-q2",
                    "chapter_id": sample_data["chapter_id"],
                    "question_text": "What examples should be included?",
                    "question_type": QuestionType.CONTENT,
                    "difficulty": QuestionDifficulty.MEDIUM,
                    "category": "examples",
                    "order": 2,
                    "generated_at": datetime.now(timezone.utc),
                    "metadata": {}
                },
                "response": {
                    "_id": "dr2",
                    "question_id": "draft-q2",
                    "response_text": "Include code examples, real-world scenarios, and practical exercises.",
                    "status": ResponseStatus.COMPLETE,
                    "created_at": datetime.now(timezone.utc)
                }
            }
        ]
        
        # Insert questions and responses
        await test_db.questions.insert_many([item["question"] for item in questions_with_responses])
        await test_db.question_responses.insert_many([item["response"] for item in questions_with_responses])
        
        app.dependency_overrides[get_database] = lambda: test_db
        
        try:
            from app.services.draft_generation_service import DraftGenerationService
            
            # Mock the AI service for draft generation
            mock_draft_ai = MagicMock()
            mock_draft_ai.generate_chapter_draft = AsyncMock(return_value={
                "draft_content": "Generated chapter content incorporating question responses...",
                "metadata": {
                    "source": "questions",
                    "response_count": 2,
                    "ai_model": "gpt-4",
                    "processing_time": 4500
                }
            })
            
            draft_service = DraftGenerationService(mock_draft_ai)
            
            # Generate draft from question responses
            result = await draft_service.generate_draft_from_questions(
                sample_data["book_id"],
                sample_data["chapter_id"]
            )
            
            assert "Generated chapter content" in result.draft_content
            assert result.metadata.source == "questions"
            assert result.metadata.response_count == 2
            
            # Verify the AI service received the question responses
            mock_draft_ai.generate_chapter_draft.assert_called_once()
            call_args = mock_draft_ai.generate_chapter_draft.call_args[1]
            assert "question_responses" in call_args
            assert len(call_args["question_responses"]) == 2
            
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_analytics_integration(self, test_db, sample_data):
        """Test integration with analytics and reporting services."""
        # Create comprehensive test data
        questions = [
            {
                "_id": f"analytics-q{i+1}",
                "chapter_id": sample_data["chapter_id"],
                "question_text": f"Analytics test question {i+1}",
                "question_type": list(QuestionType)[i % len(QuestionType)],
                "difficulty": list(QuestionDifficulty)[i % len(QuestionDifficulty)],
                "category": f"category-{i % 3}",
                "order": i + 1,
                "generated_at": datetime.now(timezone.utc),
                "metadata": {}
            }
            for i in range(6)
        ]
        
        responses = [
            {
                "_id": f"ar{i+1}",
                "question_id": f"analytics-q{i+1}",
                "response_text": f"Response {i+1} " * (10 + i * 5),  # Varying lengths
                "status": list(ResponseStatus)[i % len(ResponseStatus)],
                "time_spent": (i + 1) * 120,  # Varying completion times
                "created_at": datetime.now(timezone.utc),
                "word_count": (10 + i * 5) * 2
            }
            for i in range(4)  # Only 4 responses for 6 questions
        ]
        
        ratings = [
            {
                "_id": f"rating{i+1}",
                "question_id": f"analytics-q{i+1}",
                "rating": (i % 5) + 1,
                "feedback": f"Feedback for question {i+1}",
                "created_at": datetime.now(timezone.utc)
            }
            for i in range(3)  # Only 3 ratings
        ]
        
        await test_db.questions.insert_many(questions)
        await test_db.question_responses.insert_many(responses)
        await test_db.question_ratings.insert_many(ratings)
        
        app.dependency_overrides[get_database] = lambda: test_db
        
        try:
            from app.services.analytics_service import AnalyticsService
            
            analytics_service = AnalyticsService()
            
            # Get comprehensive analytics
            analytics = await analytics_service.get_chapter_analytics(sample_data["chapter_id"])
            
            # Verify question analytics
            assert analytics.question_metrics.total_questions == 6
            assert analytics.question_metrics.response_rate == 67  # 4/6 * 100, rounded
            
            # Verify response analytics
            assert analytics.response_metrics.avg_word_count > 0
            assert analytics.response_metrics.avg_completion_time > 0
            assert len(analytics.response_metrics.by_status) > 0
            
            # Verify rating analytics
            assert analytics.rating_metrics.total_ratings == 3
            assert 1 <= analytics.rating_metrics.avg_rating <= 5
            
            # Verify category breakdown
            assert len(analytics.category_breakdown) == 3  # 3 categories
            
        finally:
            app.dependency_overrides.clear()


class TestErrorRecoveryIntegration:
    """Integration tests for error recovery and data consistency."""

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_failure(self, test_db, sample_data):
        """Test transaction rollback when operations fail partway through."""
        app.dependency_overrides[get_database] = lambda: test_db
        
        try:
            from app.services.question_generation_service import QuestionGenerationService
            
            # Create a mock AI service that fails after processing starts
            mock_ai_service = MagicMock(spec=AIService)
            
            # Mock successful initial response, then failure during processing
            mock_ai_service.generate_chapter_questions = AsyncMock(side_effect=Exception("Processing failed"))
            
            generation_service = QuestionGenerationService(mock_ai_service)
            
            # Attempt generation that should fail
            request_data = GenerateQuestionsRequest(count=3)
            
            with pytest.raises(Exception):
                await generation_service.generate_questions_for_chapter(
                    sample_data["book_id"],
                    sample_data["chapter_id"],
                    request_data
                )
            
            # Verify no partial data was left in database
            questions = await test_db.questions.find({"chapter_id": sample_data["chapter_id"]}).to_list(None)
            assert len(questions) == 0
            
            # Verify chapter status wasn't changed
            chapter = await test_db.chapters.find_one({"_id": sample_data["chapter_id"]})
            assert chapter["questions_generated"] == False
            
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_data_consistency_under_concurrent_access(self, test_db, sample_data):
        """Test data consistency when multiple operations occur concurrently."""
        # Create a test question
        question_data = {
            "_id": "concurrent-question",
            "chapter_id": sample_data["chapter_id"],
            "question_text": "Concurrent access test",
            "question_type": QuestionType.CONTENT,
            "difficulty": QuestionDifficulty.MEDIUM,
            "category": "test",
            "order": 1,
            "generated_at": datetime.now(timezone.utc),
            "metadata": {}
        }
        await test_db.questions.insert_one(question_data)
        
        app.dependency_overrides[get_database] = lambda: test_db
        
        try:
            from app.services.question_response_service import QuestionResponseService
            
            response_service = QuestionResponseService()
            
            # Simulate concurrent response updates
            async def update_response(iteration):
                response = QuestionResponseCreate(
                    response_text=f"Concurrent response update {iteration}",
                    status=ResponseStatus.DRAFT if iteration % 2 == 0 else ResponseStatus.COMPLETE
                )
                return await response_service.save_question_response(
                    "concurrent-question",
                    response
                )
            
            # Run multiple concurrent updates
            tasks = [update_response(i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All operations should succeed (last writer wins)
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == 10
            
            # Final state should be consistent
            final_response = await test_db.question_responses.find_one({
                "question_id": "concurrent-question"
            })
            
            assert final_response is not None
            assert "Concurrent response update" in final_response["response_text"]
            assert final_response["revision_count"] >= 1
            
        finally:
            app.dependency_overrides.clear()
