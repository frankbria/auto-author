# backend/app/db/questions.py

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId

from .base import get_collection
from app.schemas.book import (
    Question,
    QuestionCreate,
    QuestionResponse,
    QuestionResponseCreate,
    QuestionRating,
    QuestionListResponse,
    QuestionProgressResponse,
)


async def create_question(question_data: QuestionCreate, user_id: str) -> Dict[str, Any]:
    """Create a new question in the database."""
    questions_collection = await get_collection("questions")
    
    # Convert to dict and add metadata
    question_dict = question_data.model_dump()
    question_dict.update({
        "_id": ObjectId(),
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    
    # Insert the question
    result = await questions_collection.insert_one(question_dict)
    
    # Return the created question with string ID
    question_dict["id"] = str(result.inserted_id)
    question_dict.pop("_id", None)
    
    return question_dict


async def get_questions_for_chapter(
    book_id: str,
    chapter_id: str,
    user_id: str,
    status: Optional[str] = None,
    category: Optional[str] = None,
    question_type: Optional[str] = None,
    page: int = 1,
    limit: int = 10
) -> QuestionListResponse:
    """Get questions for a specific chapter with optional filtering."""
    questions_collection = await get_collection("questions")
    
    # Build query
    query = {
        "book_id": book_id,
        "chapter_id": chapter_id,
        "user_id": user_id
    }
    
    if category:
        query["category"] = category
    if question_type:
        query["question_type"] = question_type
    
    # Calculate pagination
    skip = (page - 1) * limit
    
    # Get questions with pagination
    cursor = questions_collection.find(query).sort("order", 1).skip(skip).limit(limit)
    questions = await cursor.to_list(length=limit)
    
    # Get total count
    total = await questions_collection.count_documents(query)
    
    # Convert ObjectIds to strings and add response status
    processed_questions = []
    for question in questions:
        question["id"] = str(question.pop("_id"))
        
        # Check if question has a response
        responses_collection = await get_collection("question_responses")
        response = await responses_collection.find_one({
            "question_id": question["id"],
            "user_id": user_id
        })
        
        if response:
            question["response_status"] = response.get("status", "draft")
            question["has_response"] = True
        else:
            question["response_status"] = "not_answered"
            question["has_response"] = False
        
        processed_questions.append(question)
    
    # Apply status filter after getting response status
    if status:
        if status == "completed":
            processed_questions = [q for q in processed_questions if q["response_status"] == "completed"]
        elif status == "draft":
            processed_questions = [q for q in processed_questions if q["response_status"] == "draft"]
        elif status == "not_answered":
            processed_questions = [q for q in processed_questions if q["response_status"] == "not_answered"]
    
    return QuestionListResponse(
        questions=processed_questions,
        total=len(processed_questions),
        page=page,
        limit=limit,
        has_more=(page * limit) < total
    )


async def save_question_response(
    question_id: str,
    response_data: QuestionResponseCreate,
    user_id: str
) -> Dict[str, Any]:
    """Save or update a question response."""
    responses_collection = await get_collection("question_responses")
    
    # Check if response already exists
    existing_response = await responses_collection.find_one({
        "question_id": question_id,
        "user_id": user_id
    })
    
    # Calculate word count
    word_count = len(response_data.response_text.split()) if response_data.response_text else 0
    
    # Prepare response data
    response_dict = response_data.model_dump()
    response_dict.update({
        "question_id": question_id,
        "user_id": user_id,
        "word_count": word_count,
        "updated_at": datetime.now(timezone.utc),
        "last_edited_at": datetime.now(timezone.utc),
    })
    
    if existing_response:
        # Update existing response
        # Add to edit history
        edit_history = existing_response.get("metadata", {}).get("edit_history", [])
        edit_history.append({
            "timestamp": datetime.now(timezone.utc),
            "word_count": existing_response.get("word_count", 0)
        })
        
        response_dict["metadata"] = response_dict.get("metadata", {})
        response_dict["metadata"]["edit_history"] = edit_history
        
        await responses_collection.update_one(
            {"_id": existing_response["_id"]},
            {"$set": response_dict}
        )
        
        response_dict["id"] = str(existing_response["_id"])
        return response_dict
    else:
        # Create new response
        response_dict.update({
            "_id": ObjectId(),
            "created_at": datetime.now(timezone.utc),
            "metadata": {"edit_history": []}
        })
        
        result = await responses_collection.insert_one(response_dict)
        response_dict["id"] = str(result.inserted_id)
        response_dict.pop("_id", None)
        
        return response_dict


async def get_question_response(question_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a question response."""
    responses_collection = await get_collection("question_responses")
    
    response = await responses_collection.find_one({
        "question_id": question_id,
        "user_id": user_id
    })
    
    if response:
        response["id"] = str(response.pop("_id"))
        return response
    
    return None


async def save_question_rating(
    question_id: str,
    rating_data: QuestionRating,
    user_id: str
) -> Dict[str, Any]:
    """Save or update a question rating."""
    ratings_collection = await get_collection("question_ratings")
    
    # Check if rating already exists
    existing_rating = await ratings_collection.find_one({
        "question_id": question_id,
        "user_id": user_id
    })
    
    # Prepare rating data
    rating_dict = rating_data.model_dump()
    rating_dict.update({
        "question_id": question_id,
        "user_id": user_id,
        "updated_at": datetime.now(timezone.utc),
    })
    
    if existing_rating:
        # Update existing rating
        await ratings_collection.update_one(
            {"_id": existing_rating["_id"]},
            {"$set": rating_dict}
        )
        
        rating_dict["id"] = str(existing_rating["_id"])
        return rating_dict
    else:
        # Create new rating
        rating_dict.update({
            "_id": ObjectId(),
            "created_at": datetime.now(timezone.utc),
        })
        
        result = await ratings_collection.insert_one(rating_dict)
        rating_dict["id"] = str(result.inserted_id)
        rating_dict.pop("_id", None)
        
        return rating_dict


async def get_chapter_question_progress(
    book_id: str, 
    chapter_id: str, 
    user_id: str
) -> QuestionProgressResponse:
    """Get question progress for a chapter."""
    questions_collection = await get_collection("questions")
    responses_collection = await get_collection("question_responses")
    
    # Get all questions for the chapter
    questions = await questions_collection.find({
        "book_id": book_id,
        "chapter_id": chapter_id,
        "user_id": user_id
    }).to_list(length=None)
    
    total = len(questions)
    completed = 0
    in_progress = 0
    
    # Check response status for each question
    for question in questions:
        question_id = str(question["_id"])
        response = await responses_collection.find_one({
            "question_id": question_id,
            "user_id": user_id
        })
        
        if response:
            if response.get("status") == "completed":
                completed += 1
            else:
                in_progress += 1
    
    # Calculate progress
    progress = float(completed) / total if total > 0 else 0.0
    
    # Determine status
    if completed == total and total > 0:
        status = "completed"
    elif completed > 0 or in_progress > 0:
        status = "in-progress"
    else:
        status = "not-started"
    
    return QuestionProgressResponse(
        total=total,
        completed=completed,
        in_progress=in_progress,
        progress=progress,
        status=status
    )


async def delete_questions_for_chapter(
    book_id: str,
    chapter_id: str,
    user_id: str,
    preserve_with_responses: bool = True
) -> int:
    """Delete questions for a chapter, optionally preserving those with responses."""
    questions_collection = await get_collection("questions")
    responses_collection = await get_collection("question_responses")
    
    # Get all questions for the chapter
    questions = await questions_collection.find({
        "book_id": book_id,
        "chapter_id": chapter_id,
        "user_id": user_id
    }).to_list(length=None)
    
    deleted_count = 0
    
    for question in questions:
        question_id = str(question["_id"])
        
        # Check if question has responses
        has_response = await responses_collection.find_one({
            "question_id": question_id,
            "user_id": user_id
        })
        
        # Delete if no response or not preserving responses
        if not has_response or not preserve_with_responses:
            await questions_collection.delete_one({"_id": question["_id"]})
            
            # Also delete any responses
            await responses_collection.delete_many({
                "question_id": question_id,
                "user_id": user_id
            })
            
            deleted_count += 1
    
    return deleted_count


async def get_question_by_id(question_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a question by ID."""
    questions_collection = await get_collection("questions")
    
    try:
        object_id = ObjectId(question_id)
    except:
        return None
    
    question = await questions_collection.find_one({
        "_id": object_id,
        "user_id": user_id
    })
    
    if question:
        question["id"] = str(question.pop("_id"))
        return question
    
    return None
