"""#1039: ``GET /chapters`` and ``GET /chapters/{id}`` returned every chapter body
and nothing called them (the client reads ``/chapters/metadata`` and
``/chapters/{id}/content``). They are removed; POST/PUT/DELETE on the same
paths stay."""

import pytest

from app.main import app


async def _book_with_chapter(api):
    book = await api.post(
        "/api/v1/books/",
        json={"title": "Gone", "genre": "Fiction", "description": "d", "target_audience": "Adults"},
    )
    book_id = book.json()["id"]
    made = await api.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"title": "Ch", "description": "d", "level": 1, "order": 1},
    )
    return book_id, made.json()["chapter_id"]


@pytest.mark.asyncio
async def test_list_chapters_route_is_gone(auth_client_factory):
    api = await auth_client_factory()
    book_id, _ = await _book_with_chapter(api)
    for suffix in ("", "?flat=true"):
        resp = await api.get(f"/api/v1/books/{book_id}/chapters{suffix}")
        assert resp.status_code == 405


@pytest.mark.asyncio
async def test_get_chapter_route_is_gone(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id = await _book_with_chapter(api)
    resp = await api.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}")
    assert resp.status_code == 405


def test_only_the_used_methods_remain_on_those_paths():
    paths = app.openapi()["paths"]
    assert set(paths["/api/v1/books/{book_id}/chapters"]) == {"post"}
    assert set(paths["/api/v1/books/{book_id}/chapters/{chapter_id}"]) == {"put", "delete"}
