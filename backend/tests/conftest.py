import app.api.dependencies as deps
from fastapi import Request


def fake_get_rate_limiter(limit: int = 10, window: int = 60):
    """
    Fake rate limiter that does nothing.
    This is used to bypass rate limiting in tests.
    """

    async def _always_allow(request: Request):
        return {"limit": float("inf"), "remaining": float("inf"), "reset": None}

    return _always_allow


deps.get_rate_limiter = fake_get_rate_limiter
import pytest, pytest_asyncio
from httpx import AsyncClient, ASGITransport
import mongomock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app
from app.db import base
import app.db.user as user_dao
import app.db.book as book_dao
import app.db.audit_log as audit_log_dao
from app.api.dependencies import verify_jwt_token
import app.core.security as sec

import asyncio
from datetime import datetime, timezone
from app.core.security import get_current_user
from app.api.endpoints import users as users_endpoint
from app.api.endpoints import books as books_endpoint
from bson import ObjectId


class AsyncCollection:
    def __init__(self, sync_coll):
        self._coll = sync_coll

    async def insert_one(self, doc):
        return self._coll.insert_one(doc)

    async def update_one(self, *args, **kwargs):
        return self._coll.update_one(*args, **kwargs)

    async def find_one(self, *args, **kwargs):
        return self._coll.find_one(*args, **kwargs)

    async def delete_one(self, *args, **kwargs):
        return self._coll.delete_one(*args, **kwargs)

    async def find_one_and_update(self, *args, **kwargs):
        return self._coll.find_one_and_update(*args, **kwargs)

    async def delete_many(self, *args, **kwargs):
        return self._coll.delete_many(*args, **kwargs)


@pytest.fixture(scope="session")
def client():
    """
    Create a TestClient instance that will be used for all tests.
    """
    return TestClient(app)


@pytest.fixture(scope="function")
def event_loop():
    """
    Create a fresh event loop for each test function that can be used for asyncio tests.
    Using function scope instead of session prevents 'Event loop is closed' errors
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # We need to close the loop properly to prevent 'Event loop is closed' errors in future tests
    # But we need to make sure all pending tasks are finished first
    try:
        # Cancel all pending tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # Run the loop until all tasks are done or cancelled
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except Exception:
        pass  # Ignore cleanup errors
    finally:
        loop.close()


@pytest.fixture(autouse=True)
def fake_mongo(monkeypatch):
    """
    Every test will see database.users_collection, database.books_collection and .audit_log_collection
    backed by mongomock in-memory collections.
    """
    sync_client = mongomock.MongoClient()
    sync_db = sync_client["test_db"]

    # Create single AsyncCollection instances that will be shared
    users_collection_wrapper = AsyncCollection(sync_db["users"])
    books_collection_wrapper = AsyncCollection(sync_db["books"])
    audit_logs_collection_wrapper = AsyncCollection(sync_db["audit_logs"])

    # patch the globals in your database module
    monkeypatch.setattr(base, "users_collection", users_collection_wrapper)
    monkeypatch.setattr(user_dao, "users_collection", users_collection_wrapper)
    monkeypatch.setattr(base, "audit_logs_collection", audit_logs_collection_wrapper)
    monkeypatch.setattr(
        audit_log_dao, "audit_logs_collection", audit_logs_collection_wrapper
    )
    monkeypatch.setattr(base, "books_collection", books_collection_wrapper)
    monkeypatch.setattr(book_dao, "books_collection", books_collection_wrapper)
    yield
    # Clean up: remove our override so other tests aren’t “authed”
    sync_client.drop_database("test_db")


@pytest.fixture
def test_user():
    return {
        "_id": "507f1f77bcf86cd799439011",
        "id": "507f1f77bcf86cd799439011",
        "clerk_id": "test_clerk_id",
        "email": "tester@example.com",
        "first_name": "Test",
        "last_name": "User",
        "display_name": "Tester",
        "avatar_url": None,
        "bio": "I am a test user",
        "role": "user",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "books": [],
        "preferences": {
            "theme": "light",
            "email_notifications": False,
            "marketing_emails": False,
        },
    }


@pytest.fixture
def fake_user():
    return {
        "_id": "123456",
        "id": "123456",
        "clerk_id": "fake_clerk_id",
        "email": "faker@example.com",
        "first_name": "Fake",
        "last_name": "User",
        "display_name": "Fake User",
        "avatar_url": None,
        "bio": "I am a fake user",
        "role": "user",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "books": [],
        "preferences": {
            "theme": "light",
            "email_notifications": False,
            "marketing_emails": False,
        },
    }


@pytest.fixture
def auth_client_factory(monkeypatch, test_user) -> callable:
    """
    Returns a function `make_client(overrides: dict = None)`
    that gives you a TestClient whose get_current_user
    always returns `test_user` updated with your overrides.
    """

    def make_client(*, overrides: dict = None, auth: bool = True):

        # 1) merge defaults and overrides
        user = test_user.copy()
        user["_id"] = ObjectId()  # brand new each time
        user["id"] = str(user["_id"])
        if overrides:
            user.update(overrides)

        # 2) Insert into our mongomock DB
        base.users_collection._coll.insert_one(user)

        # 3) Override the audit request
        async def _noop_audit_request(*args, **kwargs):
            return None

        monkeypatch.setattr(users_endpoint, "audit_request", _noop_audit_request)
        monkeypatch.setattr(books_endpoint, "audit_request", _noop_audit_request)

        if auth:
            # 4) Stub out JWT verification to return that clerk_id
            async def _fake_verify(token: str):
                return {"sub": user["clerk_id"]}

            monkeypatch.setattr(sec, "verify_jwt_token", _fake_verify)

        client = TestClient(app)

        if auth:
            client.headers.update({"Authorization": "Bearer aaa.bbb.ccc"})

        return client

    yield make_client
    # Finally: Clean up: remove our override so other tests aren’t “authed”
    app.dependency_overrides.clear()


@pytest.fixture
def mock_jwt_token():
    """
    Fixture to provide a mock JWT token for testing.
    This token is not valid and should not be used in production.
    """
    return "mock.jwt.token"


@pytest.fixture
def invalid_jwt_token():
    """
    Fixture to provide an invalid JWT token for testing.
    This token is intentionally malformed and should not be used in production.
    """
    return "invalid.jwt_token"


@pytest.fixture
def test_book(test_user):
    """
    Fixture to provide a test book object.
    """
    book_id = ObjectId()
    return {
        "_id": book_id,
        "id": str(book_id),
        "title": "Test Book",
        "subtitle": "A book for testing",
        "description": "This is a test book.",
        "genre": "Fiction",
        "target_audience": "Adults",
        "cover_image_url": None,
        "metadata": {},
        "owner_id": test_user["clerk_id"],
        "toc_items": [],
        "published": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest_asyncio.fixture
async def async_client_factory(monkeypatch, test_user):
    """
    Returns an async function make_client(overrides: dict = None, auth: bool = True)
    that yields an AsyncClient whose get_current_user always returns test_user
    (with optional overrides), and which writes into a mongomock test DB.
    """
    # keep track of every client we hand out
    created_clients = []

    def _seed_user(overrides: dict | None):
        # Clone the fixture user & assign a fresh ObjectId
        user = test_user.copy()
        user["_id"] = ObjectId()
        user["id"] = str(user["_id"])
        if overrides:
            user.update(overrides)
        # Directly insert into the underlying mongomock collection
        base.users_collection._coll.insert_one(user)
        return user

    async def make_client(*, overrides: dict | None = None, auth: bool = True):
        # 1) Seed a new user
        user = _seed_user(overrides)

        # 2) Stub out audit_request in both endpoints
        async def _noop_audit(*args, **kwargs):
            return None

        monkeypatch.setattr(users_endpoint, "audit_request", _noop_audit)
        monkeypatch.setattr(books_endpoint, "audit_request", _noop_audit)

        # 3) If you want authentication, stub verify_jwt_token to return our user's sub
        headers = {}
        if auth:

            async def _fake_verify(token: str):
                return {"sub": user["clerk_id"]}

            monkeypatch.setattr(sec, "verify_jwt_token", _fake_verify)
            headers["Authorization"] = "Bearer dummy.token.here"

        # 4) Create an AsyncClient that drives our FastAPI app
        client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers=headers,
        )
        created_clients.append(client)
        return client

    yield make_client

    # teardown: clear any dependency overrides you may have set
    for client in created_clients:
        try:
            await client.aclose()
        except Exception as e:
            print(f"Error closing client: {e}")

    # Clear any dependency overrides
    app.dependency_overrides.clear()
