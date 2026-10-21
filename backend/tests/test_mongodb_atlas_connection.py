"""
Test MongoDB Atlas SSL/TLS connection with Python 3.13+

This test verifies that the certifi-based SSL/TLS configuration
works correctly for MongoDB Atlas connections.
"""
import pytest
from pymongo import AsyncMongoClient
import certifi
import os
import ssl


@pytest.mark.asyncio
async def test_mongodb_atlas_connection_with_ssl():
    """
    Test that MongoDB Atlas connections work with SSL/TLS configuration.

    This test validates:
    1. certifi package provides valid CA certificates
    2. The async client can connect with TLS settings
    3. Basic database operations work over SSL
    """
    # Get connection URL from environment
    # If DATABASE_URL is a local connection, skip this test
    database_url = os.getenv("DATABASE_URL", "")

    if not database_url.startswith("mongodb+srv://"):
        pytest.skip("Skipping Atlas test - not using mongodb+srv:// connection")

    # Create client with SSL/TLS configuration (same as base.py)
    client = AsyncMongoClient(
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
        await client.close()


@pytest.mark.asyncio
async def test_certifi_ca_bundle_exists():
    """Verify certifi CA bundle is accessible."""
    ca_bundle_path = certifi.where()
    assert os.path.exists(ca_bundle_path), f"CA bundle not found at {ca_bundle_path}"
    assert os.path.isfile(ca_bundle_path), f"CA bundle is not a file: {ca_bundle_path}"

    # The bundle is one TLS will actually accept, with a plausible number of
    # roots in it. This used to look for "BEGIN CERTIFICATE" in the file's first
    # 500 characters, which stopped being true when certifi 2026 put a root with
    # a longer comment block first (#821), though the bundle was as valid as ever.
    context = ssl.create_default_context(cafile=ca_bundle_path)
    assert len(context.get_ca_certs()) > 50, "CA bundle loaded almost no roots"


def test_ssl_configuration_parameters():
    """Verify SSL configuration parameters are correct."""
    from app.db.base import _client

    # Verify client was created successfully
    assert _client is not None, "MongoDB client not initialized"

    # Verify client has proper timeout settings
    assert _client.options.server_selection_timeout == 30.0, "Server selection timeout incorrect"
