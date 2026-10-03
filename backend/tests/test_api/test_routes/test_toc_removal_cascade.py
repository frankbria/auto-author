"""Removing a chapter deletes its questions, responses and ratings (#755).

Questions live in their own collection keyed by ``(book_id, chapter_id,
user_id)``; responses and ratings hang off the question id. Nothing deleted
them when a chapter left the TOC, so they waited for any later chapter with the
same id and fed its draft generation. Every path that drops a chapter (PUT /toc,
DELETE chapter, accepting a regenerated TOC through PUT /toc) now cascades.

Real MongoDB; only the AI service is patched (it would otherwise call OpenAI).
"""

from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId

from app.db import base
from app.db.base import get_collection

API = "/api/v1/books"
AI_PATCH_TARGET = (
    "app.services.ai_service.ai_service.generate_toc_from_summary_and_responses"
)


def _chapter(cid, title, subchapters=()):
    return {"id": cid, "title": title, "level": 1, "order": 1, "subchapters": list(subchapters)}


async def _book_with_toc(api, chapters, **extra):
    r = await api.post(f"{API}/", json={"title": "Cascade", "genre": "Non-fiction"})
    assert r.status_code == 201, r.text
    book_id = r.json()["id"]
    await base.books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {"$set": {"table_of_contents": {"chapters": chapters, "version": 3}, **extra}},
    )
    book = await base.books_collection.find_one({"_id": ObjectId(book_id)})
    return book_id, book["owner_id"]


async def _seed_qa(book_id, chapter_id, user_id):
    """One question for the chapter, with a response and a rating."""
    questions = await get_collection("questions")
    qid = str(
        (
            await questions.insert_one(
                {"book_id": book_id, "chapter_id": chapter_id, "user_id": user_id,
                 "question_text": f"About {chapter_id}?", "order": 1}
            )
        ).inserted_id
    )
    # `seed` tags the children with their chapter, so they stay countable after
    # their question is gone; counting through surviving questions would read 0
    # even if the cascade left every answer behind.
    seed = f"{book_id}/{chapter_id}"
    await (await get_collection("question_responses")).insert_one(
        {"question_id": qid, "user_id": user_id, "response_text": "An answer", "seed": seed}
    )
    await (await get_collection("question_ratings")).insert_one(
        {"question_id": qid, "user_id": user_id, "rating": 4, "seed": seed}
    )
    return qid


async def _qa_counts(book_id, chapter_id):
    """(questions, responses, ratings) stored for one chapter of one book."""
    seed = {"seed": f"{book_id}/{chapter_id}"}
    return (
        await (await get_collection("questions")).count_documents(
            {"book_id": book_id, "chapter_id": chapter_id}
        ),
        await (await get_collection("question_responses")).count_documents(seed),
        await (await get_collection("question_ratings")).count_documents(seed),
    )


async def _children_of(qid):
    responses = await (await get_collection("question_responses")).count_documents({"question_id": qid})
    ratings = await (await get_collection("question_ratings")).count_documents({"question_id": qid})
    return responses, ratings


class TestPutTocCascades:
    @pytest.mark.asyncio
    async def test_dropping_a_chapter_deletes_its_qa_and_keeps_the_rest(self, auth_client_factory):
        api = await auth_client_factory()
        book_id, user_id = await _book_with_toc(
            api, [_chapter("x", "Gone", [_chapter("x-sub", "Gone too")]), _chapter("y", "Stays")]
        )
        for cid in ("x", "x-sub", "y"):
            await _seed_qa(book_id, cid, user_id)

        r = await api.put(f"{API}/{book_id}/toc", json={"toc": {"chapters": [_chapter("y", "Stays")]}})

        assert r.status_code == 200, r.text
        assert await _qa_counts(book_id, "x") == (0, 0, 0)
        assert await _qa_counts(book_id, "x-sub") == (0, 0, 0)
        assert await _qa_counts(book_id, "y") == (1, 1, 1)

    @pytest.mark.asyncio
    async def test_cascade_is_scoped_to_the_book_and_user(self, auth_client_factory):
        """Another book holding the same chapter id keeps its questions."""
        api = await auth_client_factory()
        book_id, user_id = await _book_with_toc(api, [_chapter("x", "Gone")])
        other_book, _ = await _book_with_toc(api, [_chapter("x", "Other book")])
        await _seed_qa(book_id, "x", user_id)
        other_qid = await _seed_qa(other_book, "x", user_id)
        stranger_qid = await _seed_qa(book_id, "x", "someone-else")

        r = await api.put(f"{API}/{book_id}/toc", json={"toc": {"chapters": []}})

        assert r.status_code == 200, r.text
        questions = await get_collection("questions")
        assert await questions.count_documents({"book_id": book_id, "user_id": user_id}) == 0
        assert await questions.count_documents({"_id": ObjectId(other_qid)}) == 1
        assert await _children_of(other_qid) == (1, 1)
        assert await questions.count_documents({"_id": ObjectId(stranger_qid)}) == 1
        assert await _children_of(stranger_qid) == (1, 1)

    @pytest.mark.asyncio
    async def test_remove_then_readd_same_id_shows_zero_questions(self, auth_client_factory):
        """The acceptance test: remove X, then a direct API client re-adds a
        chapter carrying X's id. X's questions must not come back."""
        api = await auth_client_factory()
        book_id, user_id = await _book_with_toc(api, [_chapter("x", "Old X"), _chapter("y", "Y")])
        await _seed_qa(book_id, "x", user_id)

        r = await api.put(f"{API}/{book_id}/toc", json={"toc": {"chapters": [_chapter("y", "Y")]}})
        assert r.status_code == 200, r.text
        r = await api.put(
            f"{API}/{book_id}/toc",
            json={"toc": {"chapters": [_chapter("y", "Y"), _chapter("x", "New X")]}},
        )
        assert r.status_code == 200, r.text

        new_x = next(c for c in r.json()["toc"]["chapters"] if c["title"] == "New X")
        assert await _qa_counts(book_id, "x") == (0, 0, 0)
        listed = await api.get(f"{API}/{book_id}/chapters/{new_x['id']}/questions")
        assert listed.status_code == 200, listed.text
        assert listed.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_failed_put_deletes_nothing(self, auth_client_factory):
        """A 409 leaves the TOC unchanged, so it must leave the Q&A too.

        This is the expected_version 409. The race 409 (another writer bumps the
        version between read and write) cannot be produced deterministically
        without mocking the books collection; the cascade sits after that
        write's modified_count check for the same reason."""
        api = await auth_client_factory()
        book_id, user_id = await _book_with_toc(api, [_chapter("x", "X")])
        await _seed_qa(book_id, "x", user_id)

        r = await api.put(
            f"{API}/{book_id}/toc", json={"toc": {"chapters": [], "expected_version": 1}}
        )

        assert r.status_code == 409, r.text
        assert await _qa_counts(book_id, "x") == (1, 1, 1)


class TestDeleteChapterCascades:
    @pytest.mark.asyncio
    async def test_delete_endpoint_removes_chapter_and_subchapter_qa(self, auth_client_factory):
        api = await auth_client_factory()
        book_id, user_id = await _book_with_toc(
            api, [_chapter("x", "Gone", [_chapter("x-sub", "Gone too")]), _chapter("y", "Stays")]
        )
        for cid in ("x", "x-sub", "y"):
            await _seed_qa(book_id, cid, user_id)

        r = await api.delete(f"{API}/{book_id}/chapters/x")

        assert r.status_code == 200, r.text
        assert await _qa_counts(book_id, "x") == (0, 0, 0)
        assert await _qa_counts(book_id, "x-sub") == (0, 0, 0)
        assert await _qa_counts(book_id, "y") == (1, 1, 1)

    @pytest.mark.asyncio
    async def test_deleting_a_missing_chapter_deletes_nothing(self, auth_client_factory):
        api = await auth_client_factory()
        book_id, user_id = await _book_with_toc(api, [_chapter("y", "Y")])
        await _seed_qa(book_id, "ghost", user_id)

        r = await api.delete(f"{API}/{book_id}/chapters/ghost")

        assert r.status_code == 404, r.text
        assert await _qa_counts(book_id, "ghost") == (1, 1, 1)


class TestAcceptingRegeneratedTocCascades:
    @pytest.mark.asyncio
    async def test_accepting_a_regenerated_toc_drops_the_old_chapters_qa(self, auth_client_factory):
        """generate-toc only proposes (#753); PUT /toc with the proposal is the
        accept. The proposal carries fresh ids, so every old chapter is removed."""
        api = await auth_client_factory()
        book_id, user_id = await _book_with_toc(
            api, [_chapter("ch1", "Old one"), _chapter("ch2", "Old two")], summary="A summary."
        )
        for cid in ("ch1", "ch2"):
            await _seed_qa(book_id, cid, user_id)
        proposal = {
            "toc": {"chapters": [_chapter("ch1", "New one"), _chapter("ch2", "New two")]},
            "chapters_count": 2,
            "has_subchapters": False,
            "success": True,
        }

        with patch(AI_PATCH_TARGET, AsyncMock(return_value=proposal)):
            gen = await api.post(
                f"{API}/{book_id}/generate-toc",
                json={"question_responses": [{"question": "Q", "answer": "A"}]},
            )
        assert gen.status_code == 200, gen.text
        body = gen.json()
        r = await api.put(
            f"{API}/{book_id}/toc",
            json={"toc": {**body["toc"], "expected_version": body["base_version"]}},
        )

        assert r.status_code == 200, r.text
        assert await _qa_counts(book_id, "ch1") == (0, 0, 0)
        assert await _qa_counts(book_id, "ch2") == (0, 0, 0)
