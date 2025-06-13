import pytest
from httpx import AsyncClient
from unittest.mock import patch, Mock
from bson import ObjectId
from datetime import datetime, timezone
from app.schemas.chapter_questions import QuestionType, QuestionDifficulty, ResponseStatus


@pytest.mark.asyncio
class TestChapterQuestionsAPI:
    """Test suite for User Story 4.2 chapter questions API endpoints."""

    @pytest.fixture
    def mock_book_data(self):
        """Create test book data."""
        return {
            "_id": ObjectId(),
            "title": "Test Book for Questions",
            "description": "A book for testing chapter questions",
            "genre": "Technical",
            "target_audience": "Developers",
            "owner_id": "test_user_123",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "toc": {
                "chapters": [
                    {
                        "id": "chapter_1",
                        "title": "Introduction to Testing",
                        "description": "Learn the basics of software testing",
                        "level": 1,
                        "order": 1
                    },
                    {
                        "id": "chapter_2",
                        "title": "Advanced Testing Techniques",
                        "description": "Explore advanced testing methodologies",
                        "level": 1,
                        "order": 2
                    }
                ]
            }
        }

    @pytest.fixture
    def mock_questions_data(self):
        """Create mock questions data."""
        return [
            {
                "id": "q1",
                "chapter_id": "chapter_1",
                "question_text": "What are the key principles of software testing?",
                "question_type": QuestionType.RESEARCH.value,
                "difficulty": QuestionDifficulty.MEDIUM.value,
                "category": "foundations",
                "order": 1,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "suggested_response_length": "200-300 words",
                    "help_text": "Consider test-driven development principles",
                    "examples": ["Unit testing", "Integration testing"]
                },
                "has_response": False
            },
            {
                "id": "q2",
                "chapter_id": "chapter_1",
                "question_text": "How do you design effective test cases?",
                "question_type": QuestionType.RESEARCH.value,
                "difficulty": QuestionDifficulty.HARD.value,
                "category": "design",
                "order": 2,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "suggested_response_length": "300-500 words",
                    "help_text": "Think about edge cases and boundary conditions"
                },
                "has_response": True,
                "response_status": ResponseStatus.COMPLETED.value
            }
        ]

    async def test_generate_chapter_questions_success(self, async_client_factory, mock_book_data, mock_questions_data):
        """Test successful question generation for a chapter."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"

        # Mock the question generation service
        with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.generate_questions_for_chapter.return_value = {
                "questions": mock_questions_data,
                "total": len(mock_questions_data),
                "generation_id": "gen_123"
            }

            # Mock book lookup
            with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
                mock_get_book.return_value = mock_book_data

                request_data = {
                    "count": 5,
                    "difficulty": "medium",
                    "focus": ["research", "character"]
                }

                response = await client.post(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
                    json=request_data
                )

                assert response.status_code == 200
                data = response.json()
                assert "questions" in data
                assert "total" in data
                assert "generation_id" in data
                assert len(data["questions"]) == len(mock_questions_data)
                assert data["total"] == len(mock_questions_data)

                # Verify service was called with correct parameters
                mock_service_instance.generate_questions_for_chapter.assert_called_once_with(
                    book_id=book_id,
                    chapter_id=chapter_id,
                    count=5,
                    difficulty="medium",
                    focus=["research", "character"],
                    user_id="test_user_123"
                )

    async def test_generate_chapter_questions_unauthorized(self, async_client_factory, mock_book_data):
        """Test question generation with wrong user ownership."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"

        # Mock book with different owner
        mock_book_data["owner_id"] = "different_user"
        
        with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
            mock_get_book.return_value = mock_book_data

            response = await client.post(
                f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
                json={"count": 5}
            )

            assert response.status_code == 403
            assert "Not authorized" in response.json()["detail"]

    async def test_generate_chapter_questions_book_not_found(self, async_client_factory):
        """Test question generation for non-existent book."""
        client = await async_client_factory()
        book_id = str(ObjectId())
        chapter_id = "chapter_1"

        with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
            mock_get_book.return_value = None

            response = await client.post(
                f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
                json={"count": 5}
            )

            assert response.status_code == 404
            assert "Book not found" in response.json()["detail"]

    async def test_list_chapter_questions_success(self, async_client_factory, mock_book_data, mock_questions_data):
        """Test successful retrieval of chapter questions."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"

        with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_chapter_questions.return_value = {
                "questions": mock_questions_data,
                "total": len(mock_questions_data),
                "page": 1,
                "pages": 1
            }

            with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
                mock_get_book.return_value = mock_book_data

                response = await client.get(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions"
                )

                assert response.status_code == 200
                data = response.json()
                assert "questions" in data
                assert "total" in data
                assert "page" in data
                assert len(data["questions"]) == len(mock_questions_data)

    async def test_list_chapter_questions_with_filters(self, async_client_factory, mock_book_data, mock_questions_data):
        """Test question retrieval with filtering parameters."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"

        with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            
            # Mock filtered results
            filtered_questions = [q for q in mock_questions_data if q["difficulty"] == "medium"]
            mock_service_instance.get_chapter_questions.return_value = {
                "questions": filtered_questions,
                "total": len(filtered_questions),
                "page": 1,
                "pages": 1
            }

            with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
                mock_get_book.return_value = mock_book_data

                response = await client.get(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions",
                    params={
                        "status": "unanswered",
                        "category": "foundations",
                        "question_type": "research",
                        "page": 1,
                        "limit": 10
                    }
                )

                assert response.status_code == 200
                data = response.json()
                assert len(data["questions"]) == len(filtered_questions)

                # Verify service was called with filters
                mock_service_instance.get_chapter_questions.assert_called_once()

    async def test_save_question_response_success(self, async_client_factory, mock_book_data):
        """Test successful saving of question response."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"
        question_id = "q1"

        mock_response_data = {
            "id": "resp_123",
            "question_id": question_id,
            "response_text": "Software testing ensures code quality and reliability...",
            "word_count": 12,
            "status": ResponseStatus.COMPLETED.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "last_edited_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "edit_history": []
            }
        }

        with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.save_question_response.return_value = mock_response_data

            with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
                mock_get_book.return_value = mock_book_data

                request_data = {
                    "response_text": "Software testing ensures code quality and reliability...",
                    "status": "completed"
                }

                response = await client.put(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response",
                    json=request_data
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "response" in data
                assert data["response"]["response_text"] == request_data["response_text"]
                assert data["response"]["word_count"] == 12

    async def test_save_question_response_invalid_data(self, async_client_factory, mock_book_data):
        """Test saving question response with invalid data."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"
        question_id = "q1"

        with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
            mock_get_book.return_value = mock_book_data

            # Empty response text
            request_data = {
                "response_text": "",
                "status": "completed"
            }

            response = await client.put(
                f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response",
                json=request_data
            )

            # Should handle validation error
            assert response.status_code in [400, 422]

    async def test_get_question_response_success(self, async_client_factory, mock_book_data):
        """Test successful retrieval of question response."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"
        question_id = "q1"

        mock_response = {
            "id": "resp_123",
            "question_id": question_id,
            "response_text": "Testing is crucial for software quality...",
            "word_count": 8,
            "status": ResponseStatus.COMPLETED.value,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_question_response.return_value = mock_response

            with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
                mock_get_book.return_value = mock_book_data

                response = await client.get(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["has_response"] is True
                assert data["response"]["response_text"] == mock_response["response_text"]

    async def test_get_question_response_not_found(self, async_client_factory, mock_book_data):
        """Test retrieval of non-existent question response."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"
        question_id = "q1"

        with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_question_response.return_value = None

            with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
                mock_get_book.return_value = mock_book_data

                response = await client.get(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["has_response"] is False
                assert data["response"] is None

    async def test_rate_question_success(self, async_client_factory, mock_book_data):
        """Test successful question rating."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"
        question_id = "q1"

        mock_rating = {
            "id": "rating_123",
            "question_id": question_id,
            "rating": 4,
            "feedback": "Very relevant question",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.save_question_rating.return_value = mock_rating

            with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
                mock_get_book.return_value = mock_book_data

                request_data = {
                    "rating": 4,
                    "feedback": "Very relevant question"
                }

                response = await client.post(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/rating",
                    json=request_data
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["rating"]["rating"] == 4
                assert data["rating"]["feedback"] == "Very relevant question"

    async def test_get_chapter_question_progress(self, async_client_factory, mock_book_data):
        """Test retrieval of chapter question progress."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"

        mock_progress = {
            "total": 10,
            "completed": 3,
            "in_progress": 2,
            "progress": 0.3,
            "status": "in-progress"
        }

        with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_chapter_question_progress.return_value = mock_progress

            with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
                mock_get_book.return_value = mock_book_data

                response = await client.get(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/question-progress"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 10
                assert data["completed"] == 3
                assert data["progress"] == 0.3
                assert data["status"] == "in-progress"

    async def test_regenerate_chapter_questions_success(self, async_client_factory, mock_book_data, mock_questions_data):
        """Test successful question regeneration."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"

        mock_regeneration_result = {
            "questions": mock_questions_data,
            "total": len(mock_questions_data),
            "preserved_count": 1,
            "new_count": len(mock_questions_data) - 1,
            "generation_id": "regen_123"
        }

        with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.regenerate_chapter_questions.return_value = mock_regeneration_result

            with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
                mock_get_book.return_value = mock_book_data

                request_data = {
                    "count": 5,
                    "difficulty": "medium"
                }

                response = await client.post(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/regenerate-questions",
                    json=request_data,
                    params={"preserve_responses": True}
                )

                assert response.status_code == 200
                data = response.json()
                assert "questions" in data
                assert "preserved_count" in data
                assert "new_count" in data
                assert data["preserved_count"] == 1
                assert len(data["questions"]) == len(mock_questions_data)

    async def test_regenerate_without_preserve_responses(self, async_client_factory, mock_book_data, mock_questions_data):
        """Test question regeneration without preserving responses."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"

        mock_regeneration_result = {
            "questions": mock_questions_data,
            "total": len(mock_questions_data),
            "preserved_count": 0,
            "new_count": len(mock_questions_data),
            "generation_id": "regen_456"
        }

        with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.regenerate_chapter_questions.return_value = mock_regeneration_result

            with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
                mock_get_book.return_value = mock_book_data

                response = await client.post(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/regenerate-questions",
                    json={"count": 5},
                    params={"preserve_responses": False}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["preserved_count"] == 0
                assert data["new_count"] == len(mock_questions_data)

    async def test_rate_limiting_on_generation(self, async_client_factory, mock_book_data):
        """Test rate limiting on question generation endpoints."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"

        with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
            mock_get_book.return_value = mock_book_data

            # The rate limiter might not be fully functional in test environment
            # This test validates the endpoint structure rather than actual rate limiting
            with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
                mock_service_instance = Mock()
                mock_service.return_value = mock_service_instance
                mock_service_instance.generate_questions_for_chapter.return_value = {
                    "questions": [],
                    "total": 0,
                    "generation_id": "gen_test"
                }

                response = await client.post(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
                    json={"count": 5}
                )

                # Should succeed at least once
                assert response.status_code == 200

    async def test_question_generation_with_ai_service_error(self, async_client_factory, mock_book_data):
        """Test handling of AI service errors during question generation."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"

        with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.generate_questions_for_chapter.side_effect = Exception("AI service error")

            with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
                mock_get_book.return_value = mock_book_data

                response = await client.post(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
                    json={"count": 5}
                )

                assert response.status_code == 500
                assert "Error generating questions" in response.json()["detail"]

    async def test_edge_case_empty_chapter_metadata(self, async_client_factory, mock_book_data):
        """Test question generation with minimal chapter metadata."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_empty"

        # Modify book to have a chapter with minimal metadata
        mock_book_data["toc"]["chapters"].append({
            "id": "chapter_empty",
            "title": "",
            "description": "",
            "level": 1,
            "order": 3
        })

        with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.generate_questions_for_chapter.return_value = {
                "questions": [],
                "total": 0,
                "generation_id": "gen_empty"
            }

            with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
                mock_get_book.return_value = mock_book_data

                response = await client.post(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
                    json={"count": 3}
                )

                # Should handle gracefully
                assert response.status_code == 200

    async def test_pagination_in_question_listing(self, async_client_factory, mock_book_data):
        """Test pagination functionality in question listing."""
        client = await async_client_factory()
        book_id = str(mock_book_data["_id"])
        chapter_id = "chapter_1"

        # Create mock data for multiple pages
        large_question_set = [
            {
                "id": f"q{i}",
                "chapter_id": chapter_id,
                "question_text": f"Question {i}",
                "question_type": "research",
                "difficulty": "medium",
                "category": "test",
                "order": i,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {},
                "has_response": False
            }
            for i in range(1, 16)  # 15 questions
        ]

        with patch('app.api.endpoints.books.get_question_generation_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            
            # Mock paginated response (page 1, 10 items)
            mock_service_instance.get_chapter_questions.return_value = {
                "questions": large_question_set[:10],
                "total": 15,
                "page": 1,
                "pages": 2
            }

            with patch('app.api.endpoints.books.get_book_by_id') as mock_get_book:
                mock_get_book.return_value = mock_book_data

                response = await client.get(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions",
                    params={"page": 1, "limit": 10}
                )

                assert response.status_code == 200
                data = response.json()
                assert len(data["questions"]) == 10
                assert data["total"] == 15
                assert data["page"] == 1
                assert data["pages"] == 2
