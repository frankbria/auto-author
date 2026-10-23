"""The account export's download token (#966): POST /users/me/export/token
issues a short-lived, single-use token for the session's own account, and
GET /users/me/export?token=... needs that token and the same session.

Real better-auth sessions and real Mongo; the audit helper is the real one.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.db.base import get_collection
from tests.conftest import _sync_logs
from tests.test_api.test_routes.test_account_deletion_real_session import (
    _client,
    _seed_better_auth_user,
)

TOKEN_URL = "/api/v1/users/me/export/token"
EXPORT_URL = "/api/v1/users/me/export"


async def _issue(c) -> str:
    issued = await c.post(TOKEN_URL)
    assert issued.status_code == 200, issued.text
    return issued.json()["token"]


@pytest.mark.asyncio
async def test_a_token_downloads_once(reinit_db):
    seeded = await _seed_better_auth_user("once@example.com")
    async with _client(seeded["tokens"][0]) as c:
        token = await _issue(c)
        first = await c.get(EXPORT_URL, params={"token": token})
        second = await c.get(EXPORT_URL, params={"token": token})

    assert first.status_code == 200, first.text
    assert first.json()["profile"]["email"] == "once@example.com"
    assert second.status_code == 410
    assert second.headers["content-type"].startswith("application/json")
    assert "detail" in second.json()


@pytest.mark.asyncio
async def test_an_expired_token_is_refused(reinit_db):
    seeded = await _seed_better_auth_user("late@example.com")
    async with _client(seeded["tokens"][0]) as c:
        token = await _issue(c)
        # Mongo's TTL reaper runs once a minute, so expiry is checked on redemption too.
        result = await (await get_collection("export_tokens")).update_many(
            {}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}}
        )
        assert result.modified_count == 1
        response = await c.get(EXPORT_URL, params={"token": token})

    assert response.status_code == 410
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_a_token_expires_within_a_couple_of_minutes(reinit_db):
    seeded = await _seed_better_auth_user("ttl@example.com")
    async with _client(seeded["tokens"][0]) as c:
        await _issue(c)
    [row] = await (await get_collection("export_tokens")).find().to_list(None)
    expires_at = row["expires_at"].replace(tzinfo=timezone.utc)
    assert expires_at - datetime.now(timezone.utc) <= timedelta(minutes=2)


@pytest.mark.asyncio
async def test_another_users_token_is_refused(reinit_db):
    alice = await _seed_better_auth_user("alice@example.com")
    bob = await _seed_better_auth_user("bob@example.com")
    async with _client(alice["tokens"][0]) as a, _client(bob["tokens"][0]) as b:
        alices_token = await _issue(a)
        response = await b.get(EXPORT_URL, params={"token": alices_token})

    assert response.status_code == 403
    assert "detail" in response.json()
    assert "alice@example.com" not in response.text


@pytest.mark.asyncio
async def test_an_unknown_or_missing_token_is_refused(reinit_db):
    seeded = await _seed_better_auth_user("guess@example.com")
    async with _client(seeded["tokens"][0]) as c:
        guessed = await c.get(EXPORT_URL, params={"token": "not-a-token"})
        missing = await c.get(EXPORT_URL)

    assert guessed.status_code == 410
    assert missing.status_code == 422


@pytest.mark.asyncio
async def test_a_token_without_the_session_is_refused(reinit_db):
    seeded = await _seed_better_auth_user("nocookie@example.com")
    async with _client(seeded["tokens"][0]) as c:
        token = await _issue(c)
    async with _client("no-such-session") as stranger:
        response = await stranger.get(EXPORT_URL, params={"token": token})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_issuing_tokens_is_rate_limited(reinit_db, arm_real_rate_limiter):
    seeded = await _seed_better_auth_user("busy@example.com")
    arm_real_rate_limiter(2)
    async with _client(seeded["tokens"][0]) as c:
        assert (await c.post(TOKEN_URL)).status_code == 200
        assert (await c.post(TOKEN_URL)).status_code == 200
        refused = await c.post(TOKEN_URL)

    assert refused.status_code == 429
    assert refused.headers["retry-after"]
    assert "Try again in" in refused.json()["detail"]


@pytest.mark.asyncio
async def test_a_download_writes_one_account_export_audit_row(reinit_db):
    seeded = await _seed_better_auth_user("audited@example.com")
    async with _client(seeded["tokens"][0]) as c:
        token = await _issue(c)
        assert (await c.get(EXPORT_URL, params={"token": token})).status_code == 200
        # A refused redemption is not an export.
        assert (await c.get(EXPORT_URL, params={"token": token})).status_code == 410

    rows = list(_sync_logs.find({"action": "account_export"}))
    assert len(rows) == 1
    [row] = rows
    assert row["actor_id"] == seeded["user_id"]
    assert row["target_id"] == seeded["user_id"]
    assert row["resource_type"] == "user"
    assert token not in str(row)
