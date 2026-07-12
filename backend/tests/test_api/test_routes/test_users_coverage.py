"""
Integration coverage tests for app/api/endpoints/users.py.

Covers the previously-untested endpoints (update_user_data, get_all_users,
delete_user_account) plus the error branches of read_users_me,
update_profile, and delete_profile. Real MongoDB is used (session auth mocked
via auth_client_factory); only the DB helper calls that simulate failures are
patched per-test.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.security import get_current_user_from_session

pytestmark = pytest.mark.asyncio

USERS = "app.api.endpoints.users"


# ---------------------------------------------------------------------------
# read_users_me — edge/error branches
# ---------------------------------------------------------------------------
async def test_read_me_applies_default_preferences(auth_client_factory):
    """Empty preferences fall back to the hardcoded defaults (line 55)."""
    client = await auth_client_factory(overrides={"preferences": {}})
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 200
    prefs = resp.json()["preferences"]
    assert prefs["theme"] == "dark"
    assert prefs["email_notifications"] is True


async def test_read_me_uses_id_when_no_mongo_id(auth_client_factory):
    """When the user dict has no _id, fall back to the `id` key (lines 65-66)."""
    client = await auth_client_factory(auth=False)

    async def _custom_user(request=None):
        return {"id": "plain-id-789", "auth_id": "a-789", "email": "x@y.z", "role": "user"}

    app.dependency_overrides[get_current_user_from_session] = _custom_user
    try:
        resp = await client.get("/api/v1/users/me")
    finally:
        app.dependency_overrides.pop(get_current_user_from_session, None)

    assert resp.status_code == 200
    assert resp.json()["id"] == "plain-id-789"


async def test_read_me_internal_error_returns_500(auth_client_factory):
    """An unexpected error inside read_users_me maps to 500 (lines 86-91)."""
    client = await auth_client_factory()
    with patch(f"{USERS}.audit_request", side_effect=RuntimeError("boom")):
        resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Error retrieving user profile"


# ---------------------------------------------------------------------------
# update_profile (PATCH /me) — error branches
# ---------------------------------------------------------------------------
async def test_patch_me_happy_path(auth_client_factory):
    client = await auth_client_factory()
    resp = await client.patch("/api/v1/users/me", json={"first_name": "Renamed"})
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Renamed"


async def test_patch_me_duplicate_email_returns_409(auth_client_factory):
    client = await auth_client_factory()
    with patch(f"{USERS}.update_user", AsyncMock(side_effect=Exception("E11000 duplicate key error"))):
        resp = await client.patch("/api/v1/users/me", json={"email": "dupe@example.com"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Email already exists"


async def test_patch_me_timeout_returns_504(auth_client_factory):
    client = await auth_client_factory()
    with patch(f"{USERS}.update_user", AsyncMock(side_effect=Exception("operation timed out"))):
        resp = await client.patch("/api/v1/users/me", json={"first_name": "X"})
    assert resp.status_code == 504


async def test_patch_me_generic_error_returns_500(auth_client_factory):
    client = await auth_client_factory()
    with patch(f"{USERS}.update_user", AsyncMock(side_effect=Exception("something broke"))):
        resp = await client.patch("/api/v1/users/me", json={"first_name": "X"})
    assert resp.status_code == 500


async def test_patch_me_user_not_found_returns_404(auth_client_factory):
    client = await auth_client_factory()
    with patch(f"{USERS}.update_user", AsyncMock(return_value=None)):
        resp = await client.patch("/api/v1/users/me", json={"first_name": "X"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# delete_profile (DELETE /me)
# ---------------------------------------------------------------------------
async def test_delete_me_happy_path(auth_client_factory):
    client = await auth_client_factory()
    resp = await client.delete("/api/v1/users/me")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Account successfully deleted"


async def test_delete_me_not_found_returns_404(auth_client_factory):
    client = await auth_client_factory()
    with patch(f"{USERS}.delete_user", AsyncMock(return_value=False)):
        resp = await client.delete("/api/v1/users/me")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST / — removed (issue #186)
#
# The unauthenticated create endpoint was an enumeration oracle (distinct 409s
# for existing auth_id vs email vs 201) and a junk-record vector. Signup rides
# the better-auth session auto-create in app/core/security.py instead.
# ---------------------------------------------------------------------------
async def test_post_users_route_is_gone_for_anonymous(auth_client_factory):
    client = await auth_client_factory(auth=False)
    resp = await client.post(
        "/api/v1/users/",
        json={"auth_id": "attacker-id", "email": "victim@example.com"},
    )
    assert resp.status_code in (404, 405)


async def test_post_users_route_is_gone_even_authenticated(auth_client_factory):
    # test_user (auth_id test-auth-id-123, tester@example.com) is seeded by the
    # factory — an existing record must NOT be distinguishable via 409/201.
    client = await auth_client_factory()
    resp = await client.post(
        "/api/v1/users/",
        json={"auth_id": "test-auth-id-123", "email": "tester@example.com"},
    )
    assert resp.status_code in (404, 405)


# ---------------------------------------------------------------------------
# update_user_data (PUT /{auth_id})
# ---------------------------------------------------------------------------
async def test_put_user_self_happy_path(auth_client_factory):
    client = await auth_client_factory()
    resp = await client.put(
        "/api/v1/users/test-auth-id-123", json={"first_name": "Updated"}
    )
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Updated"


MARKUP_BIO = "<script>alert(1)</script><b>bold</b>  claim"


async def test_put_sanitizes_strings_same_as_patch(auth_client_factory):
    """AC (#265): a string field containing markup is stored identically
    (sanitized) whether written via PATCH /me or PUT /{auth_id}."""
    from app.db import base

    client = await auth_client_factory()
    resp = await client.patch("/api/v1/users/me", json={"bio": MARKUP_BIO})
    assert resp.status_code == 200
    via_patch = (await base.users_collection.find_one({"auth_id": "test-auth-id-123"}))["bio"]
    assert "<" not in via_patch  # PATCH already sanitizes — pin it

    resp = await client.put(
        "/api/v1/users/test-auth-id-123", json={"bio": "different"}
    )
    assert resp.status_code == 200
    resp = await client.put(
        "/api/v1/users/test-auth-id-123", json={"bio": MARKUP_BIO}
    )
    assert resp.status_code == 200
    via_put = (await base.users_collection.find_one({"auth_id": "test-auth-id-123"}))["bio"]
    assert via_put == via_patch


async def test_put_user_other_non_admin_returns_403(auth_client_factory):
    client = await auth_client_factory()
    resp = await client.put(
        "/api/v1/users/someone-else", json={"first_name": "Nope"}
    )
    assert resp.status_code == 403
    assert "permissions" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Issue #244 — privileged fields are not writable via the API
# UserUpdate is extra="forbid", so an unknown/privileged key is a 422 and the
# handler (and its generic $set) never runs.
# ---------------------------------------------------------------------------
PRIVILEGED_FIELDS = [
    ("role", "admin"),
    ("plan", "pro"),
    ("is_active", False),
    ("stripe_customer_id", "cus_evil"),
    ("stripe_subscription_id", "sub_evil"),
    ("book_ids", ["not-yours"]),
    ("auth_id", "someone-else"),
]


@pytest.mark.parametrize("field,value", PRIVILEGED_FIELDS)
async def test_patch_me_privileged_field_rejected_and_not_persisted(
    auth_client_factory, field, value
):
    """AC (#244): authenticated PATCH /users/me with a privileged field is
    rejected with 422 and the stored document is byte-identical afterwards."""
    from app.db import base

    client = await auth_client_factory()
    before = await base.users_collection.find_one({"auth_id": "test-auth-id-123"})
    assert before is not None  # fail fast if the factory didn't seed the user
    resp = await client.patch("/api/v1/users/me", json={field: value})
    assert resp.status_code == 422
    after = await base.users_collection.find_one({"auth_id": "test-auth-id-123"})
    assert after == before


async def test_patch_me_declared_fields_still_persist(auth_client_factory):
    """extra="forbid" (#244) must not break a normal update: declared fields
    still round-trip to the stored document."""
    from app.db import base

    client = await auth_client_factory()
    resp = await client.patch(
        "/api/v1/users/me", json={"first_name": "Ada", "bio": "Mathematician"}
    )
    assert resp.status_code == 200
    stored = await base.users_collection.find_one({"auth_id": "test-auth-id-123"})
    assert stored["first_name"] == "Ada"
    assert stored["bio"] == "Mathematician"


async def test_put_user_role_rejected_and_not_persisted(auth_client_factory):
    """#244: role is unwritable via PUT /users/{auth_id} as well."""
    from app.db import base

    client = await auth_client_factory()
    resp = await client.put(
        "/api/v1/users/test-auth-id-123",
        json={"role": "admin", "first_name": "Kept"},
    )
    assert resp.status_code == 422
    stored = await base.users_collection.find_one({"auth_id": "test-auth-id-123"})
    assert stored["role"] == "user"
    assert stored["first_name"] != "Kept"


async def test_put_user_role_rejected_even_for_admin(auth_client_factory):
    """#244: no API path writes role — an admin PUT targeting another user is
    422 too; roles are managed directly in the database."""
    from app.db import base

    admin_client = await auth_client_factory(
        overrides={"role": "admin", "auth_id": "admin-244"}
    )
    await auth_client_factory()  # seeds the default test-auth-id-123 user
    resp = await admin_client.put(
        "/api/v1/users/test-auth-id-123", json={"role": "superadmin"}
    )
    assert resp.status_code == 422
    stored = await base.users_collection.find_one({"auth_id": "test-auth-id-123"})
    assert stored["role"] == "user"


async def test_put_user_fetch_error_returns_504(auth_client_factory):
    client = await auth_client_factory()
    with patch(f"{USERS}.get_user_by_auth_id", AsyncMock(side_effect=Exception("timeout"))):
        resp = await client.put(
            "/api/v1/users/test-auth-id-123", json={"first_name": "X"}
        )
    assert resp.status_code == 504


async def test_put_user_admin_target_missing_returns_404(auth_client_factory):
    client = await auth_client_factory(overrides={"role": "admin", "auth_id": "admin-1"})
    resp = await client.put(
        "/api/v1/users/ghost-user", json={"first_name": "X"}
    )
    assert resp.status_code == 404


async def test_put_user_update_returns_none_404(auth_client_factory):
    """update_user returning None yields 404 (now that HTTPException isn't swallowed)."""
    client = await auth_client_factory()
    with patch(f"{USERS}.update_user", AsyncMock(return_value=None)):
        resp = await client.put(
            "/api/v1/users/test-auth-id-123", json={"first_name": "X"}
        )
    assert resp.status_code == 404


async def test_put_user_update_error_returns_500(auth_client_factory):
    client = await auth_client_factory()
    with patch(f"{USERS}.update_user", AsyncMock(side_effect=Exception("db down"))):
        resp = await client.put(
            "/api/v1/users/test-auth-id-123", json={"first_name": "X"}
        )
    assert resp.status_code == 500


# ---------------------------------------------------------------------------
# get_all_users (GET /admin/users) — admin only
# ---------------------------------------------------------------------------
async def test_admin_list_users(auth_client_factory, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "BYPASS_AUTH", True)
    client = await auth_client_factory()
    resp = await client.get("/api/v1/users/admin/users")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# delete_user_account (DELETE /{auth_id})
# ---------------------------------------------------------------------------
async def test_delete_user_self_happy_path(auth_client_factory):
    client = await auth_client_factory()
    resp = await client.delete("/api/v1/users/test-auth-id-123")
    assert resp.status_code == 204


async def test_delete_user_other_non_admin_returns_403(auth_client_factory):
    client = await auth_client_factory()
    resp = await client.delete("/api/v1/users/someone-else")
    assert resp.status_code == 403


async def test_delete_user_not_found_returns_404(auth_client_factory):
    """delete_user returning False yields 404 (HTTPException no longer swallowed)."""
    client = await auth_client_factory(overrides={"role": "admin", "auth_id": "admin-2"})
    with patch(f"{USERS}.delete_user", AsyncMock(return_value=False)):
        resp = await client.delete("/api/v1/users/ghost-user")
    assert resp.status_code == 404


async def test_delete_user_db_error_returns_504(auth_client_factory):
    client = await auth_client_factory()
    with patch(f"{USERS}.delete_user", AsyncMock(side_effect=Exception("db down"))):
        resp = await client.delete("/api/v1/users/test-auth-id-123")
    assert resp.status_code == 504
