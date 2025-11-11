import pytest, pytest_asyncio
from unittest.mock import patch, AsyncMock
import app


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


@pytest.mark.skip(reason="Skipping test: No books data table yet")
def test_account_deletion_with_data_cleanup(auth_client_factory):
    """
    Test account deletion with associated data cleanup.
    Verifies that the API cleans up all user data during deletion.
    """
    # Create a client with user data that has books
    books = ["book_id_1", "book_id_2"]
    client = auth_client_factory({"books": books})

    # Mock function to delete books

    # Make the request to delete account
    response = client.delete("/api/v1/users/me")

    # Assert successful response
    assert response.status_code == 200

    # Verify that the books were deleted


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
