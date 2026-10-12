"""A failure the code handles and carries on from is still reported (#996).

No log line reaches Sentry (#808), and the SDK reports only what is raised: an
unhandled exception, or a 5xx a route raises. A failure that is logged and
carried on from left no trace outside the container log: an audit record that
could not be written, a session that could not be checked, a daily purge that
failed, a deleted user's files still in storage, a customer billed twice.

Each of those now goes through ``report_failure``. The real Sentry SDK, sending
to a list; real MongoDB.
"""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sentry_sdk
from bson import ObjectId
from fastapi import FastAPI
from starlette.requests import Request

from app import main
from app.core import better_auth_session, reporting
from app.core.config import settings
from app.core.reporting import report_failure
from app.db import book as book_dao
from app.db import user as user_dao
from app.services.chapter_access_service import chapter_access_service
from tests.session_cookies import signed_session_cookie
from tests.test_api.test_rate_limit_routes import _create_book, _seed_toc, _small_toc
from tests.test_api import test_stripe_webhook_current_subscription as stripe_tests

pytestmark = pytest.mark.asyncio

# The webhook tests' own client: the webhook router alone, Stripe test settings, a fresh database.
webhook_client = stripe_tests.webhook_client

SENTINEL = "SENTINEL-what-the-user-wrote"


@pytest.fixture
def reports(monkeypatch):
    """The SDK as the app starts it, sending to a list. Inert again afterwards."""
    sent: list = []
    real_init = sentry_sdk.init
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://key@sentry.invalid/1")
    monkeypatch.setattr(sentry_sdk, "init", lambda **options: real_init(**options, transport=sent.append))
    monkeypatch.setattr(reporting, "_last_reported", {})
    main._init_sentry()
    yield sent
    real_init()


def _kinds(reports) -> list[str]:
    return [r["fingerprint"][1] for r in reports if r.get("fingerprint", [""])[0] == "handled"]


def _said(reports) -> str:
    return json.dumps(reports, default=str)


class TestTheOneFunctionEveryReportGoesThrough:
    async def test_an_error_is_sent_once_with_its_kind(self, reports):
        try:
            raise RuntimeError("storage is down")
        except RuntimeError as error:
            report_failure("delete-cover", error)

        assert [(r["level"], r["fingerprint"]) for r in reports] == [("error", ["handled", "delete-cover"])]
        assert reports[0]["exception"]["values"][-1]["type"] == "RuntimeError"

    async def test_a_message_is_sent_when_there_is_no_exception(self, reports):
        report_failure("startup-indexes", message="Startup index creation failed")

        assert [(r["message"], r["fingerprint"]) for r in reports] == [
            ("Startup index creation failed", ["handled", "startup-indexes"])
        ]

    async def test_the_same_kind_again_within_five_minutes_is_not_sent(self, reports):
        for _ in range(3):
            report_failure("session-validation", RuntimeError("database is away"))

        assert _kinds(reports) == ["session-validation"]

    async def test_it_is_sent_again_after_five_minutes(self, reports, monkeypatch):
        report_failure("session-validation", RuntimeError("database is away"))
        clock = reporting.time.monotonic()
        monkeypatch.setattr(reporting.time, "monotonic", lambda: clock + reporting.REPORT_AGAIN_SECONDS + 1)
        report_failure("session-validation", RuntimeError("database is away"))

        assert _kinds(reports) == ["session-validation", "session-validation"]

    async def test_another_kind_is_not_held_back_by_it(self, reports):
        report_failure("session-validation", RuntimeError("database is away"))
        report_failure("audit-log", RuntimeError("database is away"))

        assert _kinds(reports) == ["session-validation", "audit-log"]

    async def test_reporting_never_breaks_what_called_it(self, reports, monkeypatch):
        monkeypatch.setattr(sentry_sdk, "capture_exception", MagicMock(side_effect=RuntimeError("sentry is down")))

        report_failure("audit-log", RuntimeError("database is away"))


class TestADatabaseErrorDoesNotBringTheDocumentWithIt:
    async def test_the_detail_the_driver_appends_is_cut(self, reports):
        """pymongo ends a write error with ``full error: {...}``, and for a document that
        fails a schema rule that holds the value that failed. Handled database errors are
        reported by hand now, so more of these reach Sentry than before."""
        detail = "{'code': 121, 'errInfo': {'details': {'consideredValue': '%s'}}}" % SENTINEL
        report_failure("access-log", RuntimeError(f"Document failed validation, full error: {detail}"))

        assert reports[0]["exception"]["values"][-1]["value"] == "Document failed validation"
        assert SENTINEL not in _said(reports)


class TestAnAccessRecordThatCouldNotBeWritten:
    async def test_the_request_is_answered_and_the_gap_in_the_record_is_reported(self, auth_client_factory, reports):
        """Eight routes log who read or changed a chapter, and carry on if that fails."""
        api = await auth_client_factory()
        book_id = await _create_book(api)
        toc = _small_toc()
        toc["chapters"][0]["title"] = SENTINEL
        await _seed_toc(book_id, toc)
        chapter_id = toc["chapters"][0]["id"]

        with patch.object(chapter_access_service, "log_access", AsyncMock(side_effect=RuntimeError("database is away"))):
            first = await api.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}/content")
            await api.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}/content")

        assert first.status_code == 200
        assert _kinds(reports) == ["access-log"]
        assert SENTINEL not in _said(reports)


class TestASessionThatCouldNotBeChecked:
    def _request(self, token: str) -> Request:
        cookie = f"better-auth.session_token={signed_session_cookie(token)}"
        return Request({"type": "http", "method": "GET", "path": "/", "headers": [(b"cookie", cookie.encode())]})

    async def test_is_reported_and_the_request_goes_on_as_signed_out(self, reports):
        with patch.object(better_auth_session, "get_collection", AsyncMock(side_effect=RuntimeError("database is away"))):
            session = await better_auth_session.validate_better_auth_session(self._request(SENTINEL))

        assert session is None
        assert _kinds(reports) == ["session-validation"]
        assert SENTINEL not in _said(reports)

    async def test_so_is_a_user_who_could_not_be_looked_up(self, reports):
        with patch.object(better_auth_session, "get_collection", AsyncMock(side_effect=RuntimeError("database is away"))):
            user = await better_auth_session.get_better_auth_user(str(ObjectId()))

        assert user is None
        assert _kinds(reports) == ["session-validation"]


class TestStartUpAndTheDailyPurge:
    @pytest.fixture(autouse=True)
    def own_export_pool(self, monkeypatch):
        """Shutdown closes the export pool; hand it one that no other test uses."""
        monkeypatch.setattr("app.services.export_service.export_executor", ThreadPoolExecutor(1))

    async def _start(self):
        async with main.lifespan(FastAPI()):
            await asyncio.sleep(0.05)  # the purge runs as a task of its own

    async def test_indexes_that_could_not_be_created(self, motor_reinit_db, reports):
        from app.db.indexing_strategy import ChapterTabIndexManager

        failed = AsyncMock(return_value={"success": False, "message": f"index on {SENTINEL} failed"})
        with patch.object(ChapterTabIndexManager, "create_all_indexes", failed):
            await self._start()

        assert _kinds(reports) == ["startup-indexes"]
        assert SENTINEL not in _said(reports)

    async def test_accounts_that_could_not_be_marked_verified(self, motor_reinit_db, reports):
        with patch.object(user_dao, "grandfather_unverified_accounts", AsyncMock(side_effect=RuntimeError("database is away"))):
            await self._start()

        assert _kinds(reports) == ["startup-verify-accounts"]

    async def test_a_purge_of_expired_accounts_that_failed(self, motor_reinit_db, reports):
        with patch.object(user_dao, "purge_expired_users", AsyncMock(side_effect=RuntimeError("database is away"))):
            await self._start()

        assert _kinds(reports) == ["purge-accounts"]


class TestADeletedUsersFilesStillInStorage:
    async def test_a_cover_that_could_not_be_deleted(self, reports):
        from app.services.file_upload_service import FileUploadService

        with patch.object(FileUploadService, "delete_cover_image", AsyncMock(side_effect=RuntimeError("storage is down"))):
            await book_dao._delete_cover_files({"_id": ObjectId(), "cover_image_url": f"/uploads/{SENTINEL}.png"})

        assert _kinds(reports) == ["delete-files"]
        assert SENTINEL not in _said(reports)

    async def test_books_that_could_not_be_deleted_for_a_user(self, reports):
        broken = MagicMock()
        broken.delete_many = AsyncMock(side_effect=RuntimeError("database is away"))
        broken.find = MagicMock(side_effect=RuntimeError("database is away"))
        with patch.object(user_dao, "books_collection", broken):
            deleted = await user_dao.delete_user_books("auth-1")

        assert deleted is False
        assert _kinds(reports) == ["delete-user-data"]


class TestACustomerBilledTwice:
    async def test_is_reported_by_the_event_to_look_up_and_not_by_who_it_is(self, webhook_client, reports):
        await stripe_tests._seed_pro_on("sub_A")

        response = await stripe_tests._post_signed(
            webhook_client, stripe_tests.event(event_id="evt_second_sub", subscription_id="sub_B")
        )

        assert response.json()["status"] == "not_current_subscription"
        assert [r["fingerprint"] for r in reports] == [["stripe-webhook", "second-subscription"]]
        assert "evt_second_sub" in reports[0]["message"]
        assert "auth-stripe-1" not in _said(reports) and "cus_test_1" not in _said(reports)
