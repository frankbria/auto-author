import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """
    Test that the root endpoint returns a 200 status code and health check message.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "Auto Author" in response.json().get(
        "message", ""
    )  # Assuming the root returns a message field
