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
async def test_generate_toc_structure(ai_service):
    """Test TOC generation"""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="""{
            "chapters": [
                {
                    "title": "Introduction",
                    "description": "Getting started",
                    "subchapters": []
                },
                {
                    "title": "Main Content",
                    "description": "Core concepts",
                    "subchapters": [
                        {
                            "title": "Subtopic 1",
                            "description": "Details"
                        }
                    ]
                }
            ],
            "total_chapters": 2,
            "estimated_pages": 100,
            "structure_notes": "Well organized"
        }"""))
    ]
    
    with patch.object(ai_service.client.chat.completions, 'create', 
                      AsyncMock(return_value=mock_response)):
        result = await ai_service.generate_toc_structure(
            book_description="A book about testing",
            genre="Technical",
            target_audience="Developers",
            additional_context={"writing_style": "Educational"}
        )
        
        assert result["success"] is True
        assert len(result["toc"]["chapters"]) == 2
        assert result["toc"]["chapters"][0]["title"] == "Introduction"
        assert len(result["toc"]["chapters"][1]["subchapters"]) == 1
        assert result["toc"]["total_chapters"] == 2


@pytest.mark.asyncio
async def test_generate_chapter_questions(ai_service):
    """Test chapter question generation"""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="""{
            "questions": [
                {
                    "id": "q1",
                    "question": "What is the main topic?",
                    "type": "open-ended",
                    "purpose": "context",
                    "follow_up_prompts": ["Can you elaborate?"],
                    "expected_length": "medium"
                },
                {
                    "id": "q2", 
                    "question": "Describe your experience",
                    "type": "narrative",
                    "purpose": "story",
                    "follow_up_prompts": ["What happened next?"],
                    "expected_length": "long"
                }
            ]
        }"""))
    ]
    
    with patch.object(ai_service.client.chat.completions, 'create',
                      AsyncMock(return_value=mock_response)):
        result = await ai_service.generate_chapter_questions(
            chapter_title="Introduction",
            chapter_description="Getting started with the topic",
            book_genre="Educational",
            target_audience="Students"
        )
        
        assert result["success"] is True
        assert len(result["questions"]) == 2
        assert result["questions"][0]["question"] == "What is the main topic?"
        assert result["questions"][0]["type"] == "open-ended"
        assert result["questions"][1]["type"] == "narrative"


@pytest.mark.asyncio
async def test_generate_chapter_draft(ai_service):
    """Test chapter draft generation"""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="""# Introduction to Testing

Testing is a crucial part of software development. It ensures that your code works as expected and helps catch bugs early.

## Why Testing Matters

Quality software requires thorough testing. Here are the key benefits:

1. **Early Bug Detection**: Find issues before they reach production
2. **Code Confidence**: Make changes without fear of breaking things
3. **Documentation**: Tests serve as living documentation

## Types of Tests

There are several types of tests you should know about...
"""))
    ]
    
    with patch.object(ai_service.client.chat.completions, 'create',
                      AsyncMock(return_value=mock_response)):
        result = await ai_service.generate_chapter_draft(
            chapter_title="Introduction to Testing",
            chapter_description="Learn testing basics",
            question_responses=[
                {
                    "question": "What is the main purpose?",
                    "answer": "To teach developers about testing"
                },
                {
                    "question": "What should readers learn?",
                    "answer": "Different types of tests and when to use them"
                }
            ],
            writing_style="educational",
            target_length=2000
        )
        
        assert result["success"] is True
        assert "Introduction to Testing" in result["draft"]
        assert "Why Testing Matters" in result["draft"]
        assert result["metadata"]["word_count"] > 0
        assert result["metadata"]["writing_style"] == "educational"


@pytest.mark.asyncio
async def test_validate_content(ai_service):
    """Test content validation"""
    # Test appropriate content
    appropriate_result = await ai_service.validate_content(
        "This is a clean, educational text about programming."
    )
    assert appropriate_result["is_appropriate"] is True
    assert appropriate_result["confidence"] > 0.8
    
    # Test with mock for inappropriate content
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="""{
            "is_appropriate": false,
            "confidence": 0.95,
            "reason": "Contains inappropriate language",
            "suggestions": ["Remove offensive terms", "Use professional language"]
        }"""))
    ]
    
    with patch.object(ai_service.client.chat.completions, 'create',
                      AsyncMock(return_value=mock_response)):
        inappropriate_result = await ai_service.validate_content(
            "Some inappropriate content here"
        )
        assert inappropriate_result["is_appropriate"] is False
        assert len(inappropriate_result["suggestions"]) > 0


@pytest.mark.asyncio
async def test_summarize_chapter(ai_service):
    """Test chapter summarization"""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="""{
            "summary": "This chapter introduces the basics of unit testing in Python using pytest framework.",
            "key_points": [
                "Setting up pytest",
                "Writing your first test",
                "Test fixtures and parametrization"
            ],
            "word_count": 15,
            "themes": ["testing", "python", "quality assurance"]
        }"""))
    ]
    
    with patch.object(ai_service.client.chat.completions, 'create',
                      AsyncMock(return_value=mock_response)):
        result = await ai_service.summarize_chapter(
            "Long chapter content about testing..." * 100
        )
        
        assert "summary" in result
        assert len(result["key_points"]) == 3
        assert "testing" in result["themes"]
        assert result["word_count"] > 0


@pytest.mark.asyncio
async def test_ai_service_error_handling(ai_service):
    """Test error handling in AI service"""
    # Test API error
    with patch.object(ai_service.client.chat.completions, 'create',
                      AsyncMock(side_effect=Exception("API Error"))):
        result = await ai_service.generate_toc_structure(
            "Test book", "Fiction", "General"
        )
        assert result["success"] is False
        assert "error" in result
        
    # Test JSON parsing error
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Invalid JSON"))
    ]
    
    with patch.object(ai_service.client.chat.completions, 'create',
                      AsyncMock(return_value=mock_response)):
        result = await ai_service.generate_toc_structure(
            "Test book", "Fiction", "General"
        )
        assert result["success"] is False


@pytest.mark.asyncio
async def test_enhance_question(ai_service):
    """Test question enhancement"""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="""{
            "enhanced_question": "Can you describe a specific moment when you first realized your passion for writing? What were you doing, and how did it make you feel?",
            "follow_up_prompts": [
                "What triggered that moment?",
                "How did others react?",
                "What changed after that?"
            ],
            "question_type": "narrative",
            "improvements": ["Added sensory details", "Made more specific", "Included emotional component"]
        }"""))
    ]
    
    with patch.object(ai_service.client.chat.completions, 'create',
                      AsyncMock(return_value=mock_response)):
        result = await ai_service.enhance_question(
            "When did you start writing?",
            "personal_story"
        )
        
        assert len(result["enhanced_question"]) > len("When did you start writing?")
        assert len(result["follow_up_prompts"]) > 0
        assert result["question_type"] == "narrative"