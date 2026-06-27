"""
Integration coverage tests for app/api/endpoints/users.py.

Covers the previously-untested endpoints (create_new_user, update_user_data,
get_all_users, delete_user_account) plus the error branches of read_users_me,
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
# create_new_user (POST /)
# ---------------------------------------------------------------------------
async def test_create_user_happy_path(auth_client_factory):
    client = await auth_client_factory()
    resp = await client.post(
        "/api/v1/users/",
        json={"auth_id": "brand-new-id", "email": "brandnew@example.com", "first_name": "New"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["auth_id"] == "brand-new-id"
    assert data["email"] == "brandnew@example.com"


async def test_create_user_duplicate_auth_id_returns_409(auth_client_factory):
    # test_user (auth_id test-auth-id-123) is seeded by the factory.
    client = await auth_client_factory()
    resp = await client.post(
        "/api/v1/users/",
        json={"auth_id": "test-auth-id-123", "email": "other@example.com"},
    )
    assert resp.status_code == 409
    assert "auth ID" in resp.json()["detail"]


async def test_create_user_duplicate_email_returns_409(auth_client_factory):
    client = await auth_client_factory()
    resp = await client.post(
        "/api/v1/users/",
        json={"auth_id": "unique-id-1", "email": "tester@example.com"},
    )
    assert resp.status_code == 409
    assert "email" in resp.json()["detail"]


async def test_create_user_db_error_returns_500(auth_client_factory):
    client = await auth_client_factory()
    with patch(f"{USERS}.create_user", AsyncMock(side_effect=Exception("db down"))):
        resp = await client.post(
            "/api/v1/users/",
            json={"auth_id": "another-new-id", "email": "another@example.com"},
        )
    assert resp.status_code == 500


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


async def test_put_user_other_non_admin_returns_403(auth_client_factory):
    client = await auth_client_factory()
    resp = await client.put(
        "/api/v1/users/someone-else", json={"first_name": "Nope"}
    )
    assert resp.status_code == 403
    assert "permissions" in resp.json()["detail"]


async def test_put_user_non_admin_role_change_returns_403(auth_client_factory):
    client = await auth_client_factory()
    resp = await client.put(
        "/api/v1/users/test-auth-id-123", json={"role": "admin"}
    )
    assert resp.status_code == 403
    assert "admins" in resp.json()["detail"]


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
