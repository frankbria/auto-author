"""
Tests for health check endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure


def test_health_check_basic(client: TestClient):
    """Test basic health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_check_healthy(client: TestClient):
    """Test readiness check when all dependencies are healthy."""
    response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert "mongodb" in data["checks"]
    assert data["checks"]["mongodb"]["status"] == "ready"
    assert "response_time_ms" in data["checks"]["mongodb"]


@pytest.mark.asyncio
async def test_readiness_check_mongodb_down(client: TestClient):
    """Test readiness check when MongoDB is down."""
    with patch("app.api.health._client.admin.command") as mock_command:
        mock_command.side_effect = ServerSelectionTimeoutError("MongoDB timeout")

        response = client.get("/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["status"] == "not_ready"
        assert "mongodb" in data["detail"]["checks"]
        assert data["detail"]["checks"]["mongodb"]["status"] == "not_ready"


@pytest.mark.asyncio
async def test_readiness_check_database_operations_fail(client: TestClient):
    """Test readiness check when database operations fail."""
    with patch("app.api.health._db.command") as mock_command:
        mock_command.side_effect = ConnectionFailure("Database operations failed")

        response = client.get("/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["status"] == "not_ready"
        assert "database_operations" in data["detail"]["checks"]
        assert data["detail"]["checks"]["database_operations"]["status"] == "not_ready"


def test_liveness_check(client: TestClient):
    """Test liveness check endpoint."""
    response = client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] > 0


@pytest.mark.asyncio
async def test_detailed_health_check_authenticated(client: TestClient, auth_headers: dict):
    """Test detailed health check with authentication."""
    response = client.get("/health/detailed", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "healthy_with_warnings"]
    assert "checks" in data

    # Check MongoDB info
    assert "mongodb" in data["checks"]
    assert "version" in data["checks"]["mongodb"]

    # Check database info
    assert "database" in data["checks"]
    assert "collections" in data["checks"]["database"]

    # Check system resources
    assert "system_resources" in data["checks"]
    assert "cpu_percent" in data["checks"]["system_resources"]
    assert "memory_percent" in data["checks"]["system_resources"]
    assert "disk_percent" in data["checks"]["system_resources"]

    # Check application info
    assert "application" in data["checks"]
    assert "uptime_seconds" in data["checks"]["application"]


def test_detailed_health_check_unauthenticated(client: TestClient):
    """Test detailed health check without authentication."""
    response = client.get("/health/detailed")

    assert response.status_code == 401
    data = response.json()
    assert "Authentication required" in data["detail"]


@pytest.mark.asyncio
async def test_detailed_health_check_with_warnings(client: TestClient, auth_headers: dict):
    """Test detailed health check with system warnings."""
    with patch("app.api.health.psutil") as mock_psutil:
        # Mock high memory usage
        mock_memory = Mock()
        mock_memory.percent = 95
        mock_memory.total = 16 * 1024**3  # 16 GB
        mock_memory.used = int(16 * 1024**3 * 0.95)
        mock_psutil.virtual_memory.return_value = mock_memory

        # Mock high disk usage
        mock_disk = Mock()
        mock_disk.percent = 92
        mock_disk.total = 100 * 1024**3  # 100 GB
        mock_disk.used = int(100 * 1024**3 * 0.92)
        mock_disk.free = int(100 * 1024**3 * 0.08)
        mock_psutil.disk_usage.return_value = mock_disk

        # Mock CPU
        mock_psutil.cpu_percent.return_value = 45

        response = client.get("/health/detailed", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy_with_warnings"
        assert "warnings" in data
        assert any("memory" in w.lower() for w in data["warnings"])
        assert any("disk" in w.lower() for w in data["warnings"])


@pytest.mark.asyncio
async def test_detailed_health_check_degraded(client: TestClient, auth_headers: dict):
    """Test detailed health check when service is degraded."""
    with patch("app.api.health._client.server_info") as mock_server_info:
        mock_server_info.side_effect = ConnectionFailure("MongoDB connection error")

        response = client.get("/health/detailed", headers=auth_headers)

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["status"] in ["degraded", "degraded_with_warnings"]
        assert "mongodb" in data["detail"]["checks"]
        assert data["detail"]["checks"]["mongodb"]["status"] == "error"


def test_format_uptime():
    """Test uptime formatting."""
    from app.api.health import _format_uptime

    assert _format_uptime(30) == "30s"
    assert _format_uptime(90) == "1m 30s"
    assert _format_uptime(3661) == "1h 1m 1s"
    assert _format_uptime(90061) == "1d 1h 1m 1s"
    assert _format_uptime(0) == "0s"


@pytest.mark.asyncio
async def test_readiness_check_slow_response(client: TestClient):
    """Test readiness check with slow MongoDB response."""
    async def slow_command(*args, **kwargs):
        import asyncio
        await asyncio.sleep(0.2)  # 200ms
        return {"ok": 1}

    with patch("app.api.health._client.admin.command", side_effect=slow_command):
        response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["checks"]["mongodb"]["response_time_ms"] > 100


@pytest.mark.asyncio
async def test_detailed_health_connection_pool_stats(client: TestClient, auth_headers: dict):
    """Test detailed health check includes connection pool stats."""
    response = client.get("/health/detailed", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "mongodb" in data["checks"]
    assert "pool_config" in data["checks"]["mongodb"]
    assert data["checks"]["mongodb"]["pool_config"]["max_pool_size"] == 50
    assert data["checks"]["mongodb"]["pool_config"]["min_pool_size"] == 10
