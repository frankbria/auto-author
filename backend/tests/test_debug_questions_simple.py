"""Debug test for question schema validation"""

import pytest
from app.schemas.book import QuestionCreate, Question, QuestionType, QuestionDifficulty, QuestionMetadata
from datetime import datetime, timezone


def test_question_create_schema():
    """Test creating a QuestionCreate object"""
    metadata = QuestionMetadata(
        suggested_response_length="200-300 words",
        help_text="Test help",
        examples=["Example 1", "Example 2"]
    )
    
    question_create = QuestionCreate(
        book_id="test_book",
        chapter_id="test_chapter",
        question_text="What is the main theme of this chapter?",
        question_type=QuestionType.THEME,
        difficulty=QuestionDifficulty.MEDIUM,
        category="development",
        order=1,
        metadata=metadata
    )
    
    assert question_create.book_id == "test_book"
    assert question_create.chapter_id == "test_chapter"
    assert question_create.question_type == QuestionType.THEME
    assert question_create.difficulty == QuestionDifficulty.MEDIUM


def test_question_schema():
    """Test creating a Question object"""
    metadata = QuestionMetadata(
        suggested_response_length="200-300 words",
        help_text="Test help",
        examples=["Example 1", "Example 2"]
    )
    
    question = Question(
        id="test_id",
        book_id="test_book",
        chapter_id="test_chapter",
        question_text="What is the main theme of this chapter?",
        question_type=QuestionType.THEME,
        difficulty=QuestionDifficulty.MEDIUM,
        category="development",
        order=1,
        metadata=metadata,
        generated_at=datetime.now(timezone.utc)
    )
    
    assert question.id == "test_id"
    assert question.book_id == "test_book"
    assert question.chapter_id == "test_chapter"
    assert question.question_type == QuestionType.THEME


def test_question_from_dict():
    """Test creating a Question from a dictionary"""
    question_dict = {
        "id": "test_id",
        "book_id": "test_book",
        "chapter_id": "test_chapter",
        "question_text": "What is the main theme of this chapter?",
        "question_type": "theme",
        "difficulty": "medium",
        "category": "development",
        "order": 1,
        "metadata": {
            "suggested_response_length": "200-300 words",
            "help_text": "Test help",
            "examples": ["Example 1", "Example 2"]
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    
    question_from_dict = Question(**question_dict)
    
    assert question_from_dict.id == "test_id"
    assert question_from_dict.book_id == "test_book"
    assert question_from_dict.chapter_id == "test_chapter"
    assert question_from_dict.question_type == QuestionType.THEME
    assert question_from_dict.difficulty == QuestionDifficulty.MEDIUM