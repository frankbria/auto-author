import pytest
from fastapi.testclient import TestClient
from app.main import app
import asyncio


@pytest.fixture(scope="session")
def client():
    """
    Create a TestClient instance that will be used for all tests.
    """
    return TestClient(app)


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop that can be used for asyncio tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
