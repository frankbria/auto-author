"""Account deletion leaves no usage counters and no better-auth verification
rows (#957).

The verification shapes are the ones better-auth 1.7.7 writes: the user id is
the ``value`` of trust-device, pending two-factor sign-in, password-reset and
delete-account rows; a pending sign-in's attempt counter and OTP are keyed by
that row's identifier; a signed-in OTP is keyed by ``<user id>!<session id>``.
Email verification is a JWT and writes no row.

Against a real MongoDB.
"""

import pytest

from app.db.base import get_collection
from app.db.usage import increment_usage
from app.db.user import create_user, delete_user
from tests.test_api.test_routes.test_account_deletion_real_session import (
    _seed_better_auth_user,
)

pytestmark = pytest.mark.asyncio


def _verification_rows(user_id: str, tag: str) -> list:
    pending = f"2fa-pending{tag}"
    return [
        {"identifier": f"trust-device-{tag}", "value": user_id},
        {"identifier": pending, "value": user_id},
        {"identifier": f"2fa-attempts-{pending}", "value": "0"},
        {"identifier": f"2fa-otp-{pending}", "value": "hashed:0"},
        {"identifier": f"reset-password:token{tag}", "value": user_id},
        {"identifier": f"delete-account-token{tag}", "value": user_id},
        {"identifier": f"2fa-otp-{user_id}!session{tag}", "value": "hashed:0"},
    ]


async def _account(email: str, tag: str) -> str:
    user_id = (await _seed_better_auth_user(email))["user_id"]
    await create_user({"auth_id": user_id, "email": email, "plan": "free", "is_active": True})
    await (await get_collection("verification")).insert_many(_verification_rows(user_id, tag))
    await increment_usage(user_id, "day:2026-10-22", 86400)
    await increment_usage(user_id, "rl:DELETE /users/me:0", 120)
    return user_id


async def _identifiers() -> set:
    return {d["identifier"] async for d in (await get_collection("verification")).find()}


async def test_deletion_removes_the_users_verification_rows_only(reinit_db):
    victim = await _account("gone@example.com", "A")
    bystander = await _account("stays@example.com", "B")
    oauth_state = {"identifier": "oauth-state", "value": '{"callbackURL": "/"}'}
    await (await get_collection("verification")).insert_one(oauth_state)

    assert await delete_user(victim) is True

    survivors = {row["identifier"] for row in _verification_rows(bystander, "B")}
    assert await _identifiers() == survivors | {"oauth-state"}


async def test_deletion_removes_the_users_usage_counters_only(reinit_db):
    victim = await _account("gone@example.com", "A")
    bystander = await _account("stays@example.com", "B")
    counters = await get_collection("usage_counters")

    assert await delete_user(victim) is True

    assert await counters.count_documents({"user_id": victim}) == 0
    assert await counters.count_documents({"user_id": bystander}) == 2
