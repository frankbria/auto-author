"""Export downloads are named safely, and each export is logged (#804).

The title went into ``Content-Disposition`` as written. Starlette encodes
headers as latin-1, so a title outside it raised after the whole export had
been built: a 500 for every book with a CJK, Cyrillic or emoji title, in every
format. And every export's access-log call failed validation and was swallowed.

Real exports through the real routes; nothing is stubbed.
"""

from urllib.parse import unquote

import pytest

from app.db import base
from tests.test_api.test_export_endpoints import _seed_toc
from tests.test_api.test_rate_limit_routes import _small_toc

pytestmark = pytest.mark.asyncio

FORMATS = {"pdf": ".pdf", "docx": ".docx", "epub": ".epub", "markdown": ".md"}

# (title, the name a browser that reads filename* saves, the ASCII fallback)
TITLES = [
    ("書名", "書名", "book"),
    ("Война и мир", "Война и мир", "book"),
    ("📚 Field Guide", "Field Guide", "Field Guide"),
    ("Café Olé", "Café Olé", "Caf Ol"),
    ("Plain Title", "Plain Title", "Plain Title"),
]


async def _book(api, title: str) -> str:
    response = await api.post(
        "/api/v1/books/",
        json={"title": title, "genre": "Non-fiction", "target_audience": "Adults"},
    )
    assert response.status_code == 201, response.text
    book_id = response.json()["id"]
    await _seed_toc(book_id, _small_toc())
    return book_id


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("title, saved_as, fallback", TITLES, ids=[t[0] for t in TITLES])
async def test_a_book_with_any_title_exports_in_every_format(
    auth_client_factory, title, saved_as, fallback, fmt
):
    api = await auth_client_factory()
    book_id = await _book(api, title)

    response = await api.get(f"/api/v1/books/{book_id}/export/{fmt}")

    assert response.status_code == 200, response.text
    assert len(response.content) > 0
    disposition = response.headers["content-disposition"]
    extension = FORMATS[fmt]
    # RFC 6266: an ASCII name for clients that only read `filename`, and the
    # real one, percent-encoded UTF-8, in `filename*`.
    assert disposition.startswith(f'attachment; filename="{fallback}{extension}"; filename*=UTF-8\'\''), disposition
    assert unquote(disposition.split("filename*=UTF-8''")[1]) == f"{saved_as}{extension}"
    disposition.encode("ascii")  # the header itself never leaves ASCII


async def test_a_title_cannot_break_out_of_the_header(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _book(api, 'x"; filename="evil.exe\r\nSet-Cookie: a=b')

    response = await api.get(f"/api/v1/books/{book_id}/export/markdown")

    assert response.status_code == 200, response.text
    disposition = response.headers["content-disposition"]
    assert disposition.count('"') == 2
    assert "\r" not in disposition and "\n" not in disposition
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("fmt", FORMATS)
async def test_an_export_is_recorded_in_the_access_log(auth_client_factory, fmt):
    api = await auth_client_factory()
    book_id = await _book(api, "Logged Book")

    response = await api.get(f"/api/v1/books/{book_id}/export/{fmt}")

    assert response.status_code == 200, response.text
    rows = await base._db.get_collection("chapter_access_logs").find({"book_id": book_id}).to_list(None)
    assert len(rows) == 1
    [row] = rows
    assert row["access_type"] == f"export_{fmt}"
    assert row["chapter_id"] is None  # the whole book, not a chapter
    assert row["user_id"]
