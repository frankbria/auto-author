"""Account data export (#790): GET /users/me/export.

Real better-auth session documents, no patched resolver, so the owner scoping
is the one production uses.
"""

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from app.db.base import get_collection
from tests.test_api.test_routes.test_account_deletion_real_session import (
    _client,
    _seed_better_auth_user,
)


async def _seed_content(owner_id: str, marker: str) -> None:
    """A book with chapter content, a question, an answer and a rating, each
    carrying ``marker`` so a leak into another user's export is detectable."""
    book_id = str(
        (
            await (await get_collection("books")).insert_one(
                {
                    "title": f"{marker} book",
                    "owner_id": owner_id,
                    "created_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
                    "collaborators": [{"user_id": f"{marker}-invitee"}],
                    "table_of_contents": {
                        "chapters": [
                            {"id": "ch1", "title": "One", "content": f"<p>{marker} chapter</p>"}
                        ]
                    },
                }
            )
        ).inserted_id
    )
    question_id = str(
        (
            await (await get_collection("questions")).insert_one(
                {"book_id": book_id, "user_id": owner_id, "question_text": f"{marker} question"}
            )
        ).inserted_id
    )
    await (await get_collection("question_responses")).insert_one(
        {"question_id": question_id, "user_id": owner_id, "response_text": f"{marker} answer"}
    )
    await (await get_collection("question_ratings")).insert_one(
        {"question_id": question_id, "user_id": owner_id, "rating": 4, "feedback": f"{marker} rating"}
    )


async def _export(token: str):
    async with _client(token) as c:
        return await c.get("/api/v1/users/me/export")


@pytest.mark.asyncio
async def test_export_returns_the_callers_profile_books_and_answers(motor_reinit_db):
    seeded = await _seed_better_auth_user("exporter@example.com", name="Ex Porter")
    await _seed_content(seeded["user_id"], "MINE")

    response = await _export(seeded["tokens"][0])

    assert response.status_code == 200, response.text
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert data["profile"]["email"] == "exporter@example.com"
    assert data["profile"]["first_name"] == "Ex"
    assert datetime.fromisoformat(data["exported_at"])
    [book] = data["books"]
    assert book["title"] == "MINE book"
    assert book["table_of_contents"]["chapters"][0]["content"] == "<p>MINE chapter</p>"
    assert ObjectId.is_valid(book["_id"])
    # Mongo hands dates back naive; the file marks every one as UTC.
    assert book["created_at"] == "2026-10-01T00:00:00+00:00"
    assert data["profile"]["created_at"].endswith("+00:00")
    assert "collaborators" not in book and "invitee" not in response.text
    assert [q["question_text"] for q in data["questions"]] == ["MINE question"]
    assert [r["response_text"] for r in data["question_responses"]] == ["MINE answer"]
    assert [r["feedback"] for r in data["question_ratings"]] == ["MINE rating"]


@pytest.mark.asyncio
async def test_export_never_contains_another_users_data(motor_reinit_db):
    """No IDOR: the endpoint takes no id, and each export holds only its caller's rows."""
    alice = await _seed_better_auth_user("alice@example.com", name="Alice A")
    bob = await _seed_better_auth_user("bob@example.com", name="Bob B")
    await _seed_content(alice["user_id"], "ALICE")
    await _seed_content(bob["user_id"], "BOB")

    alices = await _export(alice["tokens"][0])
    bobs = await _export(bob["tokens"][0])

    assert "ALICE" in alices.text and "BOB" not in alices.text
    assert "bob@example.com" not in alices.text
    assert "BOB" in bobs.text and "ALICE" not in bobs.text
    assert "alice@example.com" not in bobs.text
    assert len(bobs.json()["books"]) == 1


@pytest.mark.asyncio
async def test_export_holds_no_credential_and_no_internal_field(motor_reinit_db):
    seeded = await _seed_better_auth_user("careful@example.com")
    async with _client(seeded["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
    await (await get_collection("users")).update_one(
        {"auth_id": seeded["user_id"]},
        {"$set": {"stripe_event_created": 1760000000, "internal_note": "fraud-flag"}},
    )

    response = await _export(seeded["tokens"][0])

    assert response.status_code == 200
    # The seed's password hash, TOTP secret, backup codes and session token. The
    # endpoint reads no better-auth collection, so this half is a tripwire for
    # the day one is added; the planted users-doc fields test the allowlist.
    for secret in ('"hash"', "totp-secret", '"codes"', seeded["tokens"][0]):
        assert secret not in response.text
    profile = response.json()["profile"]
    assert "stripe_event_created" not in profile and "internal_note" not in profile


@pytest.mark.asyncio
async def test_export_requires_a_session(motor_reinit_db):
    async with _client("no-such-token") as c:
        response = await c.get("/api/v1/users/me/export")
    assert response.status_code == 401
