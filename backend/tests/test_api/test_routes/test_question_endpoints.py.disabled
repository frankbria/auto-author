import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.schemas.book import (
    QuestionType,
    QuestionDifficulty,
    ResponseStatus
)

# Import fixtures
from ...fixtures.question_generation_fixtures import (
    sample_questions,
    sample_question_responses,
    mock_question_service,
    question_generation_request
)


@pytest.fixture
def app_with_question_routes(mock_auth):
    """Create a test app with question routes and mock auth."""
    from app.main import app
    
    # Mock the get_question_generation_service function
    with patch("app.api.endpoints.books.get_question_generation_service") as mock_get_service:
        # Setup the mock service to be returned
        mock_get_service.return_value = mock_question_service
        
        # Return the app for testing
        yield app


@pytest.fixture
def client(app_with_question_routes):
    """Create a test client for the app."""
    return TestClient(app_with_question_routes)


class TestQuestionEndpoints:
    """Tests for the question-related API endpoints."""
    
    def test_generate_questions(self, client, mock_auth, question_generation_request):
        """Test the generate questions endpoint."""
        # Create the request body
        request_body = {
            "count": question_generation_request["count"],
            "difficulty": question_generation_request["difficulty"].value if question_generation_request["difficulty"] else None,
            "focus": [q_type.value for q_type in question_generation_request["focus"]] if question_generation_request["focus"] else None
        }
        
        # Make the request
        response = client.post(
            "/api/v1/books/test-book-id/chapters/ch-test-1/generate-questions",
            json=request_body,
            headers=mock_auth["headers"]
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert "generation_id" in data
        assert "total" in data
        assert data["total"] == 2
    
    def test_list_questions(self, client, mock_auth):
        """Test the list questions endpoint."""
        # Make the request
        response = client.get(
            "/api/v1/books/test-book-id/chapters/ch-test-1/questions",
            headers=mock_auth["headers"]
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
    
    def test_list_questions_with_filters(self, client, mock_auth):
        """Test the list questions endpoint with filters."""
        # Make the request with query parameters
        response = client.get(
            "/api/v1/books/test-book-id/chapters/ch-test-1/questions?status=completed&category=character&question_type=character&page=1&limit=10",
            headers=mock_auth["headers"]
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
    
    def test_save_question_response(self, client, mock_auth):
        """Test saving a question response."""
        # Create the request body
        request_body = {
            "response_text": "This is a test response.",
            "status": ResponseStatus.DRAFT.value
        }
        
        # Make the request
        response = client.put(
            "/api/v1/books/test-book-id/chapters/ch-test-1/questions/q-mock-1/response",
            json=request_body,
            headers=mock_auth["headers"]
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "success" in data
        assert data["success"] == True
        assert "message" in data
        assert data["response"]["response_text"] == "Mock response text"
    
    def test_get_question_response(self, client, mock_auth):
        """Test getting a question response."""
        # Make the request
        response = client.get(
            "/api/v1/books/test-book-id/chapters/ch-test-1/questions/q-mock-1/response",
            headers=mock_auth["headers"]
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "has_response" in data
        assert "success" in data
        assert data["success"] == True
    
    def test_rate_question(self, client, mock_auth):
        """Test rating a question."""
        # Create the request body
        request_body = {
            "rating": 4,
            "feedback": "Good question"
        }
        
        # Make the request
        response = client.post(
            "/api/v1/books/test-book-id/chapters/ch-test-1/questions/q-mock-1/rating",
            json=request_body,
            headers=mock_auth["headers"]
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] == True
        assert "message" in data
    
    def test_get_question_progress(self, client, mock_auth):
        """Test getting question progress for a chapter."""
        # Make the request
        response = client.get(
            "/api/v1/books/test-book-id/chapters/ch-test-1/question-progress",
            headers=mock_auth["headers"]
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "completed" in data
        assert "progress" in data
        assert "status" in data
        assert data["total"] == 5
        assert data["completed"] == 2
        assert data["progress"] == 0.4
        assert data["status"] == "in-progress"
    
    def test_regenerate_questions(self, client, mock_auth, question_generation_request):
        """Test regenerating questions for a chapter."""
        # Create the request body
        request_body = {
            "count": question_generation_request["count"],
            "difficulty": question_generation_request["difficulty"].value if question_generation_request["difficulty"] else None,
            "focus": [q_type.value for q_type in question_generation_request["focus"]] if question_generation_request["focus"] else None
        }
        
        # Make the request
        response = client.post(
            "/api/v1/books/test-book-id/chapters/ch-test-1/regenerate-questions?preserve_responses=true",
            json=request_body,
            headers=mock_auth["headers"]
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert "generation_id" in data
        assert "total" in data
        assert data["total"] == 2
