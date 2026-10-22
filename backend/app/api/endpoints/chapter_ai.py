"""
Chapter AI endpoints: draft generation, style transformation, text enhancement
and transcription cleanup.

Extracted verbatim from ``books.py`` (issue #1123). Behavior-preserving move:
routes are mounted under the same ``/books`` prefix in ``router.py``.
"""
import logging
from typing import Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from app.api.dependencies import (
    audit_after_commit, get_rate_limiter, get_ai_usage_quota,
    get_entitlement_checker
)
from app.core.security import get_current_user_from_session
from app.db.database import get_book_metadata_by_id, get_book_owner_id
from app.schemas.ai_input import (
    EnhanceTextRequest,
    EnhanceTranscriptionRequest,
    GenerateDraftRequest,
    TransformStyleRequest,
)
from app.services.ai_errors import AIServiceError
from app.services.ai_service import ai_service
from app.services.content_enhancement import (
    available_enhancements,
    is_valid_enhancement,
)
from app.services.style_templates import available_styles, is_valid_style
from app.utils.error_handlers import ai_error_http_exception

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{book_id}/chapters/{chapter_id}/generate-draft", response_model=dict, dependencies=[Depends(get_ai_usage_quota()), Depends(get_entitlement_checker("generate_draft"))])
async def generate_chapter_draft(
    book_id: str,
    chapter_id: str,
    data: GenerateDraftRequest = Body(default=GenerateDraftRequest()),
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(
        get_rate_limiter(limit=5, window=3600)
    ),  # 5 per hour
):
    """
    Generate a draft chapter based on Q&A responses using AI.
    This transforms interview-style responses into narrative content.
    """
    # Get the book and verify ownership
    book = await get_book_metadata_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to generate draft for this book"
        )

    # Get chapter information from TOC
    toc = book.get("table_of_contents", {})
    chapters = toc.get("chapters", [])

    # Find the chapter
    chapter_info = None
    for chapter in chapters:
        if chapter.get("id") == chapter_id:
            chapter_info = chapter
            break
        # Check subchapters
        for subchapter in chapter.get("subchapters", []):
            if subchapter.get("id") == chapter_id:
                chapter_info = subchapter
                break

    if not chapter_info:
        raise HTTPException(status_code=404, detail="Chapter not found in table of contents")

    # Get question responses from request or book data
    question_responses = [pair.model_dump() for pair in data.question_responses]

    # If no responses provided, try to get from stored chapter questions
    if not question_responses:
        # This would require implementing a question storage system
        # For now, we'll require responses to be provided
        raise HTTPException(
            status_code=400,
            detail="Question responses are required for draft generation. Please provide Q&A pairs."
        )

    # Get optional parameters
    writing_style = data.writing_style
    target_length = data.target_length

    # Validate target length
    if not isinstance(target_length, int) or target_length < 100 or target_length > 10000:
        target_length = 2000

    # Prepare book metadata for context
    book_metadata = {
        "title": book.get("title", ""),
        "genre": book.get("genre", ""),
        "target_audience": book.get("target_audience", ""),
    }

    try:
        # Generate draft using AI service
        result = await ai_service.generate_chapter_draft(
            chapter_title=chapter_info.get("title", ""),
            chapter_description=chapter_info.get("description", ""),
            question_responses=question_responses,
            book_metadata=book_metadata,
            writing_style=writing_style,
            target_length=target_length
        )

        if not result.get("success"):
            # Truncation is a user-fixable request problem, not an outage. 503
            # invites a retry that will fail identically; 422 says what to change
            # and carries the actionable message through (#352).
            if result.get("error_code") == "DRAFT_TRUNCATED":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "message": result.get("error"),
                        "error_code": "DRAFT_TRUNCATED",
                        "retryable": False,
                    },
                )
            raise HTTPException(
                status_code=503,
                detail=f"Failed to generate draft: {result.get('error', 'Unknown error')}"
            )

        # Log the draft generation
        await audit_after_commit(
            request=Request(
                {
                    "type": "http",
                    "method": "POST",
                    "url": f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft",
                    "headers": {},
                    "path": f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft"
                }
            ),
            current_user=current_user,
            action="generate_chapter_draft",
            resource_type="chapter",
            target_id=chapter_id,
            metadata={
                "book_id": book_id,
                "question_count": len(question_responses),
                "target_length": target_length,
                "actual_length": result["metadata"].get("word_count", 0),
                "writing_style": writing_style or "default"
            }
        )

        return {
            "success": True,
            "book_id": book_id,
            "chapter_id": chapter_id,
            "draft": result["draft"],
            "metadata": result["metadata"],
            "suggestions": result.get("suggestions", []),
            "message": "Draft generated successfully"
        }

    except HTTPException:
        raise
    # Same structured mapping the other AI endpoints use. Draft generation had
    # only the generic handler below, so once ai_service stopped flattening
    # AIServiceError into a dict, a rate limit would have surfaced as an opaque
    # 500 with no retry_after (#352).
    except AIServiceError as e:
        raise ai_error_http_exception(e)
    except Exception:
        logger.error("Error generating draft", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error generating draft"
        )


def _rewrite_failure(result: dict, action: str) -> HTTPException:
    """The response for a transform, enhance or cleanup that did not succeed.

    A rewrite the model could not finish, or one that came back with most of
    the text gone, is a 413 with a fixed code: the text is too long for one
    pass, and 503 would invite a retry that ends the same way (#801, #983).
    Anything else is an outage.
    """
    if result.get("error_code") in ("REWRITE_TRUNCATED", "REWRITE_SHORTENED"):
        return HTTPException(
            status_code=413,
            detail={
                "message": result.get("error"),
                "error_code": result["error_code"],
                "retryable": False,
            },
        )
    return HTTPException(
        status_code=503,
        detail=f"Failed to {action}: {result.get('error', 'Unknown error')}",
    )


@router.post("/{book_id}/chapters/{chapter_id}/transform-style", response_model=dict, dependencies=[Depends(get_ai_usage_quota()), Depends(get_entitlement_checker("transform_style"))])
async def transform_chapter_style(
    book_id: str,
    chapter_id: str,
    data: TransformStyleRequest = Body(default=TransformStyleRequest()),
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(
        get_rate_limiter(limit=10, window=3600)
    ),  # 10 per hour
):
    """
    Transform existing chapter text into a target writing style (issue #58).

    Preview-only: returns the rewritten text without persisting. The caller
    applies it via the chapter-content PATCH endpoint and can revert by
    restoring the snapshot it held before applying.
    """
    # Verify book ownership.
    owner_id = await get_book_owner_id(book_id)
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if owner_id != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to transform content for this book",
        )

    content = data.content
    target_style = data.target_style

    if not content or not content.strip():
        raise HTTPException(
            status_code=400,
            detail="Content is required for style transformation.",
        )
    if not is_valid_style(target_style):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported writing style: {target_style!r}. "
                f"Valid styles: {', '.join(available_styles())}."
            ),
        )

    try:
        result = await ai_service.transform_text_style(
            content=content, target_style=target_style
        )
    except AIServiceError as e:
        raise ai_error_http_exception(e)

    if not result.get("success"):
        raise _rewrite_failure(result, "transform style")

    return {
        "success": True,
        "book_id": book_id,
        "chapter_id": chapter_id,
        "transformed": result["transformed"],
        "metadata": result["metadata"],
        "message": "Style transformed successfully",
    }


@router.post("/{book_id}/chapters/{chapter_id}/enhance-text", response_model=dict, dependencies=[Depends(get_ai_usage_quota()), Depends(get_entitlement_checker("enhance_text"))])
async def enhance_chapter_text(
    book_id: str,
    chapter_id: str,
    data: EnhanceTextRequest = Body(default=EnhanceTextRequest()),
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(
        get_rate_limiter(limit=10, window=3600)
    ),  # 10 per hour
):
    """
    Enhance existing chapter text along one dimension (issue #57).

    Preview-only: returns the improved text without persisting. The caller
    applies it and can revert by restoring the snapshot it held before applying.
    Dimensions: clarity, grammar, tone, vocabulary.
    """
    # Verify book ownership.
    book = await get_book_metadata_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to enhance content for this book",
        )

    # Verify the chapter exists (matches the other chapter content endpoints),
    # so a stale/mistyped id can't consume the enhancement quota.
    chapters = book.get("table_of_contents", {}).get("chapters", [])

    def find_chapter(chapter_list):
        for chapter in chapter_list:
            if chapter.get("id") == chapter_id:
                return chapter
            if chapter.get("subchapters"):
                found = find_chapter(chapter["subchapters"])
                if found:
                    return found
        return None

    if not find_chapter(chapters):
        raise HTTPException(status_code=404, detail="Chapter not found")

    content = data.content
    enhancement_type = data.enhancement_type

    if not content or not content.strip():
        raise HTTPException(
            status_code=400,
            detail="Content is required for enhancement.",
        )
    if not is_valid_enhancement(enhancement_type):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported enhancement type: {enhancement_type!r}. "
                f"Valid types: {', '.join(available_enhancements())}."
            ),
        )

    try:
        result = await ai_service.enhance_text(
            content=content, enhancement_type=enhancement_type
        )
    except AIServiceError as e:
        raise ai_error_http_exception(e)

    if not result.get("success"):
        raise _rewrite_failure(result, "enhance text")

    return {
        "success": True,
        "book_id": book_id,
        "chapter_id": chapter_id,
        "enhanced": result["enhanced"],
        "metadata": result["metadata"],
        "message": "Text enhanced successfully",
    }


@router.post(
    "/{book_id}/chapters/{chapter_id}/enhance-transcription",
    response_model=dict,
    dependencies=[Depends(get_ai_usage_quota()), Depends(get_entitlement_checker("enhance_transcription"))],
)
async def enhance_chapter_transcription(
    book_id: str,
    chapter_id: str,
    data: EnhanceTranscriptionRequest = Body(default=EnhanceTranscriptionRequest()),
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(
        get_rate_limiter(limit=10, window=3600)
    ),  # 10 per hour
):
    """
    Clean up raw voice-dictated text into readable prose (issue #56).

    Preview-only: returns the cleaned-up text (filler removal, paragraph breaks,
    grammar/punctuation) without persisting. The caller applies it and can revert
    by restoring the snapshot it held before applying. Single cleanup mode.
    """
    # Verify book ownership.
    book = await get_book_metadata_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to enhance content for this book",
        )

    # Verify the chapter exists (matches the other chapter content endpoints),
    # so a stale/mistyped id can't consume the cleanup quota.
    chapters = book.get("table_of_contents", {}).get("chapters", [])

    def find_chapter(chapter_list):
        for chapter in chapter_list:
            if chapter.get("id") == chapter_id:
                return chapter
            if chapter.get("subchapters"):
                found = find_chapter(chapter["subchapters"])
                if found:
                    return found
        return None

    if not find_chapter(chapters):
        raise HTTPException(status_code=404, detail="Chapter not found")

    content = data.content
    if not content or not content.strip():
        raise HTTPException(
            status_code=400,
            detail="Transcription is required for cleanup.",
        )

    try:
        result = await ai_service.enhance_transcription(content=content)
    except AIServiceError as e:
        raise ai_error_http_exception(e)

    if not result.get("success"):
        raise _rewrite_failure(result, "clean up transcription")

    return {
        "success": True,
        "book_id": book_id,
        "chapter_id": chapter_id,
        "enhanced": result["enhanced"],
        "metadata": result["metadata"],
        "message": "Transcription cleaned up successfully",
    }
