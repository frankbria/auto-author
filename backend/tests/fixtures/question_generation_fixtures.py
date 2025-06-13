"""
Test fixtures for the question generation feature.

This module provides fixtures and sample data for testing the interview-style
question generation functionality.
"""

from datetime import datetime, timezone
import uuid

# Sample questions for testing
SAMPLE_QUESTIONS = [
    {
        "id": str(uuid.uuid4()),
        "chapter_id": "chapter-123",
        "question_text": "Who is the main character of this chapter and what are their key traits?",
        "question_type": "character",
        "difficulty": "medium",
        "category": "development",
        "order": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "help_text": "Consider physical traits, psychological aspects, backstory, and character development.",
            "examples": ["The protagonist shows determination through her decision to confront her fear"],
            "suggested_response_length": "200-300 words"
        },
        "response_status": "not_started"
    },
    {
        "id": str(uuid.uuid4()),
        "chapter_id": "chapter-123",
        "question_text": "What is the main conflict or challenge in this chapter?",
        "question_type": "plot",
        "difficulty": "medium",
        "category": "development",
        "order": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "help_text": "Focus on the sequence of events, cause and effect, conflicts, and resolution.",
            "examples": ["The discovery of the map sets in motion a chain of events that leads to..."],
            "suggested_response_length": "200-300 words"
        },
        "response_status": "not_started"
    },
    {
        "id": str(uuid.uuid4()),
        "chapter_id": "chapter-123",
        "question_text": "How does the setting contribute to the mood and atmosphere of this chapter?",
        "question_type": "setting",
        "difficulty": "easy",
        "category": "development",
        "order": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "help_text": "Include time, place, atmosphere, and how the setting affects the story.",
            "examples": ["The dark, narrow alleyways create a sense of claustrophobia that mirrors the character's mental state"],
            "suggested_response_length": "100-200 words"
        },
        "response_status": "not_started"
    },
    {
        "id": str(uuid.uuid4()),
        "chapter_id": "chapter-123",
        "question_text": "What themes or messages are explored in this chapter?",
        "question_type": "theme",
        "difficulty": "hard",
        "category": "development",
        "order": 4,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "help_text": "Think about underlying messages, symbols, and deeper meaning.",
            "examples": ["The recurring image of birds represents freedom and the character's desire to escape"],
            "suggested_response_length": "300-500 words"
        },
        "response_status": "not_started"
    },
    {
        "id": str(uuid.uuid4()),
        "chapter_id": "chapter-123",
        "question_text": "What research might be needed to make this chapter more authentic?",
        "question_type": "research",
        "difficulty": "medium",
        "category": "development",
        "order": 5,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "help_text": "Consider what facts, terminology, or technical details need verification.",
            "examples": ["The medical procedure described would require research on current surgical practices"],
            "suggested_response_length": "200-300 words"
        },
        "response_status": "not_started"
    }
]

# Sample responses for testing
SAMPLE_RESPONSES = [
    {
        "id": str(uuid.uuid4()),
        "question_id": SAMPLE_QUESTIONS[0]["id"],
        "user_id": "user-456",
        "response_text": "The main character of this chapter is Sarah, a determined archaeologist in her mid-30s. Her key traits are her attention to detail, stubborn persistence, and skepticism toward unfounded theories. She has spent the last decade proving herself in a male-dominated field, which has made her somewhat defensive but also extremely thorough in her work. Physically, she's practical rather than fashionable, often seen with her hair pulled back and wearing field clothes even in academic settings, which speaks to her prioritization of function over appearance and her constant readiness to get back to a dig site.",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_edited_at": datetime.now(timezone.utc).isoformat(),
        "word_count": 103,
        "status": "completed",
        "metadata": {
            "edit_history": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "word_count": 103
                }
            ]
        }
    },
    {
        "id": str(uuid.uuid4()),
        "question_id": SAMPLE_QUESTIONS[1]["id"],
        "user_id": "user-456",
        "response_text": "The main conflict in this chapter is Sarah's discovery of an artifact that contradicts the established timeline for the ancient civilization she's studying. This puts her in direct opposition with her mentor, Professor Jenkins, who has built his reputation on the current understanding of this civilization's development. Sarah must decide whether to present her findings, potentially damaging her mentor's career and her own professional relationships, or to suppress the discovery to maintain the status quo. The conflict is both external (professional disagreement) and internal (her values of truth versus loyalty).",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_edited_at": datetime.now(timezone.utc).isoformat(),
        "word_count": 98,
        "status": "draft",
        "metadata": {
            "edit_history": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "word_count": 98
                }
            ]
        }
    }
]

# Sample question ratings for testing
SAMPLE_RATINGS = [
    {
        "id": str(uuid.uuid4()),
        "question_id": SAMPLE_QUESTIONS[0]["id"],
        "user_id": "user-456",
        "rating": 5,
        "feedback": "This question was very helpful in developing my character!",
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "question_id": SAMPLE_QUESTIONS[1]["id"],
        "user_id": "user-456",
        "rating": 4,
        "feedback": "Good question, but a bit too general.",
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "question_id": SAMPLE_QUESTIONS[2]["id"],
        "user_id": "user-456",
        "rating": 3,
        "feedback": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
]

# Sample book for testing
SAMPLE_BOOK = {
    "_id": "book-789",
    "title": "The Lost Artifact",
    "owner_id": "user-456",
    "genre": "historical fiction",
    "target_audience": "adult",
    "summary": "An archaeologist discovers an artifact that challenges everything we know about ancient civilizations.",
    "table_of_contents": {
        "chapters": [
            {
                "id": "chapter-123",
                "title": "The Discovery",
                "description": "Sarah uncovers a mysterious artifact in the ruins.",
                "level": 1,
                "order": 1,
                "status": "in-progress",
                "word_count": 2500,
                "last_modified": datetime.now(timezone.utc).isoformat(),
                "subchapters": []
            },
            {
                "id": "chapter-456",
                "title": "The Confrontation",
                "description": "Sarah confronts her mentor about the artifact.",
                "level": 1,
                "order": 2,
                "status": "draft",
                "word_count": 1200,
                "last_modified": datetime.now(timezone.utc).isoformat(),
                "subchapters": []
            }
        ]
    }
}

# Mock AI service response for question generation
MOCK_AI_RESPONSE = [
    {
        "question_text": "Who is the main character of this chapter and what are their key traits?",
        "question_type": "character",
        "difficulty": "medium",
        "help_text": "Consider physical traits, psychological aspects, backstory, and character development.",
        "examples": ["The protagonist shows determination through her decision to confront her fear"]
    },
    {
        "question_text": "What is the main conflict or challenge in this chapter?",
        "question_type": "plot",
        "difficulty": "medium",
        "help_text": "Focus on the sequence of events, cause and effect, conflicts, and resolution.",
        "examples": ["The discovery of the map sets in motion a chain of events that leads to..."]
    },
    {
        "question_text": "How does the setting contribute to the mood and atmosphere of this chapter?",
        "question_type": "setting",
        "difficulty": "easy",
        "help_text": "Include time, place, atmosphere, and how the setting affects the story.",
        "examples": ["The dark, narrow alleyways create a sense of claustrophobia that mirrors the character's mental state"]
    },
    {
        "question_text": "What themes or messages are explored in this chapter?",
        "question_type": "theme",
        "difficulty": "hard",
        "help_text": "Think about underlying messages, symbols, and deeper meaning.",
        "examples": ["The recurring image of birds represents freedom and the character's desire to escape"]
    },
    {
        "question_text": "What research might be needed to make this chapter more authentic?",
        "question_type": "research",
        "difficulty": "medium",
        "help_text": "Consider what facts, terminology, or technical details need verification.",
        "examples": ["The medical procedure described would require research on current surgical practices"]
    }
]

# Mock progress response
MOCK_PROGRESS_RESPONSE = {
    "total": 5,
    "completed": 1,
    "in_progress": 1,
    "progress": 0.2,
    "status": "in-progress"
}

# Helper function to generate test question data
def generate_test_questions(chapter_id, count=5):
    """Generate a list of test questions for a specific chapter."""
    questions = []
    for i in range(count):
        question_type = ["character", "plot", "setting", "theme", "research"][i % 5]
        difficulty = ["easy", "medium", "hard"][i % 3]
        
        question = {
            "id": str(uuid.uuid4()),
            "chapter_id": chapter_id,
            "question_text": f"Test question {i+1} for chapter {chapter_id}",
            "question_type": question_type,
            "difficulty": difficulty,
            "category": "development",
            "order": i + 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "help_text": f"Help text for question {i+1}",
                "examples": [f"Example for question {i+1}"],
                "suggested_response_length": "200-300 words"
            },
            "response_status": "not_started"
        }
        questions.append(question)
    
    return questions

# Helper function to generate a response
def generate_test_response(question_id, user_id, status="completed"):
    """Generate a test response for a specific question."""
    response_text = "This is a test response for question " + question_id
    
    return {
        "id": str(uuid.uuid4()),
        "question_id": question_id,
        "user_id": user_id,
        "response_text": response_text,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_edited_at": datetime.now(timezone.utc).isoformat(),
        "word_count": len(response_text.split()),
        "status": status,
        "metadata": {
            "edit_history": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "word_count": len(response_text.split())
                }
            ]
        }
    }

# Export the fixtures with the expected names
sample_questions = SAMPLE_QUESTIONS
sample_question_responses = SAMPLE_RESPONSES
sample_question_ratings = SAMPLE_RATINGS
book_with_questions = SAMPLE_BOOK
ai_question_response = {
    "questions": MOCK_AI_RESPONSE,
    "generation_metadata": {
        "ai_model": "gpt-4",
        "parameters": {
            "temperature": 0.7,
            "max_tokens": 2000
        },
        "processing_time": 2.5
    }
}
