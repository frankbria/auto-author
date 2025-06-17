"""Debug test for question generation"""

import pytest
import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from app.services.question_generation_service import get_question_generation_service
from app.schemas.book import QuestionDifficulty
from app.db.database import get_collection


async def create_test_book():
    """Create a test book with TOC"""
    books_collection = await get_collection("books")
    
    book = {
        "_id": ObjectId(),
        "title": "Test Book for Questions",
        "owner_id": "test_user",
        "description": "Test description",
        "genre": "Non-Fiction",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "table_of_contents": {
            "chapters": [
                {
                    "id": "test_chapter_id",
                    "title": "Test Chapter",
                    "description": "Test chapter for question generation",
                    "order": 1,
                    "level": 1
                }
            ]
        }
    }
    
    await books_collection.insert_one(book)
    return str(book["_id"])


@pytest.mark.asyncio
async def test_question_generation_direct():
    """Test question generation directly without HTTP layer"""
    
    # Create test book
    book_id = await create_test_book()
    
    service = get_question_generation_service()
    
    try:
        result = await service.generate_questions_for_chapter(
            book_id=book_id,
            chapter_id="test_chapter_id",
            count=3,
            difficulty="medium",
            focus=None,
            user_id="test_user",
            current_user={"clerk_id": "test_user"}
        )
        
        print(f"Success! Generated {len(result.questions)} questions")
        print(f"Generation ID: {result.generation_id}")
        print(f"Questions: {[q.question_text for q in result.questions]}")
        
        # Verify questions were saved
        assert len(result.questions) == 3
        assert all(q.book_id == book_id for q in result.questions)
        assert all(q.chapter_id == "test_chapter_id" for q in result.questions)
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Cleanup
        books_collection = await get_collection("books")
        await books_collection.delete_one({"_id": ObjectId(book_id)})
        
        # Also cleanup questions
        questions_collection = await get_collection("questions")
        await questions_collection.delete_many({"book_id": book_id})


if __name__ == "__main__":
    asyncio.run(test_question_generation_direct())