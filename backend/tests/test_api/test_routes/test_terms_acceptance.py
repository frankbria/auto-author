"""Terms acceptance reaches the app's user (#789).

better-auth stamps ``termsVersion`` and ``termsAcceptedAt`` on the users doc at
sign-up; the backend reads them as ``terms_version`` and ``terms_accepted_at``
(#1263). Real session documents, no patched resolver.
"""

from datetime import datetime, timezone

import pytest

from app.db.base import get_collection
from app.db.user import get_user_by_auth_id
from tests.test_api.test_routes.test_account_deletion_real_session import (
    _client,
    _seed_better_auth_user,
)


async def _user_after_a_request(seeded: dict) -> dict:
    async with _client(seeded["tokens"][0]) as c:
        me = await c.get("/api/v1/users/me")
        assert me.status_code == 200, me.text
    return await get_user_by_auth_id(seeded["user_id"])


@pytest.mark.asyncio
async def test_the_app_reads_terms_acceptance_from_the_users_doc(
    reinit_db,
):
    seeded = await _seed_better_auth_user("terms@example.com")
    accepted_at = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    await (await get_collection("users")).update_one(
        {"_id": seeded["oid"]},
        {"$set": {"termsVersion": "2026-10-10", "termsAcceptedAt": accepted_at}},
    )

    user = await _user_after_a_request(seeded)

    assert user["terms_version"] == "2026-10-10"
    assert user["terms_accepted_at"].replace(tzinfo=timezone.utc) == accepted_at


@pytest.mark.asyncio
async def test_an_account_with_no_recorded_acceptance_gets_none(reinit_db):
    """An account created before #789 has nothing recorded; none is invented."""
    seeded = await _seed_better_auth_user("before-789@example.com")

    user = await _user_after_a_request(seeded)

    assert user.get("terms_version") is None
    assert user.get("terms_accepted_at") is None


async def _retained_after_deletion(seeded: dict) -> dict:
    async with _client(seeded["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        assert (await c.delete("/api/v1/users/me")).status_code == 200
    return (
        await (await get_collection("deleted_users")).find_one({"auth_id": seeded["user_id"]})
    )["retained"]


@pytest.mark.asyncio
async def test_deactivation_keeps_the_terms_acceptance_record(reinit_db):
    """#960: the 18-month record can answer "I never agreed to the Terms"."""
    seeded = await _seed_better_auth_user("terms-kept@example.com")
    accepted_at = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    await (await get_collection("users")).update_one(
        {"_id": seeded["oid"]},
        {"$set": {"termsVersion": "2026-10-10", "termsAcceptedAt": accepted_at}},
    )

    retained = await _retained_after_deletion(seeded)

    assert retained["terms_version"] == "2026-10-10"
    assert retained["terms_accepted_at"].replace(tzinfo=timezone.utc) == accepted_at


@pytest.mark.asyncio
async def test_deactivation_keeps_no_empty_entry_for_an_account_with_no_record(
    reinit_db,
):
    """The users doc has neither; the retained record leaves them out."""
    seeded = await _seed_better_auth_user("before-789-deleted@example.com")

    retained = await _retained_after_deletion(seeded)

    assert "terms_version" not in retained
    assert "terms_accepted_at" not in retained
