"""Test core AI service functionality"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ai_service import AIService
from app.core.config import settings


@pytest.fixture
def ai_service():
    """Create AI service instance"""
    return AIService()


@pytest.mark.asyncio
async def test_analyze_summary_for_toc(ai_service):
    """Test summary analysis for TOC generation"""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="""
READINESS: Ready
CONFIDENCE: 0.9
ANALYSIS: The summary provides clear structure and main topics for a technical book.
SUGGESTIONS: Consider adding more specific examples for each chapter.
        """))
    ]

    with patch.object(ai_service, '_make_openai_request',
                      AsyncMock(return_value=mock_response)):
        result = await ai_service.analyze_summary_for_toc(
            summary="A comprehensive guide to Python programming",
            book_metadata={
                "title": "Python Mastery",
                "genre": "Technical",
                "target_audience": "Developers"
            }
        )

        assert result["is_ready_for_toc"] == True
        assert result["confidence_score"] == 0.9
        assert "clear structure" in result["analysis"]


@pytest.mark.asyncio
async def test_generate_clarifying_questions(ai_service):
    """Test clarifying questions generation"""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="""
1. What specific Python topics will you focus on?
2. Will you include practical examples and exercises?
3. What makes your book different from other Python books?
4. How deep will you go into advanced topics?
        """))
    ]

    with patch.object(ai_service, '_make_openai_request',
                      AsyncMock(return_value=mock_response)):
        questions = await ai_service.generate_clarifying_questions(
            summary="A book about Python programming",
            book_metadata={
                "genre": "Technical",
                "target_audience": "Beginners"
            }
        )

        assert len(questions) == 4
        assert "Python topics" in questions[0]
        assert "practical examples" in questions[1]


@pytest.mark.asyncio
async def test_generate_toc_from_summary_and_responses(ai_service):
    """Test TOC generation from summary and responses"""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="""{
    "table_of_contents": {
        "chapters": [
            {
                "id": "ch1",
                "title": "Introduction to Python",
                "description": "Getting started with Python",
                "order": 1,
                "level": 1,
                "parent_id": null,
                "subchapters": []
            },
            {
                "id": "ch2",
                "title": "Python Basics",
                "description": "Core concepts",
                "order": 2,
                "level": 1,
                "parent_id": null,
                "subchapters": [
                    {
                        "id": "ch2.1",
                        "title": "Variables and Data Types",
                        "description": "Understanding Python data types",
                        "order": 1,
                        "level": 2,
                        "parent_id": "ch2"
                    }
                ]
            }
        ],
        "total_chapters": 2,
        "estimated_pages": 150,
        "structure_notes": "Well-organized progression from basics to advanced"
    }
}"""))
    ]

    with patch.object(ai_service, '_make_openai_request',
                      AsyncMock(return_value=mock_response)):
        result = await ai_service.generate_toc_from_summary_and_responses(
            summary="A comprehensive Python guide",
            question_responses=[
                {"question": "What topics?", "answer": "Basics to advanced"},
                {"question": "Examples?", "answer": "Yes, many practical examples"}
            ],
            book_metadata={
                "title": "Python Mastery",
                "genre": "Technical"
            }
        )

        assert "toc" in result
        assert len(result["toc"]["chapters"]) >= 2
        assert result["toc"]["total_chapters"] >= 2
        assert "success" in result
        assert result["success"] == True


@pytest.mark.asyncio
async def test_generate_chapter_questions(ai_service):
    """Test chapter questions generation"""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="""{
    "questions": [
        {
            "id": "q1",
            "question_text": "What are the main character's motivations?",
            "question_type": "character",
            "difficulty": "medium",
            "category": "Character Development",
            "metadata": {
                "suggested_response_length": "200-300 words",
                "help_text": "Think about what drives the character",
                "examples": ["desire for revenge", "search for identity"]
            }
        },
        {
            "id": "q2",
            "question_text": "Describe the setting of this chapter",
            "question_type": "setting",
            "difficulty": "easy",
            "category": "World Building",
            "metadata": {
                "suggested_response_length": "150-200 words",
                "help_text": "Consider time, place, and atmosphere"
            }
        }
    ]
}"""))
    ]

    with patch.object(ai_service, '_make_openai_request',
                      AsyncMock(return_value=mock_response)):
        # Build prompt from chapter data
        prompt = f"Generate questions for chapter: The Beginning - Introduction to the story"
        result = await ai_service.generate_chapter_questions(
            prompt=prompt,
            count=2
        )

        # The method returns a list directly, not a dict with questions key
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["question_type"] == "character"
        assert result[1]["question_type"] == "setting"


@pytest.mark.asyncio
async def test_generate_chapter_draft(ai_service):
    """Test chapter draft generation"""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="""
# The Beginning

It was a dark and stormy night when Sarah first discovered her powers. The rain pelted against the windows of the old Victorian house, creating an eerie rhythm that seemed to match her racing heartbeat.

She had always known she was different, but tonight everything would change...
        """))
    ]

    with patch.object(ai_service, '_make_openai_request',
                      AsyncMock(return_value=mock_response)):
        result = await ai_service.generate_chapter_draft(
            chapter_title="The Beginning",
            chapter_description="Sarah discovers her powers",
            question_responses=[
                {
                    "question": "What are the main character's motivations?",
                    "answer": "Sarah wants to understand her newfound abilities"
                },
                {
                    "question": "Describe the setting",
                    "answer": "A stormy night in an old Victorian house"
                }
            ],
            book_metadata={
                "genre": "Fantasy",
                "target_audience": "Young Adults"
            },
            writing_style="Descriptive and atmospheric"
        )

        assert result["success"] == True
        assert "draft" in result
        assert "Sarah" in result["draft"]
        assert "powers" in result["draft"]
        assert result["metadata"]["word_count"] > 0


@pytest.mark.asyncio
async def test_ai_service_error_handling(ai_service):
    """Test error handling in AI service"""
    from app.services.ai_errors import AIServiceError

    # Test that AIServiceError is raised on API error
    with patch.object(ai_service, '_make_openai_request',
                      AsyncMock(side_effect=Exception("API Error"))):
        # Should raise AIServiceError
        with pytest.raises(AIServiceError) as exc_info:
            await ai_service.generate_clarifying_questions(
                summary="Test summary",
                book_metadata={}
            )

        # Verify error details
        assert exc_info.value.error_code == "AI_UNEXPECTED_ERROR"
        assert exc_info.value.correlation_id is not None


@pytest.mark.asyncio
async def test_parse_questions_response(ai_service):
    """Test question parsing from AI response"""
    # Test the internal parsing method
    questions_text = """
1. What is the main theme of your book?
2. Who are your target readers?
3. What unique perspective do you bring?
4. How will readers benefit from your book?
    """

    questions = ai_service._parse_questions_response(questions_text)

    assert len(questions) == 4
    assert "main theme" in questions[0]
    assert "target readers" in questions[1]
    assert "unique perspective" in questions[2]
    assert "readers benefit" in questions[3]
