"""PATCH changes what it is sent and nothing else (#848).

A preferences PATCH replaced the stored object, so every key it left out fell
back to its default, and `"preferences": null` wiped them. A book PATCH needed a
title, and dropped every null, so a subtitle or description could never be
cleared. Real routes and real MongoDB.
"""

import pytest

from app.db.base import get_collection
from tests.test_api.test_routes.test_books_chapters_crud_coverage import create_book

pytestmark = pytest.mark.asyncio


async def _stored_preferences(api):
    me = (await api.get("/api/v1/users/me")).json()
    user = await (await get_collection("users")).find_one({"auth_id": me["auth_id"]})
    return user["preferences"]


async def test_a_partial_preferences_patch_keeps_the_keys_it_left_out(auth_client_factory):
    # The seeded user has email_notifications False, against a default of True.
    api = await auth_client_factory()

    patched = await api.patch("/api/v1/users/me", json={"preferences": {"theme": "system"}})

    assert patched.status_code == 200, patched.text
    assert patched.json()["preferences"]["theme"] == "system"
    assert patched.json()["preferences"]["email_notifications"] is False
    assert await _stored_preferences(api) == {
        "theme": "system", "email_notifications": False, "marketing_emails": False,
    }


async def test_null_preferences_write_no_null(auth_client_factory):
    api = await auth_client_factory()

    patched = await api.patch("/api/v1/users/me", json={"preferences": None, "bio": "Still here."})

    assert patched.status_code == 200, patched.text
    assert await _stored_preferences(api) == {
        "theme": "light", "email_notifications": False, "marketing_emails": False,
    }


async def test_a_book_patch_without_a_title_succeeds_and_clears_a_nullable_field(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    await api.patch(f"/api/v1/books/{book_id}", json={"title": "Kept", "subtitle": "Going"})

    patched = await api.patch(f"/api/v1/books/{book_id}", json={"subtitle": None, "genre": "Memoir"})

    assert patched.status_code == 200, patched.text
    book = (await api.get(f"/api/v1/books/{book_id}")).json()
    assert (book["title"], book["subtitle"], book["genre"]) == ("Kept", None, "Memoir")


@pytest.mark.parametrize("field", ["title", "published", "metadata"])
async def test_a_book_patch_cannot_null_a_field_that_must_have_a_value(auth_client_factory, field):
    api = await auth_client_factory()
    book_id = await create_book(api)

    patched = await api.patch(f"/api/v1/books/{book_id}", json={field: None})

    assert patched.status_code == 422, patched.text


async def test_a_user_whose_preferences_were_nulled_before_848_can_set_one_again(auth_client_factory):
    api = await auth_client_factory(overrides={"preferences": None})

    patched = await api.patch("/api/v1/users/me", json={"preferences": {"theme": "system"}})

    assert patched.status_code == 200, patched.text
    assert await _stored_preferences(api) == {"theme": "system"}


async def test_a_null_genre_or_audience_never_reaches_a_prompt_as_none():
    from app.services.ai_service import AIService
    from app.services.question_generation_service import QuestionGenerationService

    meta = {"title": "T", "genre": None, "target_audience": None, "audience": None}
    ai = AIService()
    prompts = [
        ai._build_summary_analysis_prompt("A summary.", meta),
        ai._build_questions_prompt("A summary.", meta, 3),
        ai._build_toc_generation_prompt("A summary.", [], meta),
        ai._build_draft_generation_prompt("One", "", [], meta, None, 500),
        QuestionGenerationService(ai)._build_question_generation_prompt("One", "", meta, 3),
    ]

    assert [p for p in prompts if "None" in p] == []
