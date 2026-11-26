"""The backend refuses the Service to an account that has not accepted the
current Terms (#1316). Real session documents, no patched resolver.

The frontend's screen (#961) gates the app's pages; this is the same rule for a
direct API call. Billing, the account export, deletion and the account read stay
open, matching the exits the screen offers.
"""

import re
from pathlib import Path

import pytest

from app.core.legal import TERMS_VERSION
from app.db.base import get_collection
from tests.test_api.test_routes.test_account_deletion_real_session import (
    _client,
    _seed_better_auth_user,
)

FRONTEND_LEGAL = Path(__file__).parents[4] / "frontend/src/lib/constants/legal.ts"


def test_the_backend_terms_version_mirrors_the_frontend():
    match = re.search(r"export const TERMS_VERSION = '([^']+)'", FRONTEND_LEGAL.read_text())
    assert match, f"TERMS_VERSION not found in {FRONTEND_LEGAL}"
    assert TERMS_VERSION == match.group(1)


async def _seed(email: str, version):
    seeded = await _seed_better_auth_user(email, terms_version=version)
    return seeded["tokens"][0]


@pytest.mark.asyncio
@pytest.mark.parametrize("version", ["2026-10-10", None])
async def test_an_older_or_missing_acceptance_is_refused_the_service(reinit_db, version):
    token = await _seed(f"old-{version}@example.com", version)
    async with _client(token) as c:
        for call in (c.get("/api/v1/books/"), c.post("/api/v1/books/", json={"title": "No"})):
            response = await call
            assert response.status_code == 403, response.text
            assert response.json()["detail"]["error_code"] == "TERMS_NOT_ACCEPTED"
    assert await (await get_collection("books")).count_documents({}) == 0


@pytest.mark.asyncio
async def test_the_current_acceptance_uses_the_service(reinit_db):
    token = await _seed("current@example.com", TERMS_VERSION)
    async with _client(token) as c:
        assert (await c.post("/api/v1/books/", json={"title": "Yes"})).status_code == 201
        assert (await c.get("/api/v1/books/")).status_code == 200


@pytest.mark.asyncio
async def test_the_exits_stay_open_without_acceptance(reinit_db):
    token = await _seed("exits@example.com", "2026-10-10")
    async with _client(token) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        assert (await c.get("/api/v1/billing/quotas")).status_code == 200
        token = (await c.post("/api/v1/users/me/export/token")).json()["token"]
        assert (await c.get("/api/v1/users/me/export", params={"token": token})).status_code == 200
        deleted = await c.delete("/api/v1/users/me")
        assert deleted.status_code == 200, deleted.text
