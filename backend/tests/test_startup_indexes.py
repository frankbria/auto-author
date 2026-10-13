"""Startup index creation for books + chapter_access_logs (issue #183).

ChapterTabIndexManager held the book owner_id indexes and the 90-day
access-log TTL but ran nowhere at runtime. These tests pin that the manager
creates them and that the app lifespan actually invokes it.
"""
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

from app import main
from app.db import base, questions
from app.db.audit_log import ensure_audit_log_indexes
from app.db.indexing_strategy import ChapterTabIndexManager
from app.main import app

NINETY_DAYS = 60 * 60 * 24 * 90


async def _warm_collections():
    """First createIndexes after a drop_database can be silently lost; do a
    real write on each collection so the index builds land."""
    await base._db.books.insert_one({"warm": True})
    await base._db.chapter_access_logs.insert_one({"warm": True})
    await base._db.audit_logs.insert_one({"warm": True, "action": "warm"})


async def _index_map(collection):
    return {idx["name"]: idx for idx in await collection.list_indexes().to_list(None)}


@pytest.mark.asyncio
async def test_create_all_indexes_creates_owner_and_ttl_indexes(motor_reinit_db):
    await _warm_collections()
    result = await ChapterTabIndexManager(base._db).create_all_indexes()
    assert result["success"] is True

    books_indexes = await _index_map(base._db.books)
    assert "owner_book_id_idx" in books_indexes
    assert "owner_updated_idx" in books_indexes

    access_indexes = await _index_map(base._db.chapter_access_logs)
    assert "access_logs_ttl_idx" in access_indexes
    assert access_indexes["access_logs_ttl_idx"]["expireAfterSeconds"] == NINETY_DAYS
    for name in (
        "user_book_timestamp_idx",
        "book_chapter_timestamp_idx",
        "user_access_type_timestamp_idx",
        "user_book_access_type_idx",
    ):
        assert name in access_indexes
    assert access_indexes["user_book_access_type_idx"]["partialFilterExpression"] == {
        "access_type": "tab_state"
    }


@pytest.mark.asyncio
async def test_create_all_indexes_is_idempotent(motor_reinit_db):
    await _warm_collections()
    manager = ChapterTabIndexManager(base._db)
    assert (await manager.create_all_indexes())["success"] is True
    assert (await manager.create_all_indexes())["success"] is True

    books_indexes = await _index_map(base._db.books)
    assert "owner_book_id_idx" in books_indexes
    access_indexes = await _index_map(base._db.chapter_access_logs)
    assert "access_logs_ttl_idx" in access_indexes


@pytest.mark.asyncio
async def test_no_text_index_on_books(motor_reinit_db):
    """The unused chapter-content text index was removed (no $text queries;
    it re-tokenized full chapter content on every autosave), and a stale one
    left by an earlier manual run gets dropped."""
    await _warm_collections()
    await base._db.books.create_index(
        [("table_of_contents.chapters.title", "text")],
        name="chapter_content_text_idx",
    )
    await ChapterTabIndexManager(base._db).create_all_indexes()

    books_indexes = await _index_map(base._db.books)
    assert "chapter_content_text_idx" not in books_indexes


@pytest.mark.asyncio
async def test_lifespan_creates_owner_and_ttl_indexes(motor_reinit_db):
    """The actual #183 bug: app startup never created these indexes. Run the
    real lifespan and assert they exist afterwards."""
    await _warm_collections()
    async with app.router.lifespan_context(app):
        # Beside the server, not in front of it (#1012): wait for it here.
        await app.state.database_prepared

    books_indexes = await _index_map(base._db.books)
    assert "owner_book_id_idx" in books_indexes

    access_indexes = await _index_map(base._db.chapter_access_logs)
    assert "access_logs_ttl_idx" in access_indexes
    assert access_indexes["access_logs_ttl_idx"]["expireAfterSeconds"] == NINETY_DAYS


@pytest.mark.asyncio
async def test_lifespan_purges_expired_deactivated_accounts(motor_reinit_db):
    """#954: the 18-month purge needs no one to act. A running app does it."""
    users = base._db.users
    await users.insert_one(
        {
            "auth_id": "expired",
            "deleted_at": datetime(2025, 4, 1),
            "purge_at": datetime(2026, 10, 1),
            "retained": {"email": "old@example.com"},
        }
    )
    async with app.router.lifespan_context(app):
        for _ in range(100):
            if "retained" not in await users.find_one({"auth_id": "expired"}):
                break
            await asyncio.sleep(0.05)

    assert set(await users.find_one({"auth_id": "expired"})) == {
        "_id", "auth_id", "deleted_at",
    }


def _assert_audit_indexes(indexes):
    ttl = indexes["audit_logs_ttl_idx"]
    assert ttl["key"] == {"expires_at": 1}
    assert ttl["expireAfterSeconds"] == 0
    assert indexes["actor_timestamp_idx"]["key"] == {"actor_id": 1, "timestamp": -1}


@pytest.mark.asyncio
async def test_ensure_audit_log_indexes_creates_ttl_and_actor_indexes(motor_reinit_db):
    await _warm_collections()
    await ensure_audit_log_indexes()
    await ensure_audit_log_indexes()  # idempotent
    _assert_audit_indexes(await _index_map(base._db.audit_logs))


@pytest.mark.asyncio
async def test_lifespan_creates_audit_log_indexes(motor_reinit_db):
    await _warm_collections()
    async with app.router.lifespan_context(app):
        await app.state.database_prepared
    _assert_audit_indexes(await _index_map(base._db.audit_logs))


class TestStartingWhileTheDatabaseIsAway:
    """#1012. Start-up created its indexes one after another before the server took a request,
    and each waited the driver's thirty seconds for a database that was not there. A backend
    restarted during an outage answered nothing, its liveness route included, for over ten
    minutes. The work now runs beside the server and waits for the database itself."""

    @pytest.fixture(autouse=True)
    def own_export_pool(self, monkeypatch):
        """Shutdown closes the export pool; hand it one that no other test uses."""
        monkeypatch.setattr("app.services.export_service.export_executor", ThreadPoolExecutor(1))

    @pytest.fixture
    def away(self, monkeypatch):
        """Point the app at an address nothing listens on. Returns a function that brings the
        real database back."""
        real = base._db
        client = AsyncIOMotorClient("mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=300")
        monkeypatch.setattr(base, "_db", client["nowhere"])
        monkeypatch.setattr(main, "DATABASE_RETRY_SECONDS", 0.05)
        yield lambda: monkeypatch.setattr(base, "_db", real)
        client.close()

    # Each of these enters the lifespan under a time limit: a start-up that waits for the
    # database would otherwise hang the run instead of failing it.

    @pytest.mark.asyncio
    async def test_start_up_does_not_wait_for_it(self, monkeypatch):
        # Its own absent database, slower to give up than the fixture's: one failed attempt
        # takes three seconds, so "under one" holds on a loaded machine and still cannot be
        # met by a start-up that makes even a single attempt first.
        client = AsyncIOMotorClient("mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=3000")
        monkeypatch.setattr(base, "_db", client["nowhere"])
        started = time.monotonic()
        async with asyncio.timeout(30):
            async with main.lifespan(FastAPI()) as _:
                took = time.monotonic() - started
        client.close()

        assert took < 1, f"start-up took {took:.2f}s; one failed attempt at the database alone is 3s"

    @pytest.mark.asyncio
    async def test_the_liveness_route_answers(self, away):
        async with asyncio.timeout(10):
            async with main.lifespan(app):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    response = await client.get("/api/v1/health/live")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_the_indexes_are_created_when_it_comes_back_without_a_restart(self, motor_reinit_db, away, monkeypatch):
        reported = []
        monkeypatch.setattr(main, "report_failure", lambda kind, *args, **kwargs: reported.append(kind))
        bring_it_back = away
        bring_it_back()
        await _warm_collections()
        await base._db.users.insert_one({"warm": True, "auth_id": "warm", "email": "warm@example.com"})
        await base._db.question_responses.insert_one({"warm": True})
        monkeypatch.setattr(base, "_db", AsyncIOMotorClient("mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=300")["nowhere"])
        served = FastAPI()
        # The first thing the work does. Asserting only on indexes afterwards cannot tell
        # waiting from going ahead: steps that fail while the database is away fail quietly,
        # and the later ones succeed once it is back.
        begun = []
        first_step = questions.ensure_question_indexes

        async def first_step_watched():
            begun.append(True)
            await first_step()

        monkeypatch.setattr(questions, "ensure_question_indexes", first_step_watched)

        async with asyncio.timeout(60):
            async with main.lifespan(served):
                await asyncio.sleep(1)  # long enough for more than one failed attempt
                assert not served.state.database_prepared.done(), "it gave up, or thought an absent database was ready"
                assert not begun, "the work went ahead before the database could be reached"
                assert set(reported) == {"startup-database"}
                bring_it_back()
                await served.state.database_prepared

        # The first step's indexes as well as the last's: work that went ahead while the
        # database was away would have failed its early steps and still finished its late ones.
        assert "question_user_idx" in await _index_map(base._db.question_responses)
        assert "auth_id_unique_idx" in await _index_map(base._db.users)
        assert "owner_book_id_idx" in await _index_map(base._db.books)
        assert "access_logs_ttl_idx" in await _index_map(base._db.chapter_access_logs)

    @pytest.mark.asyncio
    async def test_the_work_is_done_again_if_the_database_went_away_while_it_was_being_done(self, motor_reinit_db, away, monkeypatch):
        """Each step logs its own failure and carries on. A database that answers the first
        ping and then goes leaves every step "finished" and nothing created. Review found it."""
        reported = []
        monkeypatch.setattr(main, "report_failure", lambda kind, *args, **kwargs: reported.append(kind))
        bring_it_back = away
        bring_it_back()
        await _warm_collections()
        gone = AsyncIOMotorClient("mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=300")["nowhere"]
        passes = []
        first_step = questions.ensure_question_indexes

        async def first_step_as_the_database_goes():
            passes.append(True)
            if len(passes) == 1:
                monkeypatch.setattr(base, "_db", gone)
            await first_step()

        monkeypatch.setattr(questions, "ensure_question_indexes", first_step_as_the_database_goes)
        served = FastAPI()

        async with asyncio.timeout(120):
            async with main.lifespan(served):
                while "startup-database" not in reported:  # the first pass is over, and it is waiting again
                    await asyncio.sleep(0.1)
                assert not served.state.database_prepared.done(), "it called the work done with the database gone"
                bring_it_back()
                await served.state.database_prepared

        assert len(passes) == 2
        assert "owner_book_id_idx" in await _index_map(base._db.books)
        assert "access_logs_ttl_idx" in await _index_map(base._db.chapter_access_logs)
