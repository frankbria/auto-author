"""Chapter ids are unique across the TOC tree and minted by the server (#754).

The chapter content autosave writes with ``array_filters=[{"c.id": id}]``,
which updates every element carrying that id. Edit TOC minted
``ch${toc.length + 1}``, so delete-then-add stored ``[ch1, ch3, ch3]`` and one
autosave overwrote two chapters. Since #749, PUT /toc also copies a stored
draft onto every incoming item with the same id, so id identity decides which
chapter keeps which draft.

Real MongoDB; only the AI service is patched (it would otherwise call OpenAI).
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId

from app.db import base

API = "/api/v1/books"
AI_PATCH_TARGET = (
    "app.services.ai_service.ai_service.generate_toc_from_summary_and_responses"
)


def _is_uuid4(value):
    try:
        return uuid.UUID(value).version == 4
    except (ValueError, TypeError, AttributeError):
        return False


def _chapter(cid, title, content=None, subchapters=()):
    item = {"id": cid, "title": title, "level": 1, "order": 1, "subchapters": list(subchapters)}
    if content is not None:
        item["content"] = content
    return item


async def _book_with_toc(api, chapters, version=3):
    r = await api.post(f"{API}/", json={"title": "Ids", "genre": "Non-fiction"})
    assert r.status_code == 201, r.text
    book_id = r.json()["id"]
    await base.books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {"$set": {"table_of_contents": {"chapters": chapters, "version": version}}},
    )
    return book_id


async def _stored_toc(book_id):
    book = await base.books_collection.find_one({"_id": ObjectId(book_id)})
    return book["table_of_contents"]


def _flat(toc):
    for ch in toc["chapters"]:
        yield ch
        yield from ch.get("subchapters") or []


class TestPutTocRejectsDuplicateIds:
    @pytest.mark.asyncio
    async def test_delete_then_add_duplicate_is_400_and_toc_unchanged(
        self, auth_client_factory
    ):
        """The issue's reproduction: Edit TOC deletes ch2 and adds a chapter it
        numbers ch3, sending [ch1, ch3, ch3]. Main accepted it and the next
        autosave overwrote both ch3s."""
        api = await auth_client_factory()
        stored = [
            _chapter("ch1", "One", "<p>one</p>"),
            _chapter("ch2", "Two", "<p>two</p>"),
            _chapter("ch3", "Three", "<p>three</p>"),
        ]
        book_id = await _book_with_toc(api, stored)
        before = await _stored_toc(book_id)

        r = await api.put(
            f"{API}/{book_id}/toc",
            json={
                "toc": {
                    "chapters": [
                        _chapter("ch1", "One"),
                        _chapter("ch3", "Three"),
                        _chapter("ch3", "New Chapter"),
                    ]
                }
            },
        )

        assert r.status_code == 400, r.text
        assert r.json()["detail"] == "Chapter ids must be unique across the table of contents"
        assert await _stored_toc(book_id) == before

    @pytest.mark.asyncio
    async def test_duplicate_id_spelled_like_an_error_is_still_400(self, auth_client_factory):
        """The endpoint maps "not found" in an error to 404, so the message
        must not echo the client's id (found in cross-family review)."""
        api = await auth_client_factory()
        book_id = await _book_with_toc(api, [_chapter("a", "A")])

        r = await api.put(
            f"{API}/{book_id}/toc",
            json={"toc": {"chapters": [_chapter("Book not found", "X"), _chapter("Book not found", "Y")]}},
        )

        assert r.status_code == 400, r.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "sub",
        [
            {"id": "a", "title": "Sub"},
            {"id": "s", "title": "Sub", "subchapters": [{"id": "a", "title": "Deeper"}]},
        ],
        ids=["subchapter", "nested-subchapter"],
    )
    async def test_duplicate_anywhere_in_the_tree_is_400(self, auth_client_factory, sub):
        api = await auth_client_factory()
        book_id = await _book_with_toc(api, [_chapter("a", "A"), _chapter("b", "B")])
        before = await _stored_toc(book_id)

        r = await api.put(
            f"{API}/{book_id}/toc",
            json={"toc": {"chapters": [_chapter("a", "A"), _chapter("b", "B", subchapters=[sub])]}},
        )

        assert r.status_code == 400, r.text
        assert await _stored_toc(book_id) == before


class TestServerMintsIds:
    @pytest.mark.asyncio
    async def test_unknown_ids_are_replaced_known_ids_keep_drafts(
        self, auth_client_factory
    ):
        api = await auth_client_factory()
        book_id = await _book_with_toc(
            api, [_chapter("ch1", "One", "<p>one</p>"), _chapter("ch2", "Two", "<p>two</p>")]
        )

        r = await api.put(
            f"{API}/{book_id}/toc",
            json={
                "toc": {
                    "chapters": [
                        _chapter("ch2", "Two renamed"),
                        _chapter("client-made", "New", subchapters=[{"title": "No id"}]),
                        _chapter("ch1", "One"),
                    ]
                }
            },
        )
        assert r.status_code == 200, r.text

        toc = await _stored_toc(book_id)
        two, new, one = toc["chapters"]
        assert (two["id"], two["content"]) == ("ch2", "<p>two</p>")
        assert (one["id"], one["content"]) == ("ch1", "<p>one</p>")
        assert _is_uuid4(new["id"]) and new["id"] != "client-made"
        assert _is_uuid4(new["subchapters"][0]["id"])
        assert "content" not in new
        # The response describes the stored ids, so the client sees the minted one.
        assert [c["id"] for c in r.json()["toc"]["chapters"]] == [c["id"] for c in toc["chapters"]]

    @pytest.mark.asyncio
    async def test_reused_removed_id_does_not_inherit_its_draft(
        self, auth_client_factory
    ):
        """Requested on the issue after #749: a new chapter that reuses a
        removed chapter's id must not pick up that chapter's draft, or its
        questions (#755)."""
        api = await auth_client_factory()
        book_id = await _book_with_toc(
            api, [_chapter("ch1", "Keep", "<p>keep</p>"), _chapter("ch2", "Gone", "<p>gone</p>")]
        )
        r = await api.put(f"{API}/{book_id}/toc", json={"toc": {"chapters": [_chapter("ch1", "Keep")]}})
        assert r.status_code == 200, r.text

        r = await api.put(
            f"{API}/{book_id}/toc",
            json={"toc": {"chapters": [_chapter("ch1", "Keep"), _chapter("ch2", "Different")]}},
        )
        assert r.status_code == 200, r.text

        keep, different = (await _stored_toc(book_id))["chapters"]
        assert keep["content"] == "<p>keep</p>"
        assert different["id"] != "ch2" and _is_uuid4(different["id"])
        assert "content" not in different

    @pytest.mark.asyncio
    async def test_generate_toc_proposes_uuid4_ids(self, auth_client_factory):
        """AI output uses positional ids (ch1, ch1-1). If a stored TOC also has
        ch1, accepting the proposal would hand that draft to an unrelated
        chapter, so the proposal carries fresh ids."""
        api = await auth_client_factory()
        book_id = await _book_with_toc(api, [_chapter("ch1", "Old", "<p>old</p>")])
        await api.put(f"{API}/{book_id}/summary", json={"summary": "A long enough summary " * 5})
        proposal = {
            "toc": {
                "chapters": [
                    _chapter("ch1", "Intro", subchapters=[{"id": "ch1-1", "title": "Why"}]),
                    _chapter("ch2", "Body"),
                ]
            },
            "chapters_count": 2,
            "has_subchapters": True,
            "success": True,
        }

        with patch(AI_PATCH_TARGET, new=AsyncMock(return_value=proposal)):
            r = await api.post(
                f"{API}/{book_id}/generate-toc",
                json={"question_responses": [{"question": "Q", "answer": "A"}]},
            )

        assert r.status_code == 200, r.text
        ids = [item["id"] for item in _flat(r.json()["toc"])]
        assert len(ids) == 3 and all(_is_uuid4(i) for i in ids)
        assert len(set(ids)) == 3


class TestAddChapter:
    @pytest.mark.asyncio
    async def test_added_chapter_gets_uuid4(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _book_with_toc(api, [_chapter("ch1", "One")])

        r = await api.post(f"{API}/{book_id}/chapters", json={"title": "Two", "order": 2})

        assert r.status_code == 201, r.text
        assert _is_uuid4(r.json()["chapter_id"])

    @pytest.mark.asyncio
    async def test_add_to_tree_with_duplicate_ids_is_400_and_toc_unchanged(
        self, auth_client_factory
    ):
        api = await auth_client_factory()
        book_id = await _book_with_toc(api, [_chapter("ch3", "A"), _chapter("ch3", "B")])
        before = await _stored_toc(book_id)

        r = await api.post(f"{API}/{book_id}/chapters", json={"title": "C", "order": 3})

        assert r.status_code == 400, r.text
        assert await _stored_toc(book_id) == before


@pytest.mark.asyncio
async def test_autosave_after_toc_edit_changes_only_its_chapter(auth_client_factory):
    """End to end: edit the TOC (adding a chapter), then autosave one chapter.
    Only that chapter's draft changes."""
    api = await auth_client_factory()
    book_id = await _book_with_toc(
        api, [_chapter("ch1", "One", "<p>one</p>"), _chapter("ch2", "Two", "<p>two</p>")]
    )
    r = await api.put(
        f"{API}/{book_id}/toc",
        json={"toc": {"chapters": [_chapter("ch1", "One"), _chapter("ch2", "Two"), _chapter("ch3", "Three")]}},
    )
    assert r.status_code == 200, r.text
    new_id = r.json()["toc"]["chapters"][2]["id"]

    r = await api.patch(f"{API}/{book_id}/chapters/{new_id}/content", json={"content": "<p>new</p>"})
    assert r.status_code == 200, r.text

    contents = {c["id"]: c.get("content") for c in (await _stored_toc(book_id))["chapters"]}
    assert contents == {"ch1": "<p>one</p>", "ch2": "<p>two</p>", new_id: "<p>new</p>"}
