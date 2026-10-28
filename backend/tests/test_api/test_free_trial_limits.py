"""Free is a trial, not a plan you can write a book on (owner decision 2026-10-28).

Three limits, each pinned here:

- a lifetime AI allowance (``AI_QUOTA_FREE_TOTAL``) that never resets, instead
  of daily/monthly windows that would let a patient user write a whole book;
- AI drafts for one chapter only (``AI_QUOTA_FREE_DRAFT_CHAPTERS``);
- no book export (PDF, DOCX, EPUB, Markdown): that is what makes a book.

Pro keeps its daily/monthly windows and has none of the three. The staging E2E
account, BYPASS_AUTH and PLAN_ENFORCEMENT_ENABLED=false skip the plan gates.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

import app.api.dependencies as deps
from app.core.entitlements import TRIAL_DENIAL_MESSAGES
from app.db.usage import increment_usage
from tests.yield_dependencies import completes

pytestmark = pytest.mark.asyncio


def _trial_settings(**overrides):
    """Real metering, free = lifetime allowance only, pro = unmetered."""
    values = {
        "BYPASS_AUTH": False,
        "AI_QUOTA_ENABLED": True,
        "PLAN_ENFORCEMENT_ENABLED": True,
        "E2E_EXEMPT_EMAILS": "",
        "AI_QUOTA_FREE_DAILY": 0,
        "AI_QUOTA_FREE_MONTHLY": 0,
        "AI_QUOTA_FREE_TOTAL": 2,
        "AI_QUOTA_PRO_DAILY": 0,
        "AI_QUOTA_PRO_MONTHLY": 0,
        "AI_QUOTA_FREE_DRAFT_CHAPTERS": 1,
    }
    values.update(overrides)
    return [patch.object(deps.settings, k, v) for k, v in values.items()]


class _Patched:
    def __init__(self, patches):
        self.patches = patches

    def __enter__(self):
        for p in self.patches:
            p.start()

    def __exit__(self, *exc):
        for p in reversed(self.patches):
            p.stop()


def trial(**overrides):
    return _Patched(_trial_settings(**overrides))


# --- Lifetime AI allowance ------------------------------------------------


async def test_trial_allowance_is_lifetime_and_says_so(reinit_db, real_ai_quota):
    with trial():
        checker = completes(real_ai_quota())
        user = {"auth_id": "trial-1", "plan": "free"}
        await checker(current_user=user)
        await checker(current_user=user)
        with pytest.raises(HTTPException) as exc:
            await checker(current_user=user)

    assert exc.value.status_code == 429
    assert exc.value.headers["X-AI-Quota-Period"] == "trial"
    assert exc.value.headers["X-AI-Quota-Limit"] == "2"
    detail = exc.value.detail
    # The client tells a quota cap from a rate limit by this prefix.
    assert detail.startswith("AI usage limit reached")
    assert "2 AI generations in the free trial" in detail
    assert "doesn't reset" in detail
    assert "Upgrade to Pro" in detail
    assert "midnight" not in detail  # nothing resets, so promise nothing


async def test_trial_message_names_pros_monthly_allowance(reinit_db, real_ai_quota):
    with trial(AI_QUOTA_FREE_TOTAL=1, AI_QUOTA_PRO_MONTHLY=500):
        checker = completes(real_ai_quota())
        user = {"auth_id": "trial-2", "plan": "free"}
        await checker(current_user=user)
        with pytest.raises(HTTPException) as exc:
            await checker(current_user=user)
    assert "Upgrade to Pro for 500 per month" in exc.value.detail


async def test_pro_is_not_metered_by_the_trial_allowance(reinit_db, real_ai_quota):
    with trial(AI_QUOTA_FREE_TOTAL=1):
        checker = completes(real_ai_quota())
        pro = {"auth_id": "pro-1", "plan": "pro"}
        for _ in range(5):
            await checker(current_user=pro)


async def test_trial_counter_never_expires(reinit_db, real_ai_quota):
    from app.db.base import get_collection

    with trial():
        checker = completes(real_ai_quota())
        await checker(current_user={"auth_id": "trial-3", "plan": "free"})

    coll = await get_collection("usage_counters")
    doc = await coll.find_one({"_id": "trial-3:trial:total"})
    assert doc["count"] == 1
    assert "expires_at" not in doc  # the TTL index can't reap it


async def test_increment_usage_without_ttl_sets_no_expiry(reinit_db):
    from app.db.base import get_collection

    assert await increment_usage("user-x", "trial:total", None) == 1
    assert await increment_usage("user-x", "trial:total", None) == 2
    coll = await get_collection("usage_counters")
    assert "expires_at" not in await coll.find_one({"_id": "user-x:trial:total"})


# --- One chapter of drafts ------------------------------------------------


async def _seed_user(auth_id, plan="free", email="someone@example.com"):
    from app.db.base import users_collection

    await users_collection.insert_one({"auth_id": auth_id, "plan": plan, "email": email})
    return {"auth_id": auth_id, "plan": plan, "email": email}


async def _drafted(auth_id):
    from app.db.base import users_collection

    doc = await users_collection.find_one({"auth_id": auth_id})
    return doc.get("trial_draft_chapters", [])


async def test_first_drafted_chapter_is_the_trial_chapter(reinit_db):
    user = await _seed_user("draft-1")
    with trial():
        await deps.claim_trial_draft_chapter(user, "b1", "ch1")
        await deps.claim_trial_draft_chapter(user, "b1", "ch1")  # redraft: fine
        with pytest.raises(HTTPException) as exc:
            await deps.claim_trial_draft_chapter(user, "b1", "ch2")

    assert exc.value.status_code == 402
    assert exc.value.detail["error"] == TRIAL_DENIAL_MESSAGES["generate_draft"]
    assert exc.value.headers["X-Entitlement-Feature"] == "generate_draft"
    assert await _drafted("draft-1") == ["b1:ch1"]


async def test_the_same_chapter_id_in_another_book_is_another_chapter(reinit_db):
    user = await _seed_user("draft-2")
    with trial():
        await deps.claim_trial_draft_chapter(user, "b1", "ch1")
        with pytest.raises(HTTPException):
            await deps.claim_trial_draft_chapter(user, "b2", "ch1")


async def test_draft_cap_is_configurable(reinit_db):
    user = await _seed_user("draft-3")
    with trial(AI_QUOTA_FREE_DRAFT_CHAPTERS=2):
        await deps.claim_trial_draft_chapter(user, "b1", "ch1")
        await deps.claim_trial_draft_chapter(user, "b1", "ch2")
        with pytest.raises(HTTPException):
            await deps.claim_trial_draft_chapter(user, "b1", "ch3")
    assert sorted(await _drafted("draft-3")) == ["b1:ch1", "b1:ch2"]


async def test_concurrent_drafts_cannot_both_take_the_last_slot(reinit_db):
    import asyncio

    user = await _seed_user("draft-4")
    with trial():
        results = await asyncio.gather(
            *(deps.claim_trial_draft_chapter(user, "b1", f"ch{i}") for i in range(5)),
            return_exceptions=True,
        )
    assert sum(r is None for r in results) == 1
    assert len(await _drafted("draft-4")) == 1


@pytest.mark.parametrize(
    "plan, overrides",
    [
        ("pro", {}),
        ("free", {"BYPASS_AUTH": True}),
        ("free", {"PLAN_ENFORCEMENT_ENABLED": False}),
        ("free", {"AI_QUOTA_FREE_DRAFT_CHAPTERS": 0}),
    ],
)
async def test_draft_cap_skipped(reinit_db, plan, overrides):
    user = await _seed_user(f"draft-skip-{plan}", plan=plan)
    with trial(**overrides):
        for chapter in ("ch1", "ch2", "ch3"):
            await deps.claim_trial_draft_chapter(user, "b1", chapter)
    assert await _drafted(user["auth_id"]) == []


async def test_draft_cap_skips_the_staging_e2e_account(reinit_db):
    user = await _seed_user("draft-e2e", email="e2e@example.com")
    with trial(E2E_EXEMPT_EMAILS="e2e@example.com"), \
         patch.object(deps, "is_production_env", return_value=False):
        for chapter in ("ch1", "ch2"):
            await deps.claim_trial_draft_chapter(user, "b1", chapter)


# --- The draft endpoint uses the cap after its own checks -------------------


def _book(owner):
    chapters = [
        {"id": cid, "title": f"Chapter {cid}", "description": "d", "level": 1,
         "order": i, "subchapters": []}
        for i, cid in enumerate(("ch1", "ch2"), start=1)
    ]
    return {
        "_id": "trial_book",
        "owner_id": owner,
        "title": "Trial Book",
        "table_of_contents": {"chapters": chapters, "total_chapters": 2, "version": 1},
    }


_DRAFT_REQUEST = {
    "question_responses": [{"question": "What is this chapter about?", "answer": "Testing."}],
    "writing_style": "educational",
    "target_length": 1000,
}

_AI_RESULT = {
    "success": True,
    "draft": "# Chapter\n\nText.",
    "metadata": {"word_count": 2},
    "suggestions": [],
}


async def test_draft_endpoint_drafts_one_chapter_then_asks_for_pro(auth_client_factory):
    client = await auth_client_factory()
    ai = AsyncMock(return_value=_AI_RESULT)
    with trial(AI_QUOTA_FREE_TOTAL=0), \
         patch("app.api.endpoints.chapter_ai.get_book_metadata_by_id",
               AsyncMock(return_value=_book("test-auth-id-123"))), \
         patch("app.api.endpoints.chapter_ai.ai_service.generate_chapter_draft", ai):
        first = await client.post(
            "/api/v1/books/trial_book/chapters/ch1/generate-draft", json=_DRAFT_REQUEST
        )
        again = await client.post(
            "/api/v1/books/trial_book/chapters/ch1/generate-draft", json=_DRAFT_REQUEST
        )
        other = await client.post(
            "/api/v1/books/trial_book/chapters/ch2/generate-draft", json=_DRAFT_REQUEST
        )

    assert first.status_code == 200, first.text
    assert again.status_code == 200, again.text
    assert other.status_code == 402
    assert other.json()["detail"]["error"] == TRIAL_DENIAL_MESSAGES["generate_draft"]
    assert ai.await_count == 2  # the refused chapter never reached the model


async def test_a_refused_draft_does_not_use_the_trial_chapter(auth_client_factory):
    """Someone else's book is refused before the cap, so it pins nothing."""
    client = await auth_client_factory()
    with trial(AI_QUOTA_FREE_TOTAL=0), \
         patch("app.api.endpoints.chapter_ai.get_book_metadata_by_id",
               AsyncMock(return_value=_book("somebody-else"))):
        resp = await client.post(
            "/api/v1/books/trial_book/chapters/ch1/generate-draft", json=_DRAFT_REQUEST
        )
    assert resp.status_code == 403
    assert await _drafted("test-auth-id-123") == []


# --- Export is Pro ----------------------------------------------------------


@pytest.mark.parametrize("fmt", ["pdf", "docx", "epub", "markdown"])
async def test_free_cannot_export_a_book(auth_client_factory, fmt):
    client = await auth_client_factory()
    with trial():
        resp = await client.get(f"/api/v1/books/any-book/export/{fmt}")
    assert resp.status_code == 402
    body = resp.json()["detail"]
    assert body["error"] == TRIAL_DENIAL_MESSAGES["export"]
    assert resp.headers["X-Entitlement-Feature"] == "export"


async def test_restricted_export_refusal_keeps_the_generic_message(auth_client_factory):
    client = await auth_client_factory(overrides={"plan": "restricted"})
    with trial():
        resp = await client.get("/api/v1/books/any-book/export/pdf")
    assert resp.status_code == 402
    assert resp.json()["detail"]["error"] == "Your plan does not include this feature."


async def test_free_can_still_download_their_account_data(auth_client_factory):
    """Owning your data isn't a Pro feature: the account JSON export stays open."""
    client = await auth_client_factory()
    with trial():
        token = (await client.post("/api/v1/users/me/export/token")).json()["token"]
        resp = await client.get("/api/v1/users/me/export", params={"token": token})
    assert resp.status_code == 200, resp.text
