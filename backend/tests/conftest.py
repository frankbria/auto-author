import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest
import pymongo


import app.api.dependencies as deps
from fastapi import Request
import motor.motor_asyncio
import app.db.user as users_dao
import app.db.book as books_dao
import app.db.audit_log as audit_log_dao
from app.db import base
from app import db


# Patch the DB connection for tests to use a real MongoDB instance
TEST_MONGO_URI = "mongodb://localhost:27017/auto-author-test"
_sync_client = pymongo.MongoClient(TEST_MONGO_URI)
_sync_db = _sync_client.get_default_database()
_sync_users = _sync_db.get_collection("users")
_sync_books = _sync_db.get_collection("books")
_sync_logs = _sync_db.get_collection("audit_logs")
_sync_sessions = _sync_db.get_collection("sessions")

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
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing import Dict, Optional
from app.main import app
import app.core.security as sec
import asyncio
from datetime import datetime, timezone
from app.core.security import get_current_user
from app.api.endpoints import users as users_endpoint
from app.api.endpoints import books as books_endpoint
from bson import ObjectId

pytest_plugins = ["pytest_asyncio"]

@pytest_asyncio.fixture(scope="function")
def event_loop():
    """
    Create a new event loop for each test function.
    This ensures Motor async clients have a proper event loop context.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(autouse=False)  # Not autouse - tests must explicitly request this fixture
def motor_reinit_db():
    """
    Every test gets its own Motor client bound to a fresh database.
    Drops the test DB before & after so you start with a clean slate.

    Note: This is a SYNC fixture (not async) because autouse=True fixtures
    need to work with both sync and async tests. Using async autouse fixtures
    with sync tests causes pytest-asyncio to hang.
    """
    # Drop database before test using sync client
    _sync_client.drop_database("auto-author-test")

    # Create async Motor client for test use
    base._client = motor.motor_asyncio.AsyncIOMotorClient(TEST_MONGO_URI)
    base._db = base._client.get_default_database()

    # Set up collections
    base.users_collection = base._db.get_collection("users")
    base.books_collection = base._db.get_collection("books")
    base.audit_logs_collection = base._db.get_collection("audit_logs")
    base.sessions_collection = base._db.get_collection("sessions")

    books_dao.books_collection = base.books_collection
    books_dao.users_collection = base.users_collection
    users_dao.users_collection = base.users_collection
    audit_log_dao.audit_logs_collection = base.audit_logs_collection

    yield

    # Drop database after test using sync client
    _sync_client.drop_database("auto-author-test")
    base._client.close()


@pytest.fixture(scope="function")
def client():
    """
    Create a TestClient instance that will be used for all tests.
    """
    return TestClient(app)


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


@pytest_asyncio.fixture(scope="function")
async def auth_client_factory(motor_reinit_db, monkeypatch, test_user):
    """
    Returns an async function `make_client(overrides: dict = None)`
    that gives you an AsyncClient whose get_current_user
    always returns `test_user` updated with your overrides.
    """
    created_clients = []

    def _seed_user(overrides: dict = None):
        user = test_user.copy()
        user["_id"] = ObjectId()  # brand new each time
        user["id"] = str(user["_id"])
        if overrides:
            user.update(overrides)
        _sync_users.insert_one(user)
        return user

    async def make_client(*, overrides: dict = None, auth: bool = True):
        user = _seed_user(overrides)

        # monkeypatch.setattr(db, "get_user_by_clerk_id", lambda: user["clerk_id"])

        async def _noop_audit_request(
            request: Request,
            current_user: Dict,
            action: str,
            resource_type: str,
            target_id: Optional[str] = None,
            **kwargs,
        ):
            return None

        monkeypatch.setattr(users_endpoint, "audit_request", _noop_audit_request)
        monkeypatch.setattr(books_endpoint, "audit_request", _noop_audit_request)

        headers = {}
        if auth:
            from app.core.security import get_current_user

            app.dependency_overrides[get_current_user] = lambda: user
            monkeypatch.setattr(
                users_dao, "get_user_by_clerk_id", lambda: user["clerk_id"]
            )

            async def _fake_verify(token: str):
                return {"sub": user["clerk_id"]}
            monkeypatch.setattr(sec, "verify_jwt_token", _fake_verify)
            headers["Authorization"] = "Bearer aaa.bbb.ccc"

        client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers=headers,
        )
        created_clients.append(client)
        return client

    yield make_client

    # await base.users_collection.delete_many({})  # Clean up test users
    _sync_users.drop()
    _sync_books.drop()
    _sync_logs.drop()
    for client in created_clients:
        try:
            await client.aclose()
        except Exception as e:
            print(f"Error closing client: {e}")
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


@pytest_asyncio.fixture(scope="function")
async def async_client_factory(motor_reinit_db, monkeypatch, test_user):
    """
    Returns an async function make_client(overrides: dict = None, auth: bool = True)
    that yields an AsyncClient whose get_current_user always returns test_user
    (with optional overrides), and which writes into a real MongoDB test DB.
    """
    created_clients = []

    def _seed_user(overrides: dict | None):
        user = test_user.copy()
        user["_id"] = ObjectId()
        user["id"] = str(user["_id"])
        if overrides:
            user.update(overrides)
        _sync_users.insert_one(user)
        return user

    async def make_client(*, overrides: dict | None = None, auth: bool = True):
        user = _seed_user(overrides)

        async def _noop_audit(*args, **kwargs):
            return None

        monkeypatch.setattr(users_endpoint, "audit_request", _noop_audit)
        monkeypatch.setattr(books_endpoint, "audit_request", _noop_audit)

        headers = {}
        if auth:
            from app.core.security import get_current_user

            app.dependency_overrides[get_current_user] = lambda: user
            monkeypatch.setattr(
                users_dao, "get_user_by_clerk_id", lambda: user["clerk_id"]
            )

            async def _fake_verify(token: str):
                return {"sub": user["clerk_id"]}
            monkeypatch.setattr(sec, "verify_jwt_token", _fake_verify)
            headers["Authorization"] = "Bearer dummy.token.here"

        client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers=headers,
        )
        created_clients.append(client)
        return client

    yield make_client
    # await base.users_collection.delete_many({})  # Clean up test users
    _sync_users.drop()
    _sync_books.drop()
    _sync_logs.drop()

    for client in created_clients:
        try:
            await client.aclose()
        except Exception as e:
            print(f"Error closing client: {e}")
    app.dependency_overrides.clear()


# REMOVED: clean_db fixture was redundant and conflicting with motor_reinit_db
# The motor_reinit_db fixture (line 67) already handles database cleanup before/after each test
# Having both autouse fixtures caused race conditions and test hangs
