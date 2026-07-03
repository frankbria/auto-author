import pytest
import pytest_asyncio
from httpx import AsyncClient
import json
from datetime import datetime, timezone

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_update_user_preferences(auth_client_factory):
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

    client = await auth_client_factory()

    # Make the request to update preferences
    response = await client.patch("/api/v1/users/me", json=preferences_update)

    # Assert successful response
    assert response.status_code == 200
    data = response.json()

    # Verify preferences were updated correctly
    assert "preferences" in data
    assert data["preferences"]["theme"] == "light"
    assert data["preferences"]["email_notifications"] is False
    assert data["preferences"]["marketing_emails"] is True


@pytest.mark.asyncio
async def test_update_partial_preferences(auth_client_factory, test_user):
    """
    Test that partial preference updates work correctly.
    Verifies that updating only specific preferences doesn't affect others.
    """
    # Only update theme preference
    partial_update = {"preferences": {"theme": "system"}}

    client = await auth_client_factory()

    # Make the request to update preferences
    response = await client.patch("/api/v1/users/me", json=partial_update)

    # Assert successful response
    assert response.status_code == 200
    data = response.json()

    # Verify only the theme was updated
    assert "preferences" in data
    assert data["preferences"]["theme"] == "system"


@pytest.mark.asyncio
async def test_preferences_retrieval(auth_client_factory, test_user):
    """
    Test that user preferences are correctly retrieved from the profile endpoint.
    Verifies that the API returns the correct preference values.
    """

    client = await auth_client_factory()

    # Make the request to get profile with preferences
    response = await client.get("/api/v1/users/me")

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


@pytest.mark.asyncio
async def test_preferences_default_values(auth_client_factory):
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
    }

    client = await auth_client_factory(overrides=user_without_preferences)

    # Make the request to get profile
    response = await client.get("/api/v1/users/me")

    # Assert successful response
    assert response.status_code == 200
    data = response.json()

    # Verify default preferences are provided
    assert "preferences" in data
    assert "theme" in data["preferences"]
    assert "email_notifications" in data["preferences"]
    assert "marketing_emails" in data["preferences"]


@pytest.mark.asyncio
async def test_update_extended_preferences(auth_client_factory):
    """
    Test that all extended settings preferences (#64) can be updated.
    Covers writing, export, and notification preference fields.
    """
    preferences_update = {
        "preferences": {
            "theme": "light",
            "email_notifications": True,
            "marketing_emails": False,
            "default_writing_style": "academic",
            "auto_save_interval": 10,
            "default_export_format": "epub",
            "default_page_size": "A4",
            "include_empty_chapters": True,
            "writing_reminders": True,
            "progress_updates": False,
            "backup_notifications": False,
        }
    }

    client = await auth_client_factory()

    response = await client.patch("/api/v1/users/me", json=preferences_update)

    assert response.status_code == 200
    data = response.json()

    prefs = data["preferences"]
    assert prefs["default_writing_style"] == "academic"
    assert prefs["auto_save_interval"] == 10
    assert prefs["default_export_format"] == "epub"
    assert prefs["default_page_size"] == "A4"
    assert prefs["include_empty_chapters"] is True
    assert prefs["writing_reminders"] is True
    assert prefs["progress_updates"] is False
    assert prefs["backup_notifications"] is False


@pytest.mark.asyncio
async def test_extended_preferences_round_trip(auth_client_factory, test_user):
    """
    Integration: extended preferences persist to the database on PATCH.

    GET /users/me echoes the session user (mocked in this harness), so
    persistence is asserted against the users collection directly.
    """
    from app.db import base

    client = await auth_client_factory()

    update = {
        "preferences": {
            "theme": "dark",
            "default_writing_style": "technical",
            "auto_save_interval": 30,
            "default_export_format": "markdown",
            "default_page_size": "letter",
            "include_empty_chapters": True,
            "writing_reminders": True,
            "progress_updates": True,
            "backup_notifications": False,
        }
    }
    patch_response = await client.patch("/api/v1/users/me", json=update)
    assert patch_response.status_code == 200

    stored = await base.users_collection.find_one({"auth_id": test_user["auth_id"]})
    assert stored is not None
    prefs = stored["preferences"]
    assert prefs["default_writing_style"] == "technical"
    assert prefs["auto_save_interval"] == 30
    assert prefs["default_export_format"] == "markdown"
    assert prefs["default_page_size"] == "letter"
    assert prefs["include_empty_chapters"] is True
    assert prefs["writing_reminders"] is True
    assert prefs["progress_updates"] is True
    assert prefs["backup_notifications"] is False


@pytest.mark.asyncio
async def test_extended_preferences_defaults(auth_client_factory):
    """
    New/legacy users with no stored extended preferences get sane defaults
    matching current shipped behavior (3s auto-save, conversational, pdf/letter).
    """
    user_without_preferences = {
        "id": "user_123",
        "_id": "user_123",
        "auth_id": "auth_user_123",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "display_name": "Test User",
        "role": "user",
    }

    client = await auth_client_factory(overrides=user_without_preferences)

    response = await client.get("/api/v1/users/me")

    assert response.status_code == 200
    prefs = response.json()["preferences"]
    assert prefs["default_writing_style"] == "conversational"
    assert prefs["auto_save_interval"] == 3
    assert prefs["default_export_format"] == "pdf"
    assert prefs["default_page_size"] == "letter"
    assert prefs["include_empty_chapters"] is False
    assert prefs["writing_reminders"] is False
    assert prefs["progress_updates"] is True
    assert prefs["backup_notifications"] is True


@pytest.mark.asyncio
async def test_invalid_writing_style_rejected(auth_client_factory):
    """default_writing_style outside the 5 shipped styles is a 422."""
    client = await auth_client_factory()

    response = await client.patch(
        "/api/v1/users/me",
        json={"preferences": {"default_writing_style": "narrative"}},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_export_format_rejected(auth_client_factory):
    """default_export_format outside pdf/docx/epub/markdown is a 422."""
    client = await auth_client_factory()

    response = await client.patch(
        "/api/v1/users/me",
        json={"preferences": {"default_export_format": "rtf"}},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_page_size_rejected(auth_client_factory):
    """default_page_size outside letter/A4 is a 422."""
    client = await auth_client_factory()

    response = await client.patch(
        "/api/v1/users/me",
        json={"preferences": {"default_page_size": "legal"}},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("interval,expected_status", [(2, 422), (3, 200), (30, 200), (31, 422)])
async def test_auto_save_interval_bounds(auth_client_factory, interval, expected_status):
    """auto_save_interval must be within 3-30 seconds inclusive."""
    client = await auth_client_factory()

    response = await client.patch(
        "/api/v1/users/me",
        json={"preferences": {"auto_save_interval": interval}},
    )

    assert response.status_code == expected_status


@pytest.mark.asyncio
async def test_invalid_preference_values(auth_client_factory):
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

    client = await auth_client_factory()

    # Make the request to update preferences
    response = await client.patch("/api/v1/users/me", json=invalid_update)

    # Assert validation error
    assert response.status_code == 422
    data = response.json()

    # Verify response indicates validation error
    assert "detail" in data
