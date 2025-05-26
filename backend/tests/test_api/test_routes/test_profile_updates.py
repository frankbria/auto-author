# filepath: d:\Projects\auto-author\backend\tests\test_api\test_routes\test_profile_updates.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_update_all_profile_fields(auth_client_factory, test_user):
    """
    Test that all profile fields can be updated successfully.
    This test verifies that each editable field is properly updated in the database.
    """
    # Create a client with test user data
    client = await auth_client_factory()

    # Update data with all editable fields
    update_data = {
        "first_name": "Updated",
        "last_name": "Name",
        "bio": "Updated user biography",
        "preferences": {
            "theme": "light",
            "email_notifications": False,
            "marketing_emails": True,
        },
    }

    # Create the expected updated user result
    updated_user = test_user.copy()
    updated_user["first_name"] = update_data["first_name"]
    updated_user["last_name"] = update_data["last_name"]
    updated_user["bio"] = update_data["bio"]
    updated_user["preferences"] = update_data["preferences"]

    # Mock the database update to return our expected result
    with patch("app.db.database.update_user", return_value=updated_user):
        # Make the request to update profile
        response = await client.patch("/api/v1/users/me", json=update_data)

        # Assert successful response
        assert response.status_code == 200

        # Get the response data
        data = response.json()

        # Verify all fields were updated correctly
        assert data["first_name"] == update_data["first_name"]
        assert data["last_name"] == update_data["last_name"]
        assert data["bio"] == update_data["bio"]
        assert data["preferences"]["theme"] == update_data["preferences"]["theme"]
        assert (
            data["preferences"]["email_notifications"]
            == update_data["preferences"]["email_notifications"]
        )
        assert (
            data["preferences"]["marketing_emails"]
            == update_data["preferences"]["marketing_emails"]
        )

        # Verify fields that shouldn't change
        assert data["email"] == test_user["email"]
        assert data["clerk_id"] == test_user["clerk_id"]
        assert data["role"] == test_user["role"]


@pytest.mark.asyncio
async def test_update_partial_profile_fields(auth_client_factory, test_user):
    """
    Test that partial profile updates work correctly.
    This test verifies that updating only specific fields doesn't affect other fields.
    """
    # Create a client with test user data
    client = await auth_client_factory()

    # Only update first_name and theme
    partial_update = {"first_name": "Partially", "preferences": {"theme": "system"}}

    # Create expected result with only those fields updated
    expected_result = test_user.copy()
    expected_result["first_name"] = "Partially"
    expected_result["preferences"]["theme"] = "system"

    # Mock the database update to return our expected result
    with patch("app.api.endpoints.users.update_user", return_value=expected_result):
        # Make the request to update profile
        response = await client.patch("/api/v1/users/me", json=partial_update)

        # Assert successful response
        assert response.status_code == 200

        # Get the response data
        data = response.json()

        # Verify specific fields were updated
        assert data["first_name"] == partial_update["first_name"]
        assert data["preferences"]["theme"] == partial_update["preferences"]["theme"]

        # Verify other fields remain unchanged
        assert data["last_name"] == test_user["last_name"]
        assert data["bio"] == test_user["bio"]
        assert (
            data["preferences"]["email_notifications"]
            == test_user["preferences"]["email_notifications"]
        )
        assert (
            data["preferences"]["marketing_emails"]
            == test_user["preferences"]["marketing_emails"]
        )


@pytest.mark.asyncio
async def test_invalid_preference_format(auth_client_factory, test_user):
    """
    Test that invalid preference formats are caught and properly handled.
    This test verifies the validation for preference object format.
    """
    # Create a client with test user data
    client = await auth_client_factory()

    # Invalid update - preferences as an array instead of an object
    invalid_update = {"preferences": ["light", True, False]}

    # Make the request to update profile
    response = await client.patch("/api/v1/users/me", json=invalid_update)

    # Assert validation error response
    assert response.status_code == 422

    # Error details should include information about the validation error
    body = response.json()
    assert "errors" in body

    # At least one error should mention 'preferences'
    prefs_errors = [
        err
        for err in body["errors"]
        if len(err.get("loc", [])) >= 2 and err["loc"][1] == "preferences"
    ]
    assert prefs_errors, f"No preference-related error in {body['errors']}"
