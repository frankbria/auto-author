import sys
import os
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest
import pymongo

# Settings refuses to build without an explicit ENVIRONMENT (#777), and the app
# modules below build it at import. Forced, not defaulted: a shell exporting
# staging/production would otherwise flip the guards the suite asserts on.
os.environ["ENVIRONMENT"] = "test"

# Uploads in tests go to local disk, whatever a developer's backend/.env sets
# (#806): the storage provider is decided from settings now, and settings read
# that file. The process environment wins over it, so empty values here do too.
for _storage_field in (
    "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET",
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_BUCKET",
):
    os.environ[_storage_field] = ""

# AI tests assert the documented model defaults, whatever a developer's
# backend/.env sets (#926). The module-level ai_service singleton is built at
# import and reads these, so reset them before any app module imports it.
from app.core.config import Settings, settings as _settings

# Every AI_* field, so a setting added later is reset without editing this list.
AI_SETTINGS = tuple(name for name in Settings.model_fields if name.startswith("AI_"))
for _name in AI_SETTINGS:
    setattr(_settings, _name, Settings.model_fields[_name].default)


@pytest.fixture(autouse=True)
def unset_ai_settings(monkeypatch):
    """Every AI_* setting at its declared default, whatever the local .env says."""
    for name in AI_SETTINGS:
        monkeypatch.setattr(_settings, name, Settings.model_fields[name].default)


import app.api.dependencies as deps
from fastapi import HTTPException, Request
from pymongo import AsyncMongoClient
import app.db.user as users_dao
import app.db.book as books_dao
import app.db.audit_log as audit_log_dao
import app.db.toc_transactions as toc_transactions
from app.db import base


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
# better-auth's own name for it. It was "sessions", a collection nothing writes (#838).
_sync_sessions = _sync_db.get_collection("session")

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


async def noop_ai_quota():
    """Shared no-op AI quota dependency. Like `noop_rate_limiter`, deliberately
    ONE module-level function (not a fresh closure per factory call) so every AI
    route captures the same callable — letting a test re-arm the REAL quota on
    all of them via a single app.dependency_overrides entry
    (see arm_real_ai_quota, issue #340)."""


def fake_get_ai_usage_quota():
    """No-op AI quota factory, so test suites can generate freely.
    Mirrors fake_get_rate_limiter; enforcement is exercised via `real_ai_quota`
    (direct invocation) or `arm_real_ai_quota` (through a real route)."""
    return noop_ai_quota


# Same idempotent stash-the-real / install-the-fake dance as the rate limiter.
real_get_ai_usage_quota = getattr(
    deps, "_real_get_ai_usage_quota", deps.get_ai_usage_quota
)
deps._real_get_ai_usage_quota = real_get_ai_usage_quota
deps.get_ai_usage_quota = fake_get_ai_usage_quota
import pytest_asyncio


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
from fastapi.testclient import TestClient
from typing import Dict, Optional
from app.main import app
import asyncio
from datetime import datetime, timezone
from app.core.security import get_current_user_from_session
from app.api.endpoints import users as users_endpoint
from app.api.endpoints import books as books_endpoint
from app.api.endpoints import book_cover as book_cover_endpoint
from app.api.endpoints import chapter_questions as chapter_questions_endpoint
from app.api.endpoints import chapter_ai as chapter_ai_endpoint
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


@pytest.fixture
def arm_real_ai_quota():
    """Re-arm the REAL AI usage quota on production routes for one test (#340).

    Every AI route captured the shared `noop_ai_quota` at import time, so one
    dependency_overrides entry swaps in a genuine quota closure with a small
    test cap. BYPASS_AUTH is forced off and AI_QUOTA_ENABLED on so it counts.
    Yields arm(limit); if the target route no longer declares
    Depends(get_ai_usage_quota()), the override never fires and the test's
    expected 429 fails RED — the same test-trust guarantee #199 gave the limiter.

    The monthly window is disabled so the daily cap alone drives the 429 and the
    asserted X-AI-Quota-Period header is deterministic. E2E_EXEMPT_EMAILS is
    forced empty so an exemption configured in the ambient env can't silently
    un-meter the test user (`_is_exempt_e2e_user`).

    Unlike arm_real_rate_limiter this does NOT freeze the clock: the quota keys
    off `datetime.now(...)` day/month buckets, not the `deps.time.time` seam, and
    the only exposure is the sub-10ms window between a test's two requests
    straddling midnight UTC. Not worth patching the module-wide `datetime`.
    """
    patches = [
        _mock_patch.object(deps.settings, "BYPASS_AUTH", False),
        _mock_patch.object(deps.settings, "AI_QUOTA_ENABLED", True),
        _mock_patch.object(deps.settings, "AI_QUOTA_FREE_MONTHLY", 0),
        _mock_patch.object(deps.settings, "AI_QUOTA_PRO_MONTHLY", 0),
        _mock_patch.object(deps.settings, "E2E_EXEMPT_EMAILS", ""),
    ]
    for p in patches:
        p.start()
    armed_keys = []

    def arm(limit: int):
        # Override the callable the ROUTES actually captured, derived by name
        # from the live app rather than by referencing this module's
        # `noop_ai_quota`. If conftest ever re-executes under the second module
        # identity `tests.conftest`, this module's global is a different object
        # than the one the routes hold, and a direct reference would install an
        # override that never fires (see route_introspection.shared_dependency_call).
        from tests.route_introspection import (
            route_dependency_calls,
            shared_dependency_call,
        )

        captured = shared_dependency_call(route_dependency_calls(), "noop_ai_quota")
        assert len(captured) == 1, (
            f"Expected exactly one route-captured noop_ai_quota; found {captured}. "
            "The conftest quota swap must return ONE shared module-level function."
        )
        key = next(iter(captured))

        for name in ("AI_QUOTA_FREE_DAILY", "AI_QUOTA_PRO_DAILY"):
            p = _mock_patch.object(deps.settings, name, limit)
            p.start()
            patches.append(p)
        app.dependency_overrides[key] = real_get_ai_usage_quota()
        armed_keys.append(key)

    yield arm
    for p in reversed(patches):
        p.stop()
    for key in armed_keys:
        app.dependency_overrides.pop(key, None)

@pytest_asyncio.fixture(autouse=False)  # Not autouse - tests must explicitly request this fixture
async def reinit_db():
    """
    Every test gets its own client bound to a fresh database.
    Drops the test DB before & after so you start with a clean slate.

    Async so that teardown closes the client on the event loop the test used:
    an AsyncMongoClient is bound to its first loop and cannot be closed from
    another one.
    """
    # Drop database before test using sync client
    _sync_client.drop_database(_TEST_DB_NAME)

    # Create the async client for test use
    base._client = AsyncMongoClient(TEST_MONGO_URI)
    base._db = base._client.get_default_database()

    # Set up collections
    base.users_collection = base._db.get_collection("users")
    base.books_collection = base._db.get_collection("books")
    base.audit_logs_collection = base._db.get_collection("audit_logs")

    books_dao.books_collection = base.books_collection
    books_dao.users_collection = base.users_collection
    # delete_book opens its transaction on this client; left as imported it belongs to another event loop (#839).
    books_dao._client = base._client
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
    await base._client.close()


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


def _signed_in_as(user_map: dict):
    """The stand-in both client factories put in place of the sign-in check (#838).

    It is as strict as the real one. The cookie must be one a client was given:
    a missing or unknown cookie is refused, where it used to be signed in as the
    first user any client was made for. And the user is read from the database
    on every request, as the real check reads it, so a test that changes or
    removes the user sees that on its next request.
    """

    async def _get_user_from_session(request: Request):
        seeded = user_map.get(request.cookies.get("better-auth.session_token"))
        user = _sync_users.find_one({"_id": seeded["_id"]}) if seeded else None
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated. Please sign in.")
        return user

    return _get_user_from_session


@pytest_asyncio.fixture(scope="function")
async def auth_client_factory(reinit_db, monkeypatch, test_user):
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

        async def _noop_audit_request(
            request: Request,
            current_user: Dict,
            action: str,
            resource_type: str,
            target_id: Optional[str] = None,
            **kwargs,
        ):
            return None

        monkeypatch.setattr(users_endpoint, "audit_after_commit", _noop_audit_request)
        monkeypatch.setattr(books_endpoint, "audit_after_commit", _noop_audit_request)
        monkeypatch.setattr(book_cover_endpoint, "audit_after_commit", _noop_audit_request)
        monkeypatch.setattr(chapter_questions_endpoint, "audit_after_commit", _noop_audit_request)
        monkeypatch.setattr(chapter_ai_endpoint, "audit_after_commit", _noop_audit_request)

        cookies = {}
        if auth:
            # Create unique session token for this user
            session_token = f"test-session-{user['auth_id']}"

            # Store user in map keyed by session token for multi-user tests
            user_map[session_token] = user

            app.dependency_overrides[get_current_user_from_session] = _signed_in_as(user_map)

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
async def async_client_factory(reinit_db, monkeypatch, test_user):
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

        monkeypatch.setattr(users_endpoint, "audit_after_commit", _noop_audit)
        monkeypatch.setattr(books_endpoint, "audit_after_commit", _noop_audit)
        monkeypatch.setattr(book_cover_endpoint, "audit_after_commit", _noop_audit)
        monkeypatch.setattr(chapter_questions_endpoint, "audit_after_commit", _noop_audit)
        monkeypatch.setattr(chapter_ai_endpoint, "audit_after_commit", _noop_audit)

        cookies = {}
        if auth:
            from app.core.security import get_current_user_from_session

            # Create unique session token for this user
            session_token = f"test-session-{user['auth_id']}"

            # Store user in map keyed by session token for multi-user tests
            user_map[session_token] = user

            app.dependency_overrides[get_current_user_from_session] = _signed_in_as(user_map)

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


# REMOVED: clean_db fixture was redundant and conflicting with reinit_db
# The reinit_db fixture (line 67) already handles database cleanup before/after each test
# Having both autouse fixtures caused race conditions and test hangs
