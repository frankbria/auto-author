"""
Comprehensive tests for Clerk webhook handlers.

Test Coverage Areas:
1. Webhook signature verification (valid, invalid, missing headers)
2. User lifecycle events (created, updated, deleted)
3. Idempotency and error handling
4. Edge cases (malformed payloads, missing data)

Target: 85%+ coverage for app.api.endpoints.webhooks
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import json
import base64
import hmac
import hashlib
from datetime import datetime, timezone
from fastapi import HTTPException, status
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db import base


pytestmark = pytest.mark.asyncio


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def webhook_secret():
    """Valid Clerk webhook secret in the format whsec_<base64>"""
    # Generate a test secret: "test_secret" -> base64
    secret_bytes = b"test_secret_key_for_webhooks"
    secret_base64 = base64.b64encode(secret_bytes).decode("utf-8")
    return f"whsec_{secret_base64}"


@pytest.fixture
def clerk_user_payload():
    """Valid Clerk user.created webhook payload"""
    return {
        "type": "user.created",
        "data": {
            "id": "user_2NxAa1pyy8THf937QUAhKR2tXCI",
            "email_addresses": [{"email_address": "newuser@example.com"}],
            "first_name": "John",
            "last_name": "Doe",
            "image_url": "https://example.com/avatar.jpg",
            "metadata": {"referral": "friend"},
        },
    }


@pytest.fixture
def clerk_user_updated_payload():
    """Valid Clerk user.updated webhook payload"""
    return {
        "type": "user.updated",
        "data": {
            "id": "user_2NxAa1pyy8THf937QUAhKR2tXCI",
            "email_addresses": [{"email_address": "updated@example.com"}],
            "first_name": "Jane",
            "last_name": "Smith",
            "image_url": "https://example.com/new-avatar.jpg",
            "metadata": {"premium": "true"},
        },
    }


@pytest.fixture
def clerk_user_deleted_payload():
    """Valid Clerk user.deleted webhook payload"""
    return {
        "type": "user.deleted",
        "data": {
            "id": "user_2NxAa1pyy8THf937QUAhKR2tXCI",
        },
    }


def generate_svix_signature(payload: dict, secret: str, msg_id: str = "msg_123", timestamp: str = "1234567890"):
    """
    Generate a valid Svix signature for webhook testing.

    Args:
        payload: The webhook payload dict
        secret: The webhook secret (whsec_xxx format)
        msg_id: The message ID (svix-id header)
        timestamp: The timestamp (svix-timestamp header)

    Returns:
        Tuple of (svix_id, svix_timestamp, svix_signature)
    """
    # Encode payload as JSON with compact formatting (no spaces after separators)
    # This matches how FastAPI/httpx serializes JSON
    payload_str = json.dumps(payload, separators=(',', ':'))

    # Extract secret bytes (remove "whsec_" prefix and decode base64)
    if secret.startswith("whsec_"):
        secret_bytes = base64.b64decode(secret[6:])
    else:
        secret_bytes = secret.encode("utf-8")

    # Create signed content
    signed_content = f"{msg_id}.{timestamp}.{payload_str}"

    # Generate HMAC signature
    h = hmac.new(secret_bytes, signed_content.encode("utf-8"), hashlib.sha256)
    signature_bytes = h.digest()
    signature_b64 = base64.b64encode(signature_bytes).decode("utf-8")

    # Format as Svix signature (v1,<signature>)
    svix_signature = f"v1,{signature_b64}"

    return msg_id, timestamp, svix_signature


@pytest_asyncio.fixture
async def webhook_client(motor_reinit_db):
    """
    AsyncClient for webhook testing with database setup.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ============================================================================
# Signature Verification Tests
# ============================================================================


async def test_webhook_valid_signature(webhook_client, webhook_secret, clerk_user_payload, monkeypatch):
    """Test webhook with valid Svix signature is accepted"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    # Generate valid signature
    msg_id, timestamp, signature = generate_svix_signature(clerk_user_payload, webhook_secret)

    # Mock database operations (patch where they're used, not where they're defined)
    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.endpoints.webhooks.create_user", new_callable=AsyncMock) as mock_create_user:

        mock_get_user.return_value = None  # User doesn't exist

        response = await webhook_client.post(
            "/api/v1/webhooks/clerk",
            json=clerk_user_payload,
            headers={
                "svix-id": msg_id,
                "svix-timestamp": timestamp,
                "svix-signature": signature,
            },
        )

    assert response.status_code == 200
    assert "Processed user.created event successfully" in response.json()["message"]


async def test_webhook_invalid_signature(webhook_client, webhook_secret, clerk_user_payload, monkeypatch):
    """Test webhook with invalid signature is rejected"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    # Use incorrect signature
    invalid_signature = "v1,invalid_signature_base64"

    response = await webhook_client.post(
        "/api/v1/webhooks/clerk",
        json=clerk_user_payload,
        headers={
            "svix-id": "msg_123",
            "svix-timestamp": "1234567890",
            "svix-signature": invalid_signature,
        },
    )

    assert response.status_code == 401
    assert "Invalid webhook signature" in response.json()["detail"]


async def test_webhook_missing_svix_id(webhook_client, webhook_secret, clerk_user_payload, monkeypatch):
    """Test webhook with missing svix-id header is rejected"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    response = await webhook_client.post(
        "/api/v1/webhooks/clerk",
        json=clerk_user_payload,
        headers={
            "svix-timestamp": "1234567890",
            "svix-signature": "v1,signature",
        },
    )

    assert response.status_code == 401
    assert "Missing required Svix headers" in response.json()["detail"]


async def test_webhook_missing_timestamp(webhook_client, webhook_secret, clerk_user_payload, monkeypatch):
    """Test webhook with missing svix-timestamp header is rejected"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    response = await webhook_client.post(
        "/api/v1/webhooks/clerk",
        json=clerk_user_payload,
        headers={
            "svix-id": "msg_123",
            "svix-signature": "v1,signature",
        },
    )

    assert response.status_code == 401
    assert "Missing required Svix headers" in response.json()["detail"]


async def test_webhook_missing_signature(webhook_client, webhook_secret, clerk_user_payload, monkeypatch):
    """Test webhook with missing svix-signature header is rejected"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    response = await webhook_client.post(
        "/api/v1/webhooks/clerk",
        json=clerk_user_payload,
        headers={
            "svix-id": "msg_123",
            "svix-timestamp": "1234567890",
        },
    )

    assert response.status_code == 401
    assert "Missing required Svix headers" in response.json()["detail"]


async def test_webhook_no_secret_configured(webhook_client, clerk_user_payload, monkeypatch):
    """Test webhook fails when CLERK_WEBHOOK_SECRET is not configured"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", "")

    response = await webhook_client.post(
        "/api/v1/webhooks/clerk",
        json=clerk_user_payload,
        headers={
            "svix-id": "msg_123",
            "svix-timestamp": "1234567890",
            "svix-signature": "v1,signature",
        },
    )

    assert response.status_code == 500
    assert "Webhook secret not configured" in response.json()["detail"]


async def test_webhook_signature_replay_different_timestamp(webhook_client, webhook_secret, clerk_user_payload, monkeypatch):
    """Test that signature verification fails when timestamp changes (replay attack prevention)"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    # Generate signature with original timestamp
    msg_id, original_timestamp, signature = generate_svix_signature(clerk_user_payload, webhook_secret, timestamp="1234567890")

    # Try to use signature with different timestamp (replay attack)
    different_timestamp = "9999999999"

    response = await webhook_client.post(
        "/api/v1/webhooks/clerk",
        json=clerk_user_payload,
        headers={
            "svix-id": msg_id,
            "svix-timestamp": different_timestamp,  # Changed timestamp
            "svix-signature": signature,  # Original signature
        },
    )

    assert response.status_code == 401
    assert "Invalid webhook signature" in response.json()["detail"]


async def test_webhook_signature_multiple_versions(webhook_client, webhook_secret, clerk_user_payload, monkeypatch):
    """Test webhook accepts signature when multiple versions are provided (v1 and v2)"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    # Generate valid v1 signature
    msg_id, timestamp, valid_signature = generate_svix_signature(clerk_user_payload, webhook_secret)

    # Svix can send multiple signature versions: "v1,sig1 v2,sig2"
    multi_version_signature = f"{valid_signature} v2,invalid_signature_for_v2"

    # Mock database operations
    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.endpoints.webhooks.create_user", new_callable=AsyncMock) as mock_create_user:

        mock_get_user.return_value = None

        response = await webhook_client.post(
            "/api/v1/webhooks/clerk",
            json=clerk_user_payload,
            headers={
                "svix-id": msg_id,
                "svix-timestamp": timestamp,
                "svix-signature": multi_version_signature,
            },
        )

    # Should succeed because v1 signature is valid
    assert response.status_code == 200


async def test_webhook_signature_without_whsec_prefix(webhook_client, clerk_user_payload, monkeypatch):
    """Test webhook signature verification with plain secret (no whsec_ prefix)"""
    from app.core.config import settings

    # Use plain secret without whsec_ prefix
    plain_secret = "plain_secret_key"
    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", plain_secret)

    # Generate signature with plain secret
    msg_id, timestamp, signature = generate_svix_signature(clerk_user_payload, plain_secret)

    # Mock database operations
    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.endpoints.webhooks.create_user", new_callable=AsyncMock) as mock_create_user:

        mock_get_user.return_value = None

        response = await webhook_client.post(
            "/api/v1/webhooks/clerk",
            json=clerk_user_payload,
            headers={
                "svix-id": msg_id,
                "svix-timestamp": timestamp,
                "svix-signature": signature,
            },
        )

    assert response.status_code == 200


# ============================================================================
# User.Created Event Tests
# ============================================================================


async def test_user_created_event(webhook_client, webhook_secret, clerk_user_payload, monkeypatch):
    """Test successful user.created event creates new user in database"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    msg_id, timestamp, signature = generate_svix_signature(clerk_user_payload, webhook_secret)

    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.endpoints.webhooks.create_user", new_callable=AsyncMock) as mock_create_user:

        mock_get_user.return_value = None  # User doesn't exist
        mock_create_user.return_value = None

        response = await webhook_client.post(
            "/api/v1/webhooks/clerk",
            json=clerk_user_payload,
            headers={
                "svix-id": msg_id,
                "svix-timestamp": timestamp,
                "svix-signature": signature,
            },
        )

        assert response.status_code == 200

        # Verify create_user was called
        mock_create_user.assert_called_once()
        user_data = mock_create_user.call_args[0][0]
        assert user_data["clerk_id"] == "user_2NxAa1pyy8THf937QUAhKR2tXCI"
        assert user_data["email"] == "newuser@example.com"
        assert user_data["first_name"] == "John"
        assert user_data["last_name"] == "Doe"


async def test_user_created_idempotency(webhook_client, webhook_secret, clerk_user_payload, monkeypatch):
    """Test user.created event is idempotent (doesn't create duplicate if user exists)"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    msg_id, timestamp, signature = generate_svix_signature(clerk_user_payload, webhook_secret)

    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.endpoints.webhooks.create_user", new_callable=AsyncMock) as mock_create_user:

        # User already exists
        mock_get_user.return_value = {"clerk_id": "user_2NxAa1pyy8THf937QUAhKR2tXCI"}

        response = await webhook_client.post(
            "/api/v1/webhooks/clerk",
            json=clerk_user_payload,
            headers={
                "svix-id": msg_id,
                "svix-timestamp": timestamp,
                "svix-signature": signature,
            },
        )

        assert response.status_code == 200

        # Verify create_user was NOT called (idempotency)
        mock_create_user.assert_not_called()


async def test_user_created_no_email(webhook_client, webhook_secret, monkeypatch):
    """Test user.created event handles missing email gracefully"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    # Payload without email_addresses
    payload = {
        "type": "user.created",
        "data": {
            "id": "user_no_email",
            "email_addresses": [],  # Empty email addresses
            "first_name": "NoEmail",
            "last_name": "User",
            "metadata": {},
        },
    }

    msg_id, timestamp, signature = generate_svix_signature(payload, webhook_secret)

    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.endpoints.webhooks.create_user", new_callable=AsyncMock) as mock_create_user:

        mock_get_user.return_value = None

        response = await webhook_client.post(
            "/api/v1/webhooks/clerk",
            json=payload,
            headers={
                "svix-id": msg_id,
                "svix-timestamp": timestamp,
                "svix-signature": signature,
            },
        )

        assert response.status_code == 200

        # Verify user was created with None email
        mock_create_user.assert_called_once()
        user_data = mock_create_user.call_args[0][0]
        assert user_data["email"] is None


async def test_user_created_missing_email_addresses_field(webhook_client, webhook_secret, monkeypatch):
    """Test user.created event handles completely missing email_addresses field"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    # Payload without email_addresses field at all
    payload = {
        "type": "user.created",
        "data": {
            "id": "user_no_email_field",
            "first_name": "NoEmail",
            "last_name": "User",
            "metadata": {},
        },
    }

    msg_id, timestamp, signature = generate_svix_signature(payload, webhook_secret)

    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.endpoints.webhooks.create_user", new_callable=AsyncMock) as mock_create_user:

        mock_get_user.return_value = None

        response = await webhook_client.post(
            "/api/v1/webhooks/clerk",
            json=payload,
            headers={
                "svix-id": msg_id,
                "svix-timestamp": timestamp,
                "svix-signature": signature,
            },
        )

        assert response.status_code == 200

        # Verify user was created with None email
        mock_create_user.assert_called_once()
        user_data = mock_create_user.call_args[0][0]
        assert user_data["email"] is None


# ============================================================================
# User.Updated Event Tests
# ============================================================================


async def test_user_updated_event(webhook_client, webhook_secret, clerk_user_updated_payload, monkeypatch):
    """Test successful user.updated event updates existing user"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    msg_id, timestamp, signature = generate_svix_signature(clerk_user_updated_payload, webhook_secret)

    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.endpoints.webhooks.update_user", new_callable=AsyncMock) as mock_update_user:

        # User exists
        mock_get_user.return_value = {"clerk_id": "user_2NxAa1pyy8THf937QUAhKR2tXCI"}

        response = await webhook_client.post(
            "/api/v1/webhooks/clerk",
            json=clerk_user_updated_payload,
            headers={
                "svix-id": msg_id,
                "svix-timestamp": timestamp,
                "svix-signature": signature,
            },
        )

        assert response.status_code == 200

        # Verify update_user was called
        mock_update_user.assert_called_once()
        clerk_id, update_data = mock_update_user.call_args[0]
        assert clerk_id == "user_2NxAa1pyy8THf937QUAhKR2tXCI"
        assert update_data["email"] == "updated@example.com"
        assert update_data["first_name"] == "Jane"
        assert update_data["last_name"] == "Smith"


async def test_user_updated_user_not_exists(webhook_client, webhook_secret, clerk_user_updated_payload, monkeypatch):
    """Test user.updated event does nothing if user doesn't exist"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    msg_id, timestamp, signature = generate_svix_signature(clerk_user_updated_payload, webhook_secret)

    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.endpoints.webhooks.update_user", new_callable=AsyncMock) as mock_update_user:

        # User doesn't exist
        mock_get_user.return_value = None

        response = await webhook_client.post(
            "/api/v1/webhooks/clerk",
            json=clerk_user_updated_payload,
            headers={
                "svix-id": msg_id,
                "svix-timestamp": timestamp,
                "svix-signature": signature,
            },
        )

        assert response.status_code == 200

        # Verify update_user was NOT called
        mock_update_user.assert_not_called()


async def test_user_updated_no_email(webhook_client, webhook_secret, monkeypatch):
    """Test user.updated event handles missing email gracefully"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    payload = {
        "type": "user.updated",
        "data": {
            "id": "user_2NxAa1pyy8THf937QUAhKR2tXCI",
            "email_addresses": [],
            "first_name": "Updated",
            "last_name": "Name",
            "metadata": {},
        },
    }

    msg_id, timestamp, signature = generate_svix_signature(payload, webhook_secret)

    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.endpoints.webhooks.update_user", new_callable=AsyncMock) as mock_update_user:

        mock_get_user.return_value = {"clerk_id": "user_2NxAa1pyy8THf937QUAhKR2tXCI"}

        response = await webhook_client.post(
            "/api/v1/webhooks/clerk",
            json=payload,
            headers={
                "svix-id": msg_id,
                "svix-timestamp": timestamp,
                "svix-signature": signature,
            },
        )

        assert response.status_code == 200

        # Verify update was called with None email
        mock_update_user.assert_called_once()
        _, update_data = mock_update_user.call_args[0]
        assert update_data["email"] is None


# ============================================================================
# User.Deleted Event Tests
# ============================================================================


async def test_user_deleted_event(webhook_client, webhook_secret, clerk_user_deleted_payload, monkeypatch):
    """Test successful user.deleted event deletes user from database"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    msg_id, timestamp, signature = generate_svix_signature(clerk_user_deleted_payload, webhook_secret)

    with patch("app.api.endpoints.webhooks.delete_user", new_callable=AsyncMock) as mock_delete_user:
        mock_delete_user.return_value = None

        response = await webhook_client.post(
            "/api/v1/webhooks/clerk",
            json=clerk_user_deleted_payload,
            headers={
                "svix-id": msg_id,
                "svix-timestamp": timestamp,
                "svix-signature": signature,
            },
        )

        assert response.status_code == 200

        # Verify delete_user was called
        mock_delete_user.assert_called_once_with("user_2NxAa1pyy8THf937QUAhKR2tXCI")


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================


async def test_unknown_event_type(webhook_client, webhook_secret, monkeypatch):
    """Test webhook handles unknown event types gracefully"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    payload = {
        "type": "user.unknown_event",
        "data": {"id": "user_123"},
    }

    msg_id, timestamp, signature = generate_svix_signature(payload, webhook_secret)

    response = await webhook_client.post(
        "/api/v1/webhooks/clerk",
        json=payload,
        headers={
            "svix-id": msg_id,
            "svix-timestamp": timestamp,
            "svix-signature": signature,
        },
    )

    # Should succeed but do nothing
    assert response.status_code == 200
    assert "Processed user.unknown_event event successfully" in response.json()["message"]


async def test_malformed_json_payload(webhook_client, webhook_secret, monkeypatch):
    """Test webhook handles malformed JSON gracefully"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    # Send invalid JSON
    response = await webhook_client.post(
        "/api/v1/webhooks/clerk",
        content=b"invalid json {{{",
        headers={
            "svix-id": "msg_123",
            "svix-timestamp": "1234567890",
            "svix-signature": "v1,signature",
            "content-type": "application/json",
        },
    )

    # Should fail validation before signature check
    assert response.status_code == 422 or response.status_code == 401


async def test_missing_event_type(webhook_client, webhook_secret, monkeypatch):
    """Test webhook handles payload without event type"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    payload = {
        "data": {"id": "user_123"},
        # Missing "type" field
    }

    msg_id, timestamp, signature = generate_svix_signature(payload, webhook_secret)

    response = await webhook_client.post(
        "/api/v1/webhooks/clerk",
        json=payload,
        headers={
            "svix-id": msg_id,
            "svix-timestamp": timestamp,
            "svix-signature": signature,
        },
    )

    # Should succeed (event_type will be None, no handler matches)
    assert response.status_code == 200


async def test_database_error_on_create(webhook_client, webhook_secret, clerk_user_payload, monkeypatch):
    """Test webhook handles database errors during user creation"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    msg_id, timestamp, signature = generate_svix_signature(clerk_user_payload, webhook_secret)

    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.endpoints.webhooks.create_user", new_callable=AsyncMock) as mock_create_user:

        mock_get_user.return_value = None
        # Simulate database error
        mock_create_user.side_effect = Exception("Database connection failed")

        # TestClient raises the exception directly
        with pytest.raises(Exception, match="Database connection failed"):
            await webhook_client.post(
                "/api/v1/webhooks/clerk",
                json=clerk_user_payload,
                headers={
                    "svix-id": msg_id,
                    "svix-timestamp": timestamp,
                    "svix-signature": signature,
                },
            )


async def test_database_error_on_update(webhook_client, webhook_secret, clerk_user_updated_payload, monkeypatch):
    """Test webhook handles database errors during user update"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    msg_id, timestamp, signature = generate_svix_signature(clerk_user_updated_payload, webhook_secret)

    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.endpoints.webhooks.update_user", new_callable=AsyncMock) as mock_update_user:

        mock_get_user.return_value = {"clerk_id": "user_2NxAa1pyy8THf937QUAhKR2tXCI"}
        # Simulate database error
        mock_update_user.side_effect = Exception("Database update failed")

        with pytest.raises(Exception, match="Database update failed"):
            await webhook_client.post(
                "/api/v1/webhooks/clerk",
                json=clerk_user_updated_payload,
                headers={
                    "svix-id": msg_id,
                    "svix-timestamp": timestamp,
                    "svix-signature": signature,
                },
            )


async def test_database_error_on_delete(webhook_client, webhook_secret, clerk_user_deleted_payload, monkeypatch):
    """Test webhook handles database errors during user deletion"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    msg_id, timestamp, signature = generate_svix_signature(clerk_user_deleted_payload, webhook_secret)

    with patch("app.api.endpoints.webhooks.delete_user", new_callable=AsyncMock) as mock_delete_user:
        # Simulate database error
        mock_delete_user.side_effect = Exception("Database delete failed")

        with pytest.raises(Exception, match="Database delete failed"):
            await webhook_client.post(
                "/api/v1/webhooks/clerk",
                json=clerk_user_deleted_payload,
                headers={
                    "svix-id": msg_id,
                    "svix-timestamp": timestamp,
                    "svix-signature": signature,
                },
            )


async def test_empty_data_field(webhook_client, webhook_secret, monkeypatch):
    """Test webhook handles empty data field"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    payload = {
        "type": "user.created",
        "data": {},  # Empty data - missing 'id' field
    }

    msg_id, timestamp, signature = generate_svix_signature(payload, webhook_secret)

    # This should fail during user creation due to missing required 'id' field
    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = None

        # Should raise KeyError for missing 'id' field
        with pytest.raises(KeyError, match="id"):
            await webhook_client.post(
                "/api/v1/webhooks/clerk",
                json=payload,
                headers={
                    "svix-id": msg_id,
                    "svix-timestamp": timestamp,
                    "svix-signature": signature,
                },
            )


async def test_large_payload(webhook_client, webhook_secret, monkeypatch):
    """Test webhook handles large payloads"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "CLERK_WEBHOOK_SECRET", webhook_secret)

    # Create large metadata
    large_metadata = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

    payload = {
        "type": "user.created",
        "data": {
            "id": "user_large_payload",
            "email_addresses": [{"email_address": "large@example.com"}],
            "first_name": "Large",
            "last_name": "Payload",
            "metadata": large_metadata,
        },
    }

    msg_id, timestamp, signature = generate_svix_signature(payload, webhook_secret)

    with patch("app.api.endpoints.webhooks.get_user_by_clerk_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.endpoints.webhooks.create_user", new_callable=AsyncMock) as mock_create_user:

        mock_get_user.return_value = None

        response = await webhook_client.post(
            "/api/v1/webhooks/clerk",
            json=payload,
            headers={
                "svix-id": msg_id,
                "svix-timestamp": timestamp,
                "svix-signature": signature,
            },
        )

        # Should handle large payload successfully
        assert response.status_code == 200
        mock_create_user.assert_called_once()
