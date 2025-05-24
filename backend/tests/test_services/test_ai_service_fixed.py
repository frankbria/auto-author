# backend/tests/test_services/test_ai_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from app.services.ai_service import AIService, ai_service


class TestAIService:
    """Test cases for AI service functionality."""

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        mock_client = Mock()
        return mock_client

    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI response object."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
READINESS: Ready
CONFIDENCE: 0.8
ANALYSIS: This summary provides clear structure and actionable content suitable for TOC generation.
SUGGESTIONS: Consider adding more specific examples. Include target audience details.
"""
        return mock_response

    @pytest.fixture
    def mock_questions_response(self):
        """Mock OpenAI response for questions generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
1. What is the main problem your book addresses?
2. Who is your target audience and their expertise level?
3. What are the key concepts you want to cover?
4. What practical outcomes should readers achieve?
"""
        return mock_response

    @pytest.fixture
    def mock_toc_response(self):
        """Mock OpenAI response for TOC generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
{
  "chapters": [
    {
      "id": "ch1",
      "title": "Getting Started",
      "description": "Introduction to web development",
      "level": 1,
      "order": 1,
      "subchapters": [
        {"id": "ch1-1", "title": "Setting Up Your Environment", "description": "Dev environment setup", "level": 2, "order": 1},
        {"id": "ch1-2", "title": "Basic HTML Structure", "description": "HTML fundamentals", "level": 2, "order": 2}
      ]
    },
    {
      "id": "ch2",
      "title": "Advanced Concepts",
      "description": "Advanced web development topics",
      "level": 1,
      "order": 2,
      "subchapters": [
        {"id": "ch2-1", "title": "JavaScript Frameworks", "description": "Modern JS frameworks", "level": 2, "order": 1},
        {"id": "ch2-2", "title": "Database Integration", "description": "Working with databases", "level": 2, "order": 2}
      ]
    }
  ],
  "total_chapters": 2,
  "estimated_pages": 200
}
"""
        return mock_response

    @pytest.fixture
    def mock_invalid_toc_response(self):
        """Mock OpenAI response with invalid JSON for TOC generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = (
            "Invalid JSON response that cannot be parsed"
        )
        return mock_response

    @pytest.fixture
    def ai_service_with_mock_client(self, mock_openai_client):
        """Create an AI service instance with mocked client."""
        service = AIService()
        service.client = mock_openai_client
        return service

    @pytest.mark.asyncio
    async def test_analyze_summary_for_toc_success(
        self, ai_service_with_mock_client, mock_openai_response
    ):
        """Test successful summary analysis for TOC readiness."""
        ai_service_with_mock_client.client.chat.completions.create = AsyncMock(
            return_value=mock_openai_response
        )

        summary = "This is a comprehensive book about web development with practical examples."
        book_metadata = {"title": "Web Dev Guide", "genre": "Technical"}

        result = await ai_service_with_mock_client.analyze_summary_for_toc(
            summary, book_metadata
        )

        assert result["is_ready_for_toc"] is True
        assert result["confidence_score"] == 0.8
        assert "clear structure" in result["analysis"]
        assert len(result["suggestions"]) <= 3

    @pytest.mark.asyncio
    async def test_analyze_summary_with_error(self, ai_service_with_mock_client):
        """Test summary analysis when API call fails."""
        ai_service_with_mock_client.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        summary = "Test summary"
        book_metadata = {"title": "Test Book"}

        result = await ai_service_with_mock_client.analyze_summary_for_toc(
            summary, book_metadata
        )

        assert result["is_ready_for_toc"] is False
        assert result["confidence_score"] == 0.0
        assert "error occurred" in result["analysis"].lower()

    @pytest.mark.asyncio
    async def test_generate_clarifying_questions_success(
        self, ai_service_with_mock_client, mock_questions_response
    ):
        """Test successful generation of clarifying questions."""
        ai_service_with_mock_client.client.chat.completions.create = AsyncMock(
            return_value=mock_questions_response
        )

        summary = "Book about programming fundamentals"
        book_metadata = {"title": "Programming 101", "genre": "Educational"}

        result = await ai_service_with_mock_client.generate_clarifying_questions(
            summary, book_metadata, 4
        )

        assert len(result) == 4
        assert all(question.endswith("?") for question in result)

    @pytest.mark.asyncio
    async def test_generate_questions_with_error_returns_fallback(
        self, ai_service_with_mock_client
    ):
        """Test fallback questions when API call fails."""
        ai_service_with_mock_client.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        summary = "Test summary"
        book_metadata = {"title": "Test Book"}

        result = await ai_service_with_mock_client.generate_clarifying_questions(
            summary, book_metadata, 3
        )

        assert len(result) == 4  # Default fallback count
        assert all(question.endswith("?") for question in result)

    @pytest.mark.asyncio
    async def test_generate_toc_from_summary_and_responses_success(
        self, ai_service_with_mock_client, mock_toc_response
    ):
        """Test successful TOC generation from summary and responses."""
        ai_service_with_mock_client.client.chat.completions.create = AsyncMock(
            return_value=mock_toc_response
        )

        summary = "This book teaches web development fundamentals"
        book_metadata = {"title": "Web Dev Guide", "genre": "Technical"}
        question_responses = [
            {"question": "Who is your target audience?", "answer": "Beginners"},
            {
                "question": "What should readers achieve?",
                "answer": "Practical projects",
            },
        ]

        result = (
            await ai_service_with_mock_client.generate_toc_from_summary_and_responses(
                summary, question_responses, book_metadata
            )
        )

        assert result is not None
        assert result["success"] == True
        assert "toc" in result
        assert result["toc"]["total_chapters"] == 2
        assert len(result["toc"]["chapters"]) == 2
        assert result["toc"]["chapters"][0]["title"] == "Getting Started"
        assert len(result["toc"]["chapters"][0]["subchapters"]) == 2

    @pytest.mark.asyncio
    async def test_generate_toc_from_summary_and_responses_invalid_json(
        self, ai_service_with_mock_client, mock_invalid_toc_response
    ):
        """Test TOC generation with invalid JSON response falls back to default structure."""
        ai_service_with_mock_client.client.chat.completions.create = AsyncMock(
            return_value=mock_invalid_toc_response
        )

        summary = "This book teaches web development"
        book_metadata = {"title": "Web Dev Guide", "genre": "Technical"}
        question_responses = [
            {"question": "Who is your audience?", "answer": "Beginners"},
            {"question": "What is the focus?", "answer": "Practical projects"},
        ]

        result = (
            await ai_service_with_mock_client.generate_toc_from_summary_and_responses(
                summary, question_responses, book_metadata
            )
        )

        # Should return fallback TOC
        assert result is not None
        assert result["success"] == True
        assert "toc" in result
        assert result["toc"]["total_chapters"] == 3  # Default fallback has 3 chapters
        assert result["toc"]["chapters"][0]["title"] == "Introduction"

    @pytest.mark.asyncio
    async def test_generate_toc_from_summary_and_responses_api_error(
        self, ai_service_with_mock_client
    ):
        """Test TOC generation when API call fails."""
        ai_service_with_mock_client.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        summary = "Test summary"
        book_metadata = {"title": "Test Book", "genre": "Technical"}
        question_responses = [
            {"question": "Question 1", "answer": "Answer 1"},
            {"question": "Question 2", "answer": "Answer 2"},
        ]

        with pytest.raises(Exception) as exc_info:
            await ai_service_with_mock_client.generate_toc_from_summary_and_responses(
                summary, question_responses, book_metadata
            )

        assert "Failed to generate TOC" in str(exc_info.value)

    def test_parse_analysis_response(self):
        """Test parsing of AI analysis response."""
        service = AIService()
        analysis_text = """
READINESS: Not Ready
CONFIDENCE: 0.3
ANALYSIS: The summary lacks specific details and structure. It needs more comprehensive content to generate a meaningful table of contents.
SUGGESTIONS: Add more concrete examples. Define target audience clearly. Include chapter outline.
"""
        summary = "This is a test summary with some content here."

        result = service._parse_analysis_response(analysis_text, summary)

        assert result["is_ready_for_toc"] is False
        assert result["confidence_score"] == 0.3
        assert "lacks specific details" in result["analysis"]
        assert len(result["suggestions"]) <= 3
        assert result["word_count"] == len(summary.split())
        assert result["character_count"] == len(summary)

    def test_parse_questions_response(self):
        """Test parsing of AI questions response."""
        service = AIService()
        questions_text = """
1. What is the main problem your book solves?
2. Who is your target audience?
3. What are the key topics you want to cover?
4. What should readers be able to do after reading?
"""
        result = service._parse_questions_response(questions_text)

        assert len(result) == 4
        assert all(question.endswith("?") for question in result)
        assert "main problem" in result[0].lower()
        assert "target audience" in result[1].lower()

    def test_parse_questions_response_with_fallback(self):
        """Test fallback when questions parsing fails."""
        service = AIService()
        # Invalid format that should trigger fallback (no question marks)
        questions_text = "This is not a proper questions format"

        result = service._parse_questions_response(questions_text)

        # Should return fallback questions
        assert len(result) == 4
        assert all(question.endswith("?") for question in result)

    def test_build_summary_analysis_prompt(self):
        """Test building of summary analysis prompt."""
        service = AIService()
        summary = "Test summary content"
        book_metadata = {
            "title": "Test Book",
            "genre": "How-to",
            "target_audience": "Beginners",
        }

        prompt = service._build_summary_analysis_prompt(summary, book_metadata)

        assert "Test Book" in prompt
        assert "How-to" in prompt
        assert "Beginners" in prompt
        assert summary in prompt
        assert "READINESS:" in prompt
        assert "CONFIDENCE:" in prompt

    def test_build_questions_prompt(self):
        """Test building of questions generation prompt."""
        service = AIService()
        summary = "Test summary content"
        book_metadata = {"title": "Test Book", "genre": "How-to"}
        num_questions = 4

        prompt = service._build_questions_prompt(summary, book_metadata, num_questions)

        assert "Test Book" in prompt
        assert "How-to" in prompt
        assert summary in prompt
        assert "4 clarifying questions" in prompt
        assert "numbered list" in prompt

    def test_build_toc_generation_prompt(self):
        """Test building of TOC generation prompt."""
        service = AIService()
        summary = "A comprehensive guide to modern web development"
        book_metadata = {
            "title": "Web Dev Mastery",
            "genre": "Technical",
            "target_audience": "Developers",
        }
        question_responses = [
            {
                "question": "Who is your target audience?",
                "answer": "Beginner to intermediate developers",
            },
            {
                "question": "What is the learning approach?",
                "answer": "Focus on practical, hands-on learning",
            },
            {
                "question": "What technologies to cover?",
                "answer": "JavaScript, React, Node.js, databases",
            },
        ]

        prompt = service._build_toc_generation_prompt(
            summary, question_responses, book_metadata
        )

        assert "Web Dev Mastery" in prompt
        assert "Technical" in prompt
        assert summary in prompt
        assert "Beginner to intermediate developers" in prompt
        assert "JavaScript, React, Node.js" in prompt
        assert "JSON" in prompt

    def test_parse_toc_response_valid_json(self):
        """Test parsing valid JSON TOC response."""
        service = AIService()
        valid_json_response = """
{
  "chapters": [
    {
      "id": "ch1",
      "title": "Chapter 1",
      "description": "First chapter",
      "level": 1,
      "order": 1,
      "subchapters": [
        {"id": "ch1-1", "title": "Section 1.1", "description": "First section", "level": 2, "order": 1},
        {"id": "ch1-2", "title": "Section 1.2", "description": "Second section", "level": 2, "order": 2}
      ]
    }
  ],
  "total_chapters": 1,
  "estimated_pages": 50
}
"""

        result = service._parse_toc_response(valid_json_response)

        assert result["success"] == True
        assert "toc" in result
        assert result["toc"]["total_chapters"] == 1
        assert len(result["toc"]["chapters"]) == 1
        assert result["toc"]["chapters"][0]["title"] == "Chapter 1"
        assert len(result["toc"]["chapters"][0]["subchapters"]) == 2

    def test_parse_toc_response_invalid_json(self):
        """Test parsing invalid JSON falls back to default structure."""
        service = AIService()
        invalid_response = "This is not valid JSON at all"

        result = service._parse_toc_response(invalid_response)

        assert result["success"] == True
        assert "toc" in result
        assert result["toc"]["total_chapters"] == 3
        assert result["toc"]["chapters"][0]["title"] == "Introduction"

    def test_parse_toc_response_missing_required_fields(self):
        """Test parsing JSON with missing required fields falls back."""
        service = AIService()
        incomplete_json = '{"title": "Test"}'  # Missing chapters

        result = service._parse_toc_response(incomplete_json)

        assert result["success"] == True
        assert "toc" in result
        assert result["toc"]["total_chapters"] == 3

    def test_create_fallback_toc(self):
        """Test creation of fallback TOC structure."""
        service = AIService()

        result = service._create_fallback_toc("Chapter 1\nChapter 2")

        assert result["success"] == True
        assert "toc" in result
        assert result["toc"]["total_chapters"] >= 2
        assert result["toc"]["chapters"][0]["title"] == "Introduction"

        # Check that each chapter has the proper structure
        for chapter in result["toc"]["chapters"]:
            assert "title" in chapter
            assert "id" in chapter
            assert "subchapters" in chapter
            assert isinstance(chapter["subchapters"], list)

    def test_singleton_instance(self):
        """Test that ai_service is properly configured as singleton."""
        assert ai_service is not None
        assert isinstance(ai_service, AIService)
        assert hasattr(ai_service, "client")
        assert ai_service.model == "gpt-4"
