# backend/app/db/questions.py

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
import logging
import math

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

logger = logging.getLogger(__name__)


def serialize_datetime(obj: Any) -> Any:
    """Convert datetime objects to ISO format strings for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetime(item) for item in obj]
    return obj


async def ensure_question_indexes() -> None:
    """
    Create database indexes for question collections.

    This function creates indexes for optimal query performance across:
    - questions collection: compound index on (book_id, chapter_id, user_id)
    - question_responses collection: compound index on (question_id, user_id)
    - question_ratings collection: compound index on (question_id, user_id)
    - questions collection: index on (user_id, created_at) for history queries

    All indexes are created idempotently (safe to run multiple times).
    MongoDB will skip creation if the index already exists.
    """
    logger.info("Creating indexes for question collections...")

    try:
        # Questions collection indexes
        questions_collection = await get_collection("questions")

        # Compound index for efficient chapter question queries
        # Used in: get_questions_for_chapter, get_chapter_question_progress, delete_questions_for_chapter
        await questions_collection.create_index(
            [("book_id", 1), ("chapter_id", 1), ("user_id", 1)],
            name="book_chapter_user_idx",
            background=True
        )
        logger.info("Created index: questions.book_chapter_user_idx")

        # Index for user question history (chronological order)
        # Useful for analytics and user activity tracking
        await questions_collection.create_index(
            [("user_id", 1), ("created_at", -1)],
            name="user_created_idx",
            background=True
        )
        logger.info("Created index: questions.user_created_idx")

        # Index for sorting by order within a chapter
        await questions_collection.create_index(
            [("book_id", 1), ("chapter_id", 1), ("order", 1)],
            name="chapter_order_idx",
            background=True
        )
        logger.info("Created index: questions.chapter_order_idx")

        # Question responses collection indexes
        responses_collection = await get_collection("question_responses")

        # Compound index for efficient response lookups
        # Used in: get_question_response, save_question_response
        await responses_collection.create_index(
            [("question_id", 1), ("user_id", 1)],
            name="question_user_idx",
            background=True,
            unique=True  # Each user can only have one response per question
        )
        logger.info("Created index: question_responses.question_user_idx")

        # Index for user response history
        await responses_collection.create_index(
            [("user_id", 1), ("created_at", -1)],
            name="user_created_idx",
            background=True
        )
        logger.info("Created index: question_responses.user_created_idx")

        # Question ratings collection indexes
        ratings_collection = await get_collection("question_ratings")

        # Compound index for efficient rating lookups
        # Used in: save_question_rating
        await ratings_collection.create_index(
            [("question_id", 1), ("user_id", 1)],
            name="question_user_idx",
            background=True,
            unique=True  # Each user can only have one rating per question
        )
        logger.info("Created index: question_ratings.question_user_idx")

        logger.info("All question collection indexes created successfully")

    except Exception as e:
        logger.error(f"Error creating question indexes: {e}", exc_info=True)
        # Don't raise - index creation failures shouldn't prevent app startup
        # Queries will still work, just potentially slower


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


async def create_questions_batch(
    questions_data: List[QuestionCreate],
    user_id: str
) -> List[Dict[str, Any]]:
    """
    Create multiple questions atomically using MongoDB's insert_many.

    Args:
        questions_data: List of QuestionCreate objects to insert
        user_id: User ID for all questions

    Returns:
        List of created question dictionaries with IDs

    Raises:
        Exception: If batch insertion fails, no questions will be saved
    """
    if not questions_data:
        return []

    questions_collection = await get_collection("questions")

    # Prepare all question documents
    now = datetime.now(timezone.utc)
    question_dicts = []

    for question_data in questions_data:
        question_dict = question_data.model_dump()
        question_dict.update({
            "_id": ObjectId(),
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
        })
        question_dicts.append(question_dict)

    try:
        # Atomic batch insertion - all or nothing
        result = await questions_collection.insert_many(
            question_dicts,
            ordered=True  # Stop on first error, ensures atomicity
        )

        # Convert ObjectIds to strings and prepare return data
        created_questions = []
        for i, inserted_id in enumerate(result.inserted_ids):
            question_dict = question_dicts[i].copy()
            question_dict["id"] = str(inserted_id)
            question_dict.pop("_id", None)
            # Serialize datetime objects to ISO format strings
            question_dict = serialize_datetime(question_dict)
            created_questions.append(question_dict)

        return created_questions

    except Exception as e:
        # Log the error with traceback and re-raise to ensure caller knows operation failed
        logger.exception(f"Failed to insert questions batch: {str(e)}")
        raise Exception(f"Failed to create questions batch: {str(e)}") from e


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

    # Calculate total pages
    pages = math.ceil(total / limit) if limit > 0 else 1
    has_more = page < pages

    return QuestionListResponse(
        questions=processed_questions,
        total=len(processed_questions),
        page=page,
        pages=pages,
        has_more=has_more
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


async def delete_questions_for_book(
    book_id: str,
    user_id: str
) -> int:
    """Delete all questions and responses for a book (cascade deletion)."""
    questions_collection = await get_collection("questions")
    responses_collection = await get_collection("question_responses")

    # Get all questions for the book
    questions = await questions_collection.find({
        "book_id": book_id,
        "user_id": user_id
    }).to_list(length=None)

    # Extract question IDs
    question_ids = [str(q["_id"]) for q in questions]

    # Delete all responses for these questions
    if question_ids:
        await responses_collection.delete_many({
            "question_id": {"$in": question_ids},
            "user_id": user_id
        })

    # Delete all questions for the book
    result = await questions_collection.delete_many({
        "book_id": book_id,
        "user_id": user_id
    })

    logger.info(f"Cascade delete: Removed {result.deleted_count} questions and their responses for book {book_id}")

    return result.deleted_count


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


async def save_question_responses_batch(
    responses: List[Dict[str, Any]],
    user_id: str
) -> Dict[str, Any]:
    """
    Save multiple question responses efficiently using MongoDB bulk write operations.

    Args:
        responses: List of dicts with keys: question_id, response_text, status
        user_id: User ID for ownership

    Returns:
        Dict with:
            - success: Overall success status
            - total: Total responses provided
            - saved: Number successfully saved
            - failed: Number that failed
            - results: List of per-response results with status and optional error
            - errors: List of error details for failed responses
    """
    responses_collection = await get_collection("question_responses")

    total = len(responses)
    results = []
    successful_ops = []
    failed_responses = []

    # Process each response and prepare bulk operations
    for idx, response_item in enumerate(responses):
        try:
            question_id = response_item.get("question_id")
            response_text = response_item.get("response_text", "")
            response_status = response_item.get("status", "draft")

            if not question_id:
                results.append({
                    "index": idx,
                    "question_id": None,
                    "success": False,
                    "error": "Missing question_id"
                })
                failed_responses.append({
                    "index": idx,
                    "error": "Missing question_id"
                })
                continue

            if not response_text:
                results.append({
                    "index": idx,
                    "question_id": question_id,
                    "success": False,
                    "error": "Missing response_text"
                })
                failed_responses.append({
                    "index": idx,
                    "question_id": question_id,
                    "error": "Missing response_text"
                })
                continue

            # Check if response already exists
            existing_response = await responses_collection.find_one({
                "question_id": question_id,
                "user_id": user_id
            })

            # Calculate word count
            word_count = len(response_text.split()) if response_text else 0

            # Prepare response data
            response_dict = {
                "question_id": question_id,
                "user_id": user_id,
                "response_text": response_text,
                "status": response_status,
                "word_count": word_count,
                "updated_at": datetime.now(timezone.utc),
                "last_edited_at": datetime.now(timezone.utc),
            }

            if existing_response:
                # Update existing response
                edit_history = existing_response.get("metadata", {}).get("edit_history", [])
                edit_history.append({
                    "timestamp": datetime.now(timezone.utc),
                    "word_count": existing_response.get("word_count", 0)
                })

                response_dict["metadata"] = {
                    "edit_history": edit_history
                }

                successful_ops.append({
                    "filter": {"_id": existing_response["_id"]},
                    "update": {"$set": response_dict},
                    "is_update": True,
                    "question_id": question_id,
                    "response_id": str(existing_response["_id"]),
                    "index": idx
                })
            else:
                # Create new response
                response_dict.update({
                    "_id": ObjectId(),
                    "created_at": datetime.now(timezone.utc),
                    "metadata": {"edit_history": []}
                })

                successful_ops.append({
                    "filter": None,
                    "insert": response_dict,
                    "is_update": False,
                    "question_id": question_id,
                    "response_id": str(response_dict["_id"]),
                    "index": idx
                })

        except Exception as e:
            results.append({
                "index": idx,
                "question_id": response_item.get("question_id"),
                "success": False,
                "error": str(e)
            })
            failed_responses.append({
                "index": idx,
                "question_id": response_item.get("question_id"),
                "error": str(e)
            })

    # Execute bulk operations
    saved_count = 0
    for op in successful_ops:
        try:
            if op.get("is_update"):
                await responses_collection.update_one(
                    op["filter"],
                    op["update"]
                )
            else:
                await responses_collection.insert_one(op["insert"])

            results.append({
                "index": op["index"],
                "question_id": op["question_id"],
                "response_id": op["response_id"],
                "success": True,
                "is_update": op["is_update"]
            })
            saved_count += 1
        except Exception as e:
            results.append({
                "index": op["index"],
                "question_id": op["question_id"],
                "success": False,
                "error": f"Database error: {str(e)}"
            })
            failed_responses.append({
                "index": op["index"],
                "question_id": op["question_id"],
                "error": f"Database error: {str(e)}"
            })

    return {
        "success": len(failed_responses) == 0,
        "total": total,
        "saved": saved_count,
        "failed": len(failed_responses),
        "results": results,
        "errors": failed_responses if failed_responses else None
    }
