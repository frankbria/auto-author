"""Debug test for chapter question generation"""

import pytest
import asyncio
from datetime import datetime, timezone
from bson import ObjectId

from app.services.question_generation_service import get_question_generation_service
from app.db import base  # Use fixture-managed collections
from app.schemas.book import QuestionDifficulty


async def create_test_book():
    """Create a test book with TOC"""
    books_collection = base.books_collection  # Use fixture-managed collection
    
    book = {
        "_id": ObjectId(),
        "title": "Test Book",
        "owner_id": "test_user",
        "description": "Test description",
        "table_of_contents": {
            "chapters": [
                {
                    "id": "ch1",
                    "title": "Chapter 1",
                    "description": "First chapter",
                    "order": 1,
                    "level": 1
                }
            ]
        }
    }
    
    await books_collection.insert_one(book)
    return str(book["_id"])


@pytest.mark.asyncio
async def test_chapter_question_generation(motor_reinit_db):  # Use correct fixture name
    """Test chapter question generation directly"""
    
    # Create test book
    book_id = await create_test_book()
    
    service = get_question_generation_service()
    
    try:
        print(f"Testing question generation for book {book_id}, chapter ch1")
        
        result = await service.generate_questions_for_chapter(
            book_id=book_id,
            chapter_id="ch1",
            count=3,
            difficulty="medium",
            focus=None,
            user_id="test_user",
            current_user={"clerk_id": "test_user"}
        )
        
        print(f"✅ Success! Generated {len(result.questions)} questions")
        print(f"Generation ID: {result.generation_id}")
        for i, q in enumerate(result.questions):
            print(f"Question {i+1}: {q.question_text}")
            print(f"  Type: {q.question_type}, Difficulty: {q.difficulty}")
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        # Cleanup
        books_collection = base.books_collection  # Use fixture-managed collection
        await books_collection.delete_one({"_id": ObjectId(book_id)})
        print(f"Cleaned up test book {book_id}")


if __name__ == "__main__":
    asyncio.run(test_chapter_question_generation())