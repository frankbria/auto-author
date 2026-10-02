"""
Contract (#861): every value of the frontend's ``ChapterStatus`` enum must be
accepted by ``PATCH /books/{id}/chapters/bulk-status``.

The frontend sent ``'in_progress'`` while the backend enum is ``'in-progress'``,
so "Mark In Progress" always returned 422 and CI never noticed, because each
side's tests only used its own spelling. This reads the frontend enum source
and replays every value against the real endpoint.
"""

import re
from pathlib import Path

import pytest

FRONTEND_TYPES = Path(__file__).resolve().parents[4] / "frontend" / "src" / "types"


def _frontend_enum_values(filename: str):
    src = (FRONTEND_TYPES / filename).read_text()
    body = re.search(r"enum ChapterStatus\s*\{(.*?)\}", src, re.S)
    if body is None:  # chapter-tabs.ts re-exports the single enum from book.ts
        return None
    return re.findall(r"=\s*'([^']+)'", body.group(1))


def test_frontend_has_one_chapter_status_enum_definition():
    assert _frontend_enum_values("chapter-tabs.ts") is None
    assert _frontend_enum_values("book.ts"), "could not parse ChapterStatus in book.ts"


@pytest.mark.asyncio
async def test_bulk_status_accepts_every_frontend_status_value(auth_client_factory):
    values = _frontend_enum_values("book.ts")
    assert "in-progress" in values  # parser sanity: not vacuously empty

    api = await auth_client_factory()
    created = await api.post(
        "/api/v1/books/",
        json={
            "title": "Contract Book",
            "genre": "Fiction",
            "description": "frontend/backend status contract",
            "target_audience": "Adults",
        },
    )
    assert created.status_code == 201, created.text
    book_id = created.json()["id"]
    chapter = await api.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"title": "Ch", "description": "d", "level": 1, "order": 1},
    )
    assert chapter.status_code == 201, chapter.text
    chapter_id = chapter.json()["chapter_id"]

    for value in values:
        resp = await api.patch(
            f"/api/v1/books/{book_id}/chapters/bulk-status",
            json={"chapter_ids": [chapter_id], "status": value},
        )
        assert resp.status_code == 200, f"{value!r}: {resp.status_code} {resp.text}"
        assert resp.json()["new_status"] == value
