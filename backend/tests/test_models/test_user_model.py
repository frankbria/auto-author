import pytest
from app.models.user import User
from unittest.mock import patch
import pytest_asyncio


@pytest.fixture
def user_data():
    """
    Sample user data for testing
    """
    return {
        "clerk_id": "clerk_user_123",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "role": "user",
        "profile_image_url": "https://example.com/image.jpg",
    }


@pytest.mark.asyncio
async def test_user_creation(user_data):
    """
    Test user model creation with valid data
    """
    # Create a user instance
    user = User(**user_data)

    # Verify user attributes
    assert user.clerk_id == user_data["clerk_id"]
    assert user.email == user_data["email"]
    assert user.first_name == user_data["first_name"]
    assert user.last_name == user_data["last_name"]
    assert user.role == user_data["role"]
    assert user.profile_image_url == user_data["profile_image_url"]
