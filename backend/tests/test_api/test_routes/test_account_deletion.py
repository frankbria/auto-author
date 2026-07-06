import pytest
from unittest.mock import patch, AsyncMock

from bson.objectid import ObjectId

from app.db.base import get_collection


async def _seed_book_with_children(owner_id: str) -> str:
    """Insert a book owned by ``owner_id`` plus a question, response, rating,
    and chapter access log (the collections delete_book cascades). Returns the
    book id."""
    books = await get_collection("books")
    questions = await get_collection("questions")
    responses = await get_collection("question_responses")
    ratings = await get_collection("question_ratings")
    access_logs = await get_collection("chapter_access_logs")

    book_id = str(
        (await books.insert_one({"title": "Mine", "owner_id": owner_id})).inserted_id
    )
    question_id = str(
        (
            await questions.insert_one(
                {"book_id": book_id, "user_id": owner_id, "text": "Q?"}
            )
        ).inserted_id
    )
    await responses.insert_one(
        {"question_id": question_id, "user_id": owner_id, "answer": "A"}
    )
    await ratings.insert_one({"question_id": question_id, "rating": 4})
    await access_logs.insert_one({"book_id": book_id, "user_id": owner_id})
    return book_id


@pytest.mark.asyncio
async def test_account_deletion_successful(auth_client_factory):
    """
    Test successful account deletion.
    Verifies that the account deletion process works correctly.
    """
    # Get authenticated client with default test user
    client = await auth_client_factory()

    # Make the request to delete account
    response = await client.delete("/api/v1/users/me")

    # Assert successful response
    assert response.status_code == 200
    data = response.json()

    # Verify response indicates successful deletion
    assert "message" in data
    assert "successfully deleted" in data["message"].lower()


@pytest.mark.skip(reason="Skipping test: Unclear if this is a valid test case")
def test_account_deletion_user_not_found(auth_client_factory, fake_user):
    """
    Test account deletion when user is not found in database.
    Verifies that the API handles the case when the user to delete doesn't exist.
    """
    # Get authenticated client with fake user data
    client = auth_client_factory(
        {
            "auth": False,
            "clerk_id": fake_user["clerk_id"],
            "email": fake_user["email"],
            "first_name": fake_user["first_name"],
            "last_name": fake_user["last_name"],
        }
    )

    # Make the request to delete account
    response = client.delete("/api/v1/users/me")

    # Assert not found response
    assert response.status_code == 404
    data = response.json()

    # Verify response indicates user not found
    assert "detail" in data
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_account_deletion_with_data_cleanup(auth_client_factory):
    """DELETE /users/me cascades the user's books and their questions,
    responses, ratings and access logs; the user record itself is soft-deleted
    (retained with is_active False). Issue #179."""
    client = await auth_client_factory()
    owner_id = "test-auth-id-123"  # conftest test_user auth_id

    book_a = await _seed_book_with_children(owner_id)
    book_b = await _seed_book_with_children(owner_id)
    # Another user's book must survive.
    other_book = await _seed_book_with_children("someone-else")

    response = await client.delete("/api/v1/users/me")
    assert response.status_code == 200

    books = await get_collection("books")
    questions = await get_collection("questions")
    responses = await get_collection("question_responses")
    ratings = await get_collection("question_ratings")
    access_logs = await get_collection("chapter_access_logs")
    users = await get_collection("users")

    assert await books.count_documents({"owner_id": owner_id}) == 0
    for book_id in (book_a, book_b):
        assert await questions.count_documents({"book_id": book_id}) == 0
        assert await access_logs.count_documents({"book_id": book_id}) == 0
    assert await responses.count_documents({"user_id": owner_id}) == 0
    assert await ratings.count_documents({}) == 1  # only the other user's

    assert await books.find_one({"_id": ObjectId(other_book)}) is not None
    assert (
        await questions.count_documents({"book_id": other_book}) == 1
    ), "another user's data must not be touched"

    user_doc = await users.find_one({"auth_id": owner_id})
    assert user_doc is not None, "user record is soft-deleted, not removed"
    assert user_doc["is_active"] is False


@pytest.mark.asyncio
async def test_account_deletion_cascade_failure_keeps_user_active(
    auth_client_factory, monkeypatch
):
    """If the book cascade fails, the account deletion 500s and the user is
    NOT soft-deleted — children first, parent last — so a retry can finish
    the job."""
    import app.api.endpoints.users as users_endpoint

    client = await auth_client_factory(overrides={"is_active": True})
    owner_id = "test-auth-id-123"
    book_id = await _seed_book_with_children(owner_id)

    async def _boom(user_auth_id):
        raise RuntimeError("simulated mongo failure")

    monkeypatch.setattr(users_endpoint, "delete_all_user_books", _boom)

    response = await client.delete("/api/v1/users/me")
    assert response.status_code == 500

    books = await get_collection("books")
    users = await get_collection("users")
    assert await books.find_one({"_id": ObjectId(book_id)}) is not None
    user_doc = await users.find_one({"auth_id": owner_id})
    assert (
        user_doc["is_active"] is True
    ), "user must stay active after a failed cascade"


@pytest.mark.asyncio
async def test_delete_by_auth_id_also_cascades(auth_client_factory):
    """The self-or-admin DELETE /users/{auth_id} path cascades books too —
    it previously orphaned them exactly like /me (#179 review finding)."""
    client = await auth_client_factory()
    owner_id = "test-auth-id-123"
    await _seed_book_with_children(owner_id)

    response = await client.delete(f"/api/v1/users/{owner_id}")
    assert response.status_code == 204

    books = await get_collection("books")
    questions = await get_collection("questions")
    assert await books.count_documents({"owner_id": owner_id}) == 0
    assert await questions.count_documents({"user_id": owner_id}) == 0


@pytest.mark.asyncio
async def test_account_deletion_requires_authentication(auth_client_factory):
    """
    Test that account deletion requires authentication.
    Verifies that unauthenticated requests are rejected.
    """
    # Use the unauthenticated client fixture directly
    client = await auth_client_factory(auth=False)

    # Make the request without authentication headers
    response = await client.delete("/api/v1/users/me")

    # Assert unauthorized response - expect 401 Unauthorized for missing auth
    assert response.status_code == 401
    data = response.json()

    # Verify response indicates authentication issue
    assert "detail" in data
    assert (
        "authenticated" in data["detail"].lower()
        or "credentials" in data["detail"].lower()
        or "authorization" in data["detail"].lower()
    )


@pytest.mark.skip(reason="Skipping test: No admin functionality yet")
def test_admin_delete_other_account(auth_client_factory):
    """
    Test that admin can delete another user's account.
    """
    # Create admin user with auth_client_factory
    client = auth_client_factory({"role": "admin", "clerk_id": "admin_clerk_id"})

    # User to be deleted
    target_user_id = "clerk_user_to_delete"

    # Mock the necessary dependencies
    with patch(
        "app.db.database.delete_user", new_callable=AsyncMock
    ) as delete_user_mock:
        delete_user_mock.return_value = True

        # Make the request to delete another user's account
        response = client.delete(f"/api/v1/users/{target_user_id}")

        # Assert successful response
        assert response.status_code == 204  # No content

        # Verify our database delete function was called
        delete_user_mock.assert_called_once()


@pytest.mark.asyncio
async def test_regular_user_cannot_delete_other_account(auth_client_factory):
    """
    Test that regular users cannot delete another user's account.
    """
    # Create regular user with auth_client_factory
    client = await auth_client_factory(
        overrides={"role": "user", "clerk_id": "regular_user_clerk_id"}
    )

    # Target user ID (different from authenticated user)
    target_user_id = "different_clerk_id"

    # Make the request to delete another user's account
    response = await client.delete(f"/api/v1/users/{target_user_id}")

    # Assert forbidden response
    assert response.status_code == 403
    data = response.json()

    # Verify response indicates permission issue
    assert "detail" in data
    assert "permissions" in data["detail"].lower()
