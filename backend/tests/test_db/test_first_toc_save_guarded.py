"""The first save of a book's TOC is guarded like every later one (#871).

For a book with no TOC, GET /toc said version 0 while PUT counted a missing
version as 1, so the Edit TOC page sent no expected_version on a first save
(it would have been a 409). And PUT added its version filter only when a TOC
already existed. Two first saves, from two tabs or the wizard and Edit TOC,
both succeeded, and the second silently replaced the first.

Against a real MongoDB.
"""

import asyncio

import pytest
from bson import ObjectId

import app.db.toc_transactions as tx
from app.db.toc_transactions import update_toc_with_transaction

OWNER = "owner-auth-871"


def _toc(*titles: str, expected_version: int | None = None) -> dict:
    toc = {"chapters": [{"title": title, "description": "", "level": 1, "order": n, "subchapters": []} for n, title in enumerate(titles, 1)]}
    if expected_version is not None:
        toc["expected_version"] = expected_version
    return toc


async def _a_book_with_no_toc() -> str:
    book_id = ObjectId()
    await tx.books_collection.insert_one({"_id": book_id, "owner_id": OWNER, "title": "Small Changes"})
    return str(book_id)


async def _stored_titles(book_id: str) -> list[str]:
    book = await tx.books_collection.find_one({"_id": ObjectId(book_id)})
    return [chapter["title"] for chapter in book["table_of_contents"]["chapters"]]


@pytest.mark.asyncio
async def test_two_first_saves_that_both_read_before_either_writes_do_not_both_land(motor_reinit_db, monkeypatch):
    """The race the version is for: each writer reads the book, then both write."""
    book_id = await _a_book_with_no_toc()
    both_have_read = asyncio.Barrier(2)
    real_find_one = tx.books_collection.find_one

    async def find_one_then_wait(*args, **kwargs):
        found = await real_find_one(*args, **kwargs)
        if kwargs.get("session") is None and args and args[0].get("owner_id") == OWNER:
            await asyncio.wait_for(both_have_read.wait(), 5)
        return found

    monkeypatch.setattr(tx.books_collection, "find_one", find_one_then_wait)

    results = await asyncio.gather(
        update_toc_with_transaction(book_id, _toc("From the first tab", expected_version=1), OWNER),
        update_toc_with_transaction(book_id, _toc("From the second tab", expected_version=1), OWNER),
        return_exceptions=True,
    )
    monkeypatch.undo()

    refused = [r for r in results if isinstance(r, ValueError) and "Version conflict" in str(r)]
    landed = [r for r in results if not isinstance(r, BaseException)]
    assert (len(landed), len(refused)) == (1, 1), results
    assert await _stored_titles(book_id) in (["From the first tab"], ["From the second tab"])


@pytest.mark.asyncio
async def test_a_second_first_save_with_the_same_expected_version_is_a_conflict(motor_reinit_db):
    book_id = await _a_book_with_no_toc()

    await update_toc_with_transaction(book_id, _toc("From the wizard", expected_version=1), OWNER)
    with pytest.raises(ValueError, match="Version conflict"):
        await update_toc_with_transaction(book_id, _toc("From Edit TOC", expected_version=1), OWNER)

    assert await _stored_titles(book_id) == ["From the wizard"]


@pytest.mark.asyncio
async def test_get_and_put_agree_on_the_version_of_a_book_with_no_toc(auth_client_factory):
    api = await auth_client_factory()
    created = await api.post("/api/v1/books/", json={"title": "Small Changes", "genre": "Self-help", "target_audience": "Managers"})
    book = f"/api/v1/books/{created.json()['id']}"

    read = await api.get(f"{book}/toc")
    first_save = await api.put(f"{book}/toc", json={"toc": _toc("Why Habits Stick", expected_version=read.json()["version"])})
    second_save = await api.put(f"{book}/toc", json={"toc": _toc("Overwritten", expected_version=read.json()["version"])})

    assert read.json()["status"] == "not_generated"
    assert first_save.status_code == 200, first_save.text
    assert second_save.status_code == 409, second_save.text
