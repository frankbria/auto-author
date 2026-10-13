"""Email verification (#792).

better-auth refuses to sign in an unverified address. The backend is the second
lock: it will not create its own record for one. Accounts that existed before
verification was required are marked verified at startup, because they never
had a way to verify; the first such startup fixes what counts as before.
Real better-auth documents, no patched resolver.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.db.base import get_collection
from app.db.user import grandfather_unverified_accounts
from tests.test_api.test_routes.test_account_deletion_real_session import (
    _client,
    _seed_better_auth_user,
)

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("change", [{"$set": {"emailVerified": False}}, {"$unset": {"emailVerified": 1}}])
async def test_first_request_from_an_unverified_account_is_refused(motor_reinit_db, change):
    seeded = await _seed_better_auth_user("unverified@example.com")
    await (await get_collection("user")).update_one({"_id": seeded["oid"]}, change)

    async with _client(seeded["tokens"][0]) as c:
        response = await c.get("/api/v1/users/me")

    assert response.status_code == 403, response.text
    assert "verify your email" in response.json()["detail"].lower()
    users = await get_collection("users")
    assert await users.find_one({"auth_id": seeded["user_id"]}) is None


async def test_a_verified_account_gets_its_record_on_the_first_request(motor_reinit_db):
    seeded = await _seed_better_auth_user("verified@example.com")
    await (await get_collection("user")).update_one(
        {"_id": seeded["oid"]}, {"$set": {"emailVerified": True}}
    )

    async with _client(seeded["tokens"][0]) as c:
        response = await c.get("/api/v1/users/me")

    assert response.status_code == 200, response.text
    assert response.json()["email"] == "verified@example.com"


async def _seed_account(**fields) -> ObjectId:
    oid = ObjectId()
    await (await get_collection("user")).insert_one(
        {"_id": oid, "email": f"{oid}@example.com", **fields}
    )
    return oid


async def _seed_existing_accounts() -> dict:
    """Accounts from before the requirement, keyed by a label."""
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    return {
        "unverified": await _seed_account(emailVerified=False, createdAt=yesterday),
        "without the field": await _seed_account(createdAt=yesterday),
        "verified": await _seed_account(emailVerified=True, createdAt=yesterday),
    }


async def _verified(oid: ObjectId):
    return (await (await get_collection("user")).find_one({"_id": oid})).get("emailVerified")


async def test_accounts_that_predate_the_requirement_are_marked_verified(motor_reinit_db):
    existing = await _seed_existing_accounts()

    assert await grandfather_unverified_accounts() == 2

    assert [await _verified(oid) for oid in existing.values()] == [True, True, True]


async def test_an_account_created_under_the_requirement_is_never_marked_verified(
    motor_reinit_db,
):
    """The first run fixes the moment; a later restart must not move it."""
    await grandfather_unverified_accounts()
    signed_up_later = await _seed_account(
        emailVerified=False, createdAt=datetime.now(timezone.utc)
    )

    assert await grandfather_unverified_accounts() == 0

    assert await _verified(signed_up_later) is False


async def test_startup_marks_existing_accounts_verified(motor_reinit_db, monkeypatch):
    from app.main import app, lifespan

    # Shutdown closes the export pool; hand it one that no other test uses.
    monkeypatch.setattr(
        "app.services.export_service.export_executor", ThreadPoolExecutor(1)
    )
    existing = await _seed_existing_accounts()

    async with lifespan(app):
        await app.state.database_prepared  # beside the server since #1012

    assert await _verified(existing["unverified"]) is True


async def test_creating_the_record_does_not_log_the_email_address(motor_reinit_db, caplog):
    """#794: logs are kept longer and read more widely than the users collection."""
    seeded = await _seed_better_auth_user("private-address@example.com")

    with caplog.at_level("DEBUG", logger="app"):
        async with _client(seeded["tokens"][0]) as c:
            assert (await c.get("/api/v1/users/me")).status_code == 200

    # The application's own lines; the driver's DEBUG output is not ours to shape.
    app_log = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("app."))
    assert "Auto-creating user record" in app_log
    assert "Found better-auth user" in app_log
    assert "private-address@example.com" not in app_log
