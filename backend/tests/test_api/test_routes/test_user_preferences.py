import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime, timezone


def test_update_user_preferences(auth_client_factory):
    """
    Test that user preferences can be updated successfully.
    Verifies that preference changes are saved correctly in the database.
    """
    # Preferences update data
    preferences_update = {
        "preferences": {
            "theme": "light",
            "email_notifications": False,
            "marketing_emails": True,
        }
    }

    # Make the request to update preferences
    response = auth_client_factory().patch("/api/v1/users/me", json=preferences_update)

    # Assert successful response
    assert response.status_code == 200
    data = response.json()

    # Verify preferences were updated correctly
    assert "preferences" in data
    assert data["preferences"]["theme"] == "light"
    assert data["preferences"]["email_notifications"] == False
    assert data["preferences"]["marketing_emails"] == True


def test_update_partial_preferences(auth_client_factory, test_user):
    """
    Test that partial preference updates work correctly.
    Verifies that updating only specific preferences doesn't affect others.
    """
    # Only update theme preference
    partial_update = {"preferences": {"theme": "system"}}

    # Expected user after update
    expected_user = test_user.copy()
    expected_user["preferences"] = {
        "theme": "system",
        "email_notifications": True,  # Unchanged from mock_user_data
        "marketing_emails": False,  # Unchanged from mock_user_data
    }

    # Make the request to update preferences
    response = auth_client_factory().patch("/api/v1/users/me", json=partial_update)

    # Assert successful response
    assert response.status_code == 200
    data = response.json()

    # Verify only the theme was updated
    assert "preferences" in data
    assert data["preferences"]["theme"] == "system"
    assert data["preferences"]["email_notifications"] == True
    assert data["preferences"]["marketing_emails"] == False


def test_preferences_retrieval(auth_client_factory, test_user):
    """
    Test that user preferences are correctly retrieved from the profile endpoint.
    Verifies that the API returns the correct preference values.
    """

    # Make the request to get profile with preferences
    response = auth_client_factory().get("/api/v1/users/me")

    # Assert successful response
    assert response.status_code == 200
    data = response.json()

    # Verify preferences are returned correctly
    assert "preferences" in data
    assert data["preferences"]["theme"] == test_user["preferences"]["theme"]
    assert (
        data["preferences"]["email_notifications"]
        == test_user["preferences"]["email_notifications"]
    )
    assert (
        data["preferences"]["marketing_emails"]
        == test_user["preferences"]["marketing_emails"]
    )


def test_preferences_default_values(auth_client_factory):
    """
    Test that default preferences are provided for new users.
    Verifies that the API assigns default preference values when none are specified.
    """
    # User with no preferences set
    user_without_preferences = {
        "id": "user_123",
        "_id": "user_123",
        "clerk_id": "clerk_user_123",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "display_name": "Test User",
        "role": "user",
        # No preferences defined
    }

    # Make the request to get profile
    response = auth_client_factory().get("/api/v1/users/me")

    # Assert successful response
    assert response.status_code == 200
    data = response.json()

    # Verify default preferences are provided
    assert "preferences" in data
    assert "theme" in data["preferences"]
    assert "email_notifications" in data["preferences"]
    assert "marketing_emails" in data["preferences"]


def test_invalid_preference_values(auth_client_factory):
    """
    Test validation of preference values.
    Verifies that the API validates preference values properly.
    """
    # Update with invalid theme value
    invalid_update = {
        "preferences": {
            "theme": "invalid_theme",
            "email_notifications": "NotABoolean",  # Invalid type
        }
    }

    # Make the request to update preferences
    response = auth_client_factory().patch("/api/v1/users/me", json=invalid_update)

    # Assert validation error
    assert response.status_code == 422
    data = response.json()

    # Verify response indicates validation error
    assert "detail" in data
