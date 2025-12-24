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
from app.core.security import get_current_user_from_session
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
        "auth_id": "test-auth-id-123",
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
        "auth_id": "fake-auth-id-456",
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
    that gives you an AsyncClient whose get_current_user_from_session
    always returns `test_user` updated with your overrides.

    Authentication is mocked by overriding the get_current_user_from_session dependency.
    This simulates cookie-based session authentication without requiring actual session cookies.

    Multi-user support: When multiple clients are created with different users,
    the session token cookie is used to determine which user to return.
    """
    created_clients = []
    user_map = {}  # Map from session_token to user
    override_installed = False

    def _seed_user(overrides: dict = None):
        user = test_user.copy()
        user["_id"] = ObjectId()  # brand new each time
        user["id"] = str(user["_id"])
        if overrides:
            user.update(overrides)
        _sync_users.insert_one(user)
        return user

    async def make_client(*, overrides: dict = None, auth: bool = True):
        nonlocal override_installed
        from fastapi import Request as FastAPIRequest
        from app.core.security import get_current_user_from_session

        user = _seed_user(overrides)

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

        cookies = {}
        if auth:
            # Create unique session token for this user
            session_token = f"test-session-{user['auth_id']}"

            # Store user in map keyed by session token for multi-user tests
            user_map[session_token] = user

            # Only install the dependency override once
            # The override reads the session cookie to determine which user to return
            if not override_installed:
                async def _get_user_from_session(request: FastAPIRequest = None):
                    """Return test user based on session cookie (simulating cookie-based auth)."""
                    if request is None:
                        # If no request, return the first user in the map
                        if user_map:
                            return next(iter(user_map.values()))
                        return None

                    # Get session token from cookies
                    session_token = request.cookies.get("better-auth.session_token")
                    if session_token and session_token in user_map:
                        return user_map[session_token]

                    # Fallback: return first user (for backward compatibility)
                    if user_map:
                        return next(iter(user_map.values()))
                    return None

                app.dependency_overrides[get_current_user_from_session] = _get_user_from_session
                override_installed = True

            monkeypatch.setattr(
                users_dao, "get_user_by_auth_id", lambda auth_id: next(
                    (u for u in user_map.values() if u.get('auth_id') == auth_id), None
                )
            )

            # Set the session cookie with the user's unique token
            cookies["better-auth.session_token"] = session_token

        client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            cookies=cookies,
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
        "owner_id": test_user["auth_id"],
        "toc_items": [],
        "published": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest_asyncio.fixture(scope="function")
async def async_client_factory(motor_reinit_db, monkeypatch, test_user):
    """
    Returns an async function make_client(overrides: dict = None, auth: bool = True)
    that yields an AsyncClient whose get_current_user_from_session always returns test_user
    (with optional overrides), and which writes into a real MongoDB test DB.

    Authentication is mocked by overriding the get_current_user_from_session dependency.
    This simulates cookie-based session authentication.

    Multi-user support: When multiple clients are created with different users,
    the session token cookie is used to determine which user to return.
    """
    created_clients = []
    user_map = {}  # Map from session_token to user
    override_installed = False

    def _seed_user(overrides: dict | None):
        user = test_user.copy()
        user["_id"] = ObjectId()
        user["id"] = str(user["_id"])
        if overrides:
            user.update(overrides)
        _sync_users.insert_one(user)
        return user

    async def make_client(*, overrides: dict | None = None, auth: bool = True):
        nonlocal override_installed
        user = _seed_user(overrides)

        async def _noop_audit(*args, **kwargs):
            return None

        monkeypatch.setattr(users_endpoint, "audit_request", _noop_audit)
        monkeypatch.setattr(books_endpoint, "audit_request", _noop_audit)

        cookies = {}
        if auth:
            from app.core.security import get_current_user_from_session

            # Create unique session token for this user
            session_token = f"test-session-{user['auth_id']}"

            # Store user in map keyed by session token for multi-user tests
            user_map[session_token] = user

            # Only install the dependency override once
            # The override reads the session cookie to determine which user to return
            if not override_installed:
                async def _get_user_from_session(request=None):
                    """Return test user based on session cookie."""
                    if request is None:
                        if user_map:
                            return next(iter(user_map.values()))
                        return None

                    # Get session token from cookies
                    session_token = request.cookies.get("better-auth.session_token")
                    if session_token and session_token in user_map:
                        return user_map[session_token]

                    # Fallback: return first user
                    if user_map:
                        return next(iter(user_map.values()))
                    return None

                app.dependency_overrides[get_current_user_from_session] = _get_user_from_session
                override_installed = True

            monkeypatch.setattr(
                users_dao, "get_user_by_auth_id", lambda auth_id: next(
                    (u for u in user_map.values() if u.get('auth_id') == auth_id), None
                )
            )

            # Set the session cookie with the user's unique token
            cookies["better-auth.session_token"] = session_token

        client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            cookies=cookies,
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
