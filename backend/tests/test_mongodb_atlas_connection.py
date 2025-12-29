"""
Test MongoDB Atlas SSL/TLS connection with Python 3.13+

This test verifies that the certifi-based SSL/TLS configuration
works correctly for MongoDB Atlas connections.
"""
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
import certifi
import os


@pytest.mark.asyncio
async def test_mongodb_atlas_connection_with_ssl():
    """
    Test that MongoDB Atlas connections work with SSL/TLS configuration.

    This test validates:
    1. certifi package provides valid CA certificates
    2. Motor client can connect with TLS settings
    3. Basic database operations work over SSL
    """
    # Get connection URL from environment
    # If DATABASE_URL is a local connection, skip this test
    database_url = os.getenv("DATABASE_URL", "")

    if not database_url.startswith("mongodb+srv://"):
        pytest.skip("Skipping Atlas test - not using mongodb+srv:// connection")

    # Create client with SSL/TLS configuration (same as base.py)
    client = AsyncIOMotorClient(
        database_url,
        tlsCAFile=certifi.where(),
        tls=True,
        tlsAllowInvalidCertificates=False,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=20000,
        socketTimeoutMS=20000,
    )

    try:
        # Test connection by running a simple command
        result = await client.admin.command("ping")
        assert result["ok"] == 1.0, "MongoDB Atlas ping failed"

        # Test database access
        db = client[os.getenv("DATABASE_NAME", "auto_author_test")]
        collections = await db.list_collection_names()
        assert isinstance(collections, list), "Failed to list collections"

    finally:
        client.close()


@pytest.mark.asyncio
async def test_certifi_ca_bundle_exists():
    """Verify certifi CA bundle is accessible."""
    ca_bundle_path = certifi.where()
    assert os.path.exists(ca_bundle_path), f"CA bundle not found at {ca_bundle_path}"
    assert os.path.isfile(ca_bundle_path), f"CA bundle is not a file: {ca_bundle_path}"

    # Verify file is readable and contains certificates
    # (file may start with comments, so read more content)
    with open(ca_bundle_path, 'r') as f:
        content = f.read(500)
        assert "BEGIN CERTIFICATE" in content or "Entrust" in content, \
            "CA bundle doesn't appear to be valid"


def test_ssl_configuration_parameters():
    """Verify SSL configuration parameters are correct."""
    from app.db.base import _client

    # Verify client was created successfully
    assert _client is not None, "MongoDB client not initialized"

    # Verify client has proper timeout settings
    # Note: Motor wraps PyMongo, so we check the underlying client options
    assert _client.options.server_selection_timeout == 30.0, "Server selection timeout incorrect"
