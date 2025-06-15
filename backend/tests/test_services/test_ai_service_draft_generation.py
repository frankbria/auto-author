"""
Test AI Service Draft Generation functionality
Tests the generate_chapter_draft method after bug fix
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.ai_service import AIService
from openai import OpenAI


class TestAIServiceDraftGeneration:
    """Test the AI service draft generation functionality."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client for testing."""
        mock_client = Mock(spec=OpenAI)
        mock_completion = Mock()
        mock_completion.choices = [
            Mock(message=Mock(content="This is a generated draft based on the Q&A responses."))
        ]
        mock_client.chat.completions.create.return_value = mock_completion
        return mock_client
    
    @pytest.fixture
    def ai_service(self, mock_openai_client):
        """Create AI service with mocked dependencies."""
        with patch('app.services.ai_service.OpenAI', return_value=mock_openai_client):
            service = AIService()
            service.client = mock_openai_client
            return service
    
    @pytest.mark.asyncio
    async def test_generate_chapter_draft_success(self, ai_service):
        """Test successful draft generation from Q&A responses."""
        # Prepare test data
        chapter_title = "Introduction to AI"
        chapter_description = "Overview of artificial intelligence concepts"
        question_responses = [
            {
                "question": "What is the main goal of this chapter?",
                "answer": "To introduce readers to AI fundamentals"
            },
            {
                "question": "What key topics will be covered?",
                "answer": "Machine learning, neural networks, and applications"
            }
        ]
        book_metadata = {
            "title": "AI for Beginners",
            "genre": "Technology",
            "target_audience": "Students and professionals"
        }
        
        # Call the method
        result = await ai_service.generate_chapter_draft(
            chapter_title=chapter_title,
            chapter_description=chapter_description,
            question_responses=question_responses,
            book_metadata=book_metadata,
            writing_style="informative",
            target_length=1000
        )
        
        # Assertions
        assert result["success"] is True
        assert "draft" in result
        assert result["draft"] == "This is a generated draft based on the Q&A responses."
        assert "metadata" in result
        assert result["metadata"]["word_count"] > 0
        assert result["metadata"]["writing_style"] == "informative"
        assert result["metadata"]["target_length"] == 1000
        assert "suggestions" in result
        
        # Verify OpenAI was called correctly
        ai_service.client.chat.completions.create.assert_called_once()
        call_args = ai_service.client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4"
        assert call_args[1]["temperature"] == 0.8
    
    @pytest.mark.asyncio
    async def test_generate_chapter_draft_with_minimal_data(self, ai_service):
        """Test draft generation with minimal required data."""
        result = await ai_service.generate_chapter_draft(
            chapter_title="Test Chapter",
            chapter_description="Test description",
            question_responses=[],
            book_metadata={}
        )
        
        assert result["success"] is True
        assert result["metadata"]["writing_style"] == "default"
        assert result["metadata"]["target_length"] == 2000
    
    @pytest.mark.asyncio
    async def test_generate_chapter_draft_handles_openai_error(self, ai_service):
        """Test error handling when OpenAI API fails."""
        # Mock an error
        ai_service.client.chat.completions.create.side_effect = Exception("OpenAI API error")
        
        result = await ai_service.generate_chapter_draft(
            chapter_title="Test Chapter",
            chapter_description="Test description",
            question_responses=[],
            book_metadata={}
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "OpenAI API error" in result["error"]
        assert "draft" in result
        assert result["draft"] == ""
    
    @pytest.mark.asyncio
    async def test_generate_chapter_draft_calculates_metadata(self, ai_service):
        """Test that metadata is correctly calculated."""
        # Mock a longer response
        long_content = " ".join(["word"] * 500)  # 500 words
        ai_service.client.chat.completions.create.return_value.choices[0].message.content = long_content
        
        result = await ai_service.generate_chapter_draft(
            chapter_title="Test",
            chapter_description="Test",
            question_responses=[],
            book_metadata={},
            target_length=400
        )
        
        assert result["metadata"]["word_count"] == 500
        assert result["metadata"]["estimated_reading_time"] == 2  # 500/200 = 2.5, rounded to 2
        assert result["metadata"]["actual_length"] == 500
        assert result["metadata"]["target_length"] == 400
    
    @pytest.mark.asyncio
    async def test_build_draft_generation_prompt(self, ai_service):
        """Test prompt building for draft generation."""
        # Access the private method for testing
        prompt = ai_service._build_draft_generation_prompt(
            chapter_title="Test Chapter",
            chapter_description="A test chapter",
            question_responses=[
                {"question": "Q1?", "answer": "A1"},
                {"question": "Q2?", "answer": "A2"}
            ],
            book_metadata={"title": "Test Book", "genre": "Fiction"},
            writing_style="casual",
            target_length=500
        )
        
        # Verify prompt contains key information
        assert "Test Chapter" in prompt
        assert "A test chapter" in prompt
        assert "Q1?" in prompt
        assert "A1" in prompt
        assert "Test Book" in prompt
        assert "Fiction" in prompt
        assert "casual" in prompt
        assert "500" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_improvement_suggestions(self, ai_service):
        """Test that improvement suggestions are generated."""
        result = await ai_service.generate_chapter_draft(
            chapter_title="Test",
            chapter_description="Test",
            question_responses=[],
            book_metadata={}
        )
        
        # The _generate_improvement_suggestions method should return a list
        assert isinstance(result["suggestions"], list)
        assert len(result["suggestions"]) > 0