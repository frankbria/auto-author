"""Every route with a book id in its path refuses someone who does not own the book (#840).

Ownership was tested route by route, by whoever wrote the route, and
``export/docx`` and ``export/formats`` had no such test at all. This is one
sweep over the application's own route table: each route is sent a request the
owner could have sent, by another signed-in user, and must answer 403 or 404
and leave the book as it was. A route added later with a book id in its path
fails ``test_every_book_route_is_in_the_sweep`` until it is given a request here.

Both users sign in with real session cookies (#838): nothing stands in for the
sign-in check, so the user a route sees is the one production would give it.
"""

import io
from datetime import datetime, timezone

import pytest
from bson import ObjectId
from PIL import Image

from app.core.security import get_current_user_from_session
from app.db.base import get_collection
from app.db.questions import create_question
from app.main import app
from app.schemas.book import QuestionCreate, QuestionDifficulty, QuestionMetadata, QuestionType
from app.services.ai_service import ai_service
from tests.route_introspection import route_dependency_calls
from tests.session_cookies import mint_session, real_session_client
from tests.test_services.openai_autospec import autospec_openai_client

BOOK_ROUTE = "/api/v1/books/{book_id}"
CHAPTER = "/chapters/{chapter_id}"
QUESTION = CHAPTER + "/questions/{question_id}"
CHAPTER_ID = "ch-1"


def _a_cover() -> bytes:
    picture = io.BytesIO()
    Image.new("RGB", (600, 900), "navy").save(picture, "PNG")
    return picture.getvalue()


# One request for every route under a book: (method, path after the book) -> what to send.
# Each is a request that is in order apart from who sends it, so that a refusal is for whose
# book it is and not for what was asked.
REQUESTS: dict[tuple[str, str], dict] = {
    ("GET", ""): {},
    ("PUT", ""): {"json": {"title": "Mine Now"}},
    ("PATCH", ""): {"json": {"title": "Mine Now"}},
    ("DELETE", ""): {},
    ("POST", "/analyze-summary"): {"json": {}},
    ("GET", "/summary"): {},
    ("PUT", "/summary"): {"json": {"summary": "A summary of somebody else's book, long enough to be one."}},
    # With no summary in it, this route answers with the one the book has. Its write is tied to the
    # owner in the database as well; this reading path has only the route's own check, so it is the one swept.
    ("PATCH", "/summary"): {"json": {}},
    ("POST", "/generate-questions"): {"json": {}},
    ("GET", "/question-responses"): {},
    ("PUT", "/question-responses"): {"json": {"responses": [{"question": "Who is it for?", "answer": "Managers."}]}},
    ("GET", "/toc-readiness"): {},
    ("POST", "/generate-toc"): {"json": {}},
    ("GET", "/toc"): {},
    ("PUT", "/toc"): {"json": {"toc": {"chapters": [], "total_chapters": 0, "estimated_pages": 0, "structure_notes": ""}}},
    ("POST", "/cover-image"): {"files": {"file": ("cover.png", _a_cover(), "image/png")}},
    ("GET", "/export/formats"): {},
    ("GET", "/export/templates"): {},
    ("GET", "/export/pdf"): {},
    ("GET", "/export/docx"): {},
    ("GET", "/export/epub"): {},
    ("GET", "/export/markdown"): {},
    ("GET", "/chapters"): {},
    ("POST", "/chapters"): {"json": {"title": "A chapter of my own", "order": 2}},
    ("GET", "/chapters/metadata"): {},
    ("GET", "/chapters/tab-state"): {},
    ("POST", "/chapters/tab-state"): {
        "json": {"active_chapter_id": CHAPTER_ID, "open_tab_ids": [CHAPTER_ID], "tab_order": [CHAPTER_ID]}
    },
    ("POST", "/chapters/batch-content"): {"json": {"chapter_ids": [CHAPTER_ID]}},
    ("PATCH", "/chapters/bulk-status"): {"json": {"chapter_ids": [CHAPTER_ID], "status": "completed"}},
    ("GET", CHAPTER): {},
    ("PUT", CHAPTER): {"json": {"title": "Mine Now"}},
    ("DELETE", CHAPTER): {},
    ("GET", CHAPTER + "/content"): {},
    ("PATCH", CHAPTER + "/content"): {"json": {"content": "<p>Mine now.</p>"}},
    ("POST", CHAPTER + "/enhance-text"): {"json": {"content": "<p>A sentence to improve, and another after it.</p>", "enhancement_type": "grammar"}},
    ("POST", CHAPTER + "/enhance-transcription"): {"json": {"content": "um so a sentence to tidy up, you know"}},
    ("POST", CHAPTER + "/generate-draft"): {
        "json": {"question_responses": [{"question": "Who is it for?", "answer": "Managers."}]}
    },
    ("POST", CHAPTER + "/transform-style"): {"json": {"content": "<p>A sentence to restyle, and another after it.</p>", "target_style": "professional"}},
    ("POST", CHAPTER + "/generate-questions"): {"json": {"count": 3}},
    ("POST", CHAPTER + "/regenerate-questions"): {"json": {"count": 3}},
    ("GET", CHAPTER + "/questions"): {},
    ("GET", CHAPTER + "/question-progress"): {},
    ("POST", CHAPTER + "/questions/responses/batch"): {
        "json": [{"question_id": "{question_id}", "response_text": "Mine now.", "status": "draft"}]
    },
    ("GET", QUESTION + "/response"): {},
    ("PUT", QUESTION + "/response"): {"json": {"response_text": "Mine now.", "status": "draft"}},
    ("POST", QUESTION + "/rating"): {"json": {"question_id": "{question_id}", "user_id": "someone", "rating": 1}},
    ("POST", QUESTION + "/regenerate"): {"json": {}},
}

# The collections a book's content lives in. A refused request leaves every one of them as it was.
CONTENT = ("books", "questions", "question_responses", "question_ratings")


def _live_book_routes() -> set[tuple[str, str]]:
    return {
        (method, path.removeprefix(BOOK_ROUTE))
        for method, path in route_dependency_calls()
        if "{book_id}" in path
    }


def test_every_book_route_is_in_the_sweep():
    live = _live_book_routes()

    assert live, "found no route with a book id in its path: the route table is not being read"
    assert sorted(live - set(REQUESTS)) == [], "a route under a book has no request in REQUESTS, so nothing checks who may use it"
    assert sorted(set(REQUESTS) - live) == [], "REQUESTS names a route the application no longer has"


def test_every_route_with_a_book_id_is_under_the_books_prefix():
    # The sweep builds its paths from the prefix. A book id anywhere else would be swept wrongly.
    assert [path for _, path in route_dependency_calls() if "{book_id}" in path and not path.startswith(BOOK_ROUTE)] == []


async def _signed_in(email: str):
    now = datetime.now(timezone.utc)
    oid = ObjectId()
    await (await get_collection("user")).insert_one(
        {"_id": oid, "email": email, "name": email.split("@")[0], "emailVerified": True, "createdAt": now, "updatedAt": now}
    )
    client = real_session_client(await mint_session(oid))
    # The first request makes the application's own record of the user; do it before anything is compared.
    assert (await client.get("/api/v1/users/me")).status_code == 200
    return client


async def _adas_book(ada) -> dict:
    """A book of Ada's with a chapter, a question on it, an answer and a rating: something for every route to find."""
    created = await ada.post(
        "/api/v1/books/", json={"title": "Small Changes", "genre": "Self-help", "target_audience": "Managers"}
    )
    assert created.status_code == 201, created.text
    book_id = created.json()["id"]
    chapter = {
        "id": CHAPTER_ID, "title": "Why Habits Stick", "description": "", "level": 1, "order": 1,
        "status": "draft", "content": "<p>A habit holds when the first step is small.</p>", "word_count": 9, "subchapters": [],
    }
    await (await get_collection("books")).update_one(
        {"_id": ObjectId(book_id)},
        {"$set": {
            "summary": "Why small habits last and large resolutions do not, for managers who have tried both.",
            "table_of_contents": {"chapters": [chapter], "total_chapters": 1, "estimated_pages": 1, "structure_notes": "", "version": 1},
        }},
    )
    owner = (await ada.get("/api/v1/users/me")).json()["auth_id"]
    question = await create_question(
        QuestionCreate(
            book_id=book_id, chapter_id=CHAPTER_ID, question_text="Who is this chapter for?",
            question_type=QuestionType.THEME, difficulty=QuestionDifficulty.MEDIUM, category="reader", order=1,
            metadata=QuestionMetadata(suggested_response_length="2-3 sentences"),
        ),
        owner,
    )
    ids = {"book_id": book_id, "chapter_id": CHAPTER_ID, "question_id": question["id"]}
    answered = await ada.put(
        (BOOK_ROUTE + QUESTION + "/response").format(**ids), json={"response_text": "Managers.", "status": "draft"}
    )
    assert answered.status_code < 300, answered.text
    clarified = await ada.put(
        BOOK_ROUTE.format(**ids) + "/question-responses",
        json={"responses": [{"question": "Who is the book for?", "answer": "Managers who have tried a big change and seen it fail."}]},
    )
    assert clarified.status_code < 300, clarified.text
    return ids


async def _content() -> dict:
    return {name: [doc async for doc in (await get_collection(name)).find().sort("_id", 1)] for name in CONTENT}


def _filled(value, ids: dict):
    """The request with the book's own ids in it, wherever a body names one."""
    if isinstance(value, str):
        return value.format(**ids) if "{" in value else value
    if isinstance(value, list):
        return [_filled(item, ids) for item in value]
    if isinstance(value, dict):
        return {key: (item if key == "files" else _filled(item, ids)) for key, item in value.items()}
    return value


@pytest.fixture
def the_model(monkeypatch):
    """The provider's ``create`` call, stood in for: no test here talks to a real model."""
    provider = autospec_openai_client()
    monkeypatch.setattr(ai_service, "client", provider)
    return provider.chat.completions.create


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", sorted(REQUESTS), ids=lambda part: part or "/")
async def test_someone_who_does_not_own_the_book_is_refused(reinit_db, the_model, method, path):
    assert get_current_user_from_session not in app.dependency_overrides
    ada = await _signed_in("ada@example.com")
    grace = await _signed_in("grace@example.com")
    try:
        ids = await _adas_book(ada)
        before = await _content()

        answer = await grace.request(method, (BOOK_ROUTE + path).format(**ids), **_filled(REQUESTS[(method, path)], ids))

        assert answer.status_code in (403, 404), f"{answer.status_code}: {answer.text[:300]}"
        assert await _content() == before, "a refused request changed the book"
        assert not the_model.called, "a refused request reached the model, on the owner's account or the stranger's"
    finally:
        await ada.aclose()
        await grace.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", sorted(REQUESTS), ids=lambda part: part or "/")
async def test_the_owner_is_not_refused_the_same_request(reinit_db, the_model, method, path):
    """The other half. A request that the owner is refused too proves nothing about the stranger:
    she may have been turned away for a missing chapter or an empty answer, by a route that never
    looked at whose book it was."""
    ada = await _signed_in("ada@example.com")
    try:
        ids = await _adas_book(ada)

        answer = await ada.request(method, (BOOK_ROUTE + path).format(**ids), **_filled(REQUESTS[(method, path)], ids))

        # Through means answered, or passed on to the model: what the stand-in model says back is
        # not usable by every route, and that is not a refusal. A refusal is one whenever it comes.
        assert answer.status_code not in (401, 403, 404, 422), f"{answer.status_code}: {answer.text[:300]}"
        assert answer.status_code < 400 or the_model.called, f"{answer.status_code}: {answer.text[:300]}"
    finally:
        await ada.aclose()
