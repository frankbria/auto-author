# backend/app/db/book_delete.py
"""Book deletion: the cascade across a book's children, and the cover-file
cleanup. Split from ``book.py`` (#1144); its public names are re-exported there.
"""

import logging
from typing import Dict, List, Optional, Tuple

from bson.objectid import ObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from app.core.reporting import report_failure

from .audit_log import audit_after_write
from .base import books_collection, users_collection, _client, get_collection

logger = logging.getLogger(__name__)


# All a delete needs from a book. Unprojected, the read pulls every chapter's
# HTML just to throw it away (#786).
_DELETE_PROJECTION = {"title": 1, "cover_image_url": 1, "cover_thumbnail_url": 1}

# One $in filter is a single BSON document, capped at 16MB; an id costs about
# 35 bytes in it.
_QUESTION_ID_CHUNK = 100_000


async def delete_book(book_id: str, user_auth_id: str) -> bool:
    """Delete a book and cascade-delete all of its related data.

    Removes (atomically when MongoDB supports transactions via a replica set,
    and with a safe children-first ordering otherwise):
    - chapter access logs, questions, question responses, question ratings
    - the book document
    - the book association on the user

    Mirrors the conditional-transaction pattern in ``toc_transactions``. On a
    non-transactional deployment a mid-cascade failure leaves the book document
    (deleted last) intact, so it stays discoverable rather than orphaned.
    """
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_auth_id}, _DELETE_PROJECTION
    )
    if not book:
        return False
    # ObjectId() accepts uppercase hex; children and files are keyed by the
    # canonical lowercase id (#797).
    book_id = str(book["_id"])

    # Detect replica-set support; multi-document transactions require one.
    use_transaction = True
    try:
        async with _client.start_session():
            info = await _client.admin.command("isMaster")
            use_transaction = info.get("setName") is not None
    except Exception:
        use_transaction = False

    try:
        if use_transaction:
            async with _client.start_session() as session:
                async with await session.start_transaction():
                    deleted, counts, gone = await _delete_books_internal(
                        [book_id], user_auth_id, session
                    )
        else:
            deleted, counts, gone = await _delete_books_internal([book_id], user_auth_id, None)
    except Exception:
        # Transactional path rolls back; non-transactional path is contained by
        # children-first ordering (the book document is deleted last).
        logger.error("Cascade delete failed for book %s", book_id, exc_info=True)
        raise

    # The book vanished between the ownership check and the delete.
    if not deleted:
        return False

    # The delete's own pre-image: a cover replaced since the read above is the
    # one the book had when it went (#938).
    await _delete_cover_files(gone)

    await audit_after_write(
        action="book_delete",
        actor_id=user_auth_id,
        target_id=book_id,
        resource_type="book",
        details={"cascade_deleted": counts},
    )
    return True


async def delete_all_user_books(user_auth_id: str) -> int:
    """Cascade-delete every book the user owns (account deletion, issue #179).

    One command per collection however many books there are (#786): a per-book
    loop timed out on a 2,649-book account. A failure propagates so the caller
    can abort before touching the user record (children first, parents last),
    leaving the books in place for a retry. Returns the number of books deleted.

    Never a transaction, even on a replica set: one spanning a whole account
    outlives the 60s transaction limit on exactly the accounts this is for.
    The id list is a snapshot; delete_user runs this again after the tombstone
    to catch a book created mid-cascade (#945).
    """
    books = await books_collection.find(
        {"owner_id": user_auth_id}, _DELETE_PROJECTION
    ).to_list(length=None)
    if not books:
        return 0

    deleted, counts, _ = await _delete_books_internal(
        [str(book["_id"]) for book in books], user_auth_id, None
    )

    # Covers in batched storage calls (#941), once the documents are gone (#785).
    files = [
        (str(book["_id"]), url)
        for book in books
        for url in (book.get("cover_image_url"), book.get("cover_thumbnail_url"))
        if url
    ]
    if files:
        try:
            from app.services.file_upload_service import FileUploadService

            await FileUploadService().delete_cover_images(files)
        except Exception as error:  # the service could not be set up at all
            logger.error("Failed to delete cover files for %s", user_auth_id, exc_info=True)
            report_failure("delete-files", error)

    # One row for the account, without the titles a per-book row would keep.
    await audit_after_write(
        action="delete_books",
        actor_id=user_auth_id,
        target_id=user_auth_id,
        resource_type="books",
        details={"deleted_count": deleted, "cascade_deleted": counts},
    )
    return deleted


async def _delete_cover_files(book: Dict) -> None:
    """Remove a deleted book's cover and thumbnail. Only once the delete has
    committed: a removed file cannot roll back (#785)."""
    cover_url = book.get("cover_image_url")
    thumbnail_url = book.get("cover_thumbnail_url")
    if not (cover_url or thumbnail_url):
        return
    book_id = str(book["_id"])
    try:
        from app.services.file_upload_service import FileUploadService

        await FileUploadService().delete_cover_image(book_id, cover_url, thumbnail_url)
    except Exception as error:
        # Reached only when the upload service cannot be set up at all: its
        # own delete never raises, and reports from where it catches.
        logger.error("Failed to delete cover files for book %s", book_id, exc_info=True)
        report_failure("delete-files", error)


async def _delete_books_internal(
    book_ids: List[str],
    user_auth_id: str,
    session: Optional[AsyncClientSession],
) -> Tuple[int, Dict[str, int], Optional[Dict]]:
    """Run the cascade deletes for ``book_ids``, optionally inside a transaction
    ``session``. Children go first and the book documents + user association
    last, so a non-transactional partial failure leaves the books discoverable.
    Returns the number of book documents deleted (0 if they vanished after the
    ownership check), the per-collection child delete counts, and for a single
    book the document as the delete removed it (its pre-image), else None.
    """
    chapter_access_logs = await get_collection("chapter_access_logs")
    questions_collection = await get_collection("questions")
    responses_collection = await get_collection("question_responses")
    ratings_collection = await get_collection("question_ratings")
    in_books = {"$in": book_ids}
    question_scope = {"book_id": in_books, "user_id": user_auth_id}

    access_logs_result = await chapter_access_logs.delete_many(
        {"book_id": in_books}, session=session
    )

    questions = await questions_collection.find(
        question_scope, {"_id": 1}, session=session
    ).to_list(length=None)
    question_ids = [str(q["_id"]) for q in questions]

    responses_deleted = ratings_deleted = 0
    for start in range(0, len(question_ids), _QUESTION_ID_CHUNK):
        in_questions = {"question_id": {"$in": question_ids[start : start + _QUESTION_ID_CHUNK]}}
        responses_deleted += (
            await responses_collection.delete_many(in_questions, session=session)
        ).deleted_count
        ratings_deleted += (
            await ratings_collection.delete_many(in_questions, session=session)
        ).deleted_count

    questions_result = await questions_collection.delete_many(
        question_scope, session=session
    )

    # Parents last: book documents, then the user's book_ids association.
    book_filter = {"_id": {"$in": [ObjectId(b) for b in book_ids]}, "owner_id": user_auth_id}
    gone = None
    if len(book_ids) == 1:
        gone = await books_collection.find_one_and_delete(
            book_filter, projection=_DELETE_PROJECTION, session=session
        )
        deleted = int(gone is not None)
    else:
        deleted = (await books_collection.delete_many(book_filter, session=session)).deleted_count
    if deleted:
        await users_collection.update_one(
            {"auth_id": user_auth_id}, {"$pull": {"book_ids": in_books}}, session=session
        )

    return deleted, {
        "chapter_access_logs": access_logs_result.deleted_count,
        "questions": questions_result.deleted_count,
        "question_responses": responses_deleted,
        "question_ratings": ratings_deleted,
    }, gone
