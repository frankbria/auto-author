import sys
import os
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
import app.db.toc_transactions as toc_transactions
from app.db import base
from app import db


# Patch the DB connection for tests to use a real MongoDB instance
# DB name is env-overridable so parallel runs (e.g. CI shards, multi-agent test
# authoring) can each use an isolated database. Default preserves prior behavior.
TEST_MONGO_URI = os.environ.get(
    "TEST_MONGO_URI", "mongodb://localhost:27017/auto-author-test"
)
_TEST_DB_NAME = TEST_MONGO_URI.rsplit("/", 1)[-1].split("?")[0]

# Data-loss guard (#211): the fixtures below DROP _TEST_DB_NAME in setup/teardown.
# Abort collection now if the resolved target isn't clearly a local/test database,
# so an accidental Atlas URI can't wipe real data.
from tests.db_guard import assert_safe_test_db

assert_safe_test_db(TEST_MONGO_URI, _TEST_DB_NAME)

_sync_client = pymongo.MongoClient(TEST_MONGO_URI)
_sync_db = _sync_client.get_default_database()
_sync_users = _sync_db.get_collection("users")
_sync_books = _sync_db.get_collection("books")
_sync_logs = _sync_db.get_collection("audit_logs")
_sync_sessions = _sync_db.get_collection("sessions")

async def noop_rate_limiter(request: Request):
    """Shared no-op limiter dependency. Deliberately ONE module-level function
    (not a fresh closure per factory call) so every production route captures
    the same callable — letting a test re-arm the REAL limiter on any route via
    a single app.dependency_overrides[noop_rate_limiter] entry
    (see arm_real_rate_limiter)."""
    return {"limit": float("inf"), "remaining": float("inf"), "reset": None}


def fake_get_rate_limiter(limit: int = 10, window: int = 60):
    """
    Fake rate limiter factory that bypasses rate limiting in tests.
    Returns the shared noop_rate_limiter regardless of limit/window.
    """
    return noop_rate_limiter


# Preserve the real limiter so tests that need to exercise the actual
# rate-limiting logic can reach it (the override below hides it everywhere else).
# Idempotent: conftest can be imported more than once, so stash the genuine
# function on the module and never let a re-import capture the fake.
real_get_rate_limiter = getattr(deps, "_real_get_rate_limiter", deps.get_rate_limiter)
deps._real_get_rate_limiter = real_get_rate_limiter
deps.get_rate_limiter = fake_get_rate_limiter


def fake_get_ai_usage_quota():
    """No-op AI quota dependency, so test suites can generate freely.
    Mirrors fake_get_rate_limiter; enforcement is exercised via `real_ai_quota`."""

    async def _always_allow():
        return None

    return _always_allow


# Same idempotent stash-the-real / install-the-fake dance as the rate limiter.
real_get_ai_usage_quota = getattr(
    deps, "_real_get_ai_usage_quota", deps.get_ai_usage_quota
)
deps._real_get_ai_usage_quota = real_get_ai_usage_quota
deps.get_ai_usage_quota = fake_get_ai_usage_quota
import pytest, pytest_asyncio


@pytest.fixture
def real_rate_limiter():
    """The genuine get_rate_limiter, for tests that exercise real rate limiting
    (the module-level override above replaces it with a no-op everywhere else)."""
    return real_get_rate_limiter


@pytest.fixture
def real_ai_quota():
    """The genuine get_ai_usage_quota, for tests that assert the 429 at the cap
    (the module-level override above replaces it with a no-op everywhere else)."""
    return real_get_ai_usage_quota


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
from unittest.mock import patch as _mock_patch

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def arm_real_rate_limiter():
    """Re-arm the REAL rate limiter on production routes for one test.

    Every route captured the shared noop_rate_limiter at import time, so one
    dependency_overrides entry swaps in a genuine limiter closure with a small
    test cap. BYPASS_AUTH is forced off so the limiter actually counts.
    Yields arm(limit, window=3600); if the target route no longer declares
    Depends(get_rate_limiter(...)), the override never fires and the test's
    expected 429 fails RED — the #199 test-trust guarantee.
    """
    _bypass_off = _mock_patch.object(deps.settings, "BYPASS_AUTH", False)
    _bypass_off.start()
    # Freeze the limiter's clock 1s past a bucket start so an epoch-aligned
    # window can never roll over mid-test (same seam test_rate_limiter_window_reset
    # patches). Without this, a test straddling a real window boundary would
    # see its count reset and flake.
    _frozen_now = (int(deps.time.time() // 3600) * 3600) + 1
    _clock = _mock_patch.object(deps.time, "time", return_value=_frozen_now)
    _clock.start()

    def arm(limit: int, window: int = 3600):
        app.dependency_overrides[noop_rate_limiter] = real_get_rate_limiter(
            limit=limit, window=window
        )

    yield arm
    _clock.stop()
    _bypass_off.stop()
    app.dependency_overrides.pop(noop_rate_limiter, None)

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
    _sync_client.drop_database(_TEST_DB_NAME)

    # Create async Motor client for test use
    base._client = motor.motor_asyncio.AsyncIOMotorClient(TEST_MONGO_URI)
    base._db = base._client.get_default_database()

    # Set up collections
    base.users_collection = base._db.get_collection("users")
    base.books_collection = base._db.get_collection("books")
    base.audit_logs_collection = base._db.get_collection("audit_logs")

    books_dao.books_collection = base.books_collection
    books_dao.users_collection = base.users_collection
    users_dao.users_collection = base.users_collection
    audit_log_dao.audit_logs_collection = base.audit_logs_collection

    # toc_transactions binds _client/_db/books_collection at import time via
    # `from .base import ...`; rebind them to the fresh per-test client so the
    # transactional chapter endpoints don't run against a closed event loop.
    toc_transactions._client = base._client
    toc_transactions._db = base._db
    toc_transactions.books_collection = base.books_collection

    yield

    # Drop database after test using sync client
    _sync_client.drop_database(_TEST_DB_NAME)
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
        "plan": "free",
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
        "plan": "free",
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
