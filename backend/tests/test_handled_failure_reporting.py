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
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sentry_sdk
from bson import ObjectId
from fastapi import FastAPI
from pymongo.errors import ServerSelectionTimeoutError
from starlette.requests import Request

from app import main
from app.core import better_auth_session, reporting
from app.core.config import settings
from app.core.reporting import report_failure
from app.db import book as book_dao
from app.db import user as user_dao
from app.services import file_upload_service
from app.services.chapter_access_service import chapter_access_service
from app.services.file_upload_service import FileUploadService
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

    async def test_a_report_that_could_not_be_sent_does_not_silence_the_next_one(self, reports, monkeypatch):
        with monkeypatch.context() as broken:
            broken.setattr(sentry_sdk, "capture_exception", MagicMock(side_effect=RuntimeError("sentry is down")))
            report_failure("purge-accounts", RuntimeError("database is away"))

        report_failure("purge-accounts", RuntimeError("database is away"))

        assert _kinds(reports) == ["purge-accounts"]


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

    async def test_is_reported_and_is_not_taken_for_a_session_that_is_not_there(self, reports):
        away = AsyncMock(side_effect=ServerSelectionTimeoutError("no primary"))
        with patch.object(better_auth_session, "get_collection", away):
            with pytest.raises(better_auth_session.SessionStoreUnavailable):
                await better_auth_session.validate_better_auth_session(self._request(SENTINEL))

        assert _kinds(reports) == ["session-validation"]
        assert SENTINEL not in _said(reports)

    async def test_so_is_a_user_who_could_not_be_looked_up(self, reports):
        away = AsyncMock(side_effect=ServerSelectionTimeoutError("no primary"))
        with patch.object(better_auth_session, "get_collection", away):
            with pytest.raises(better_auth_session.SessionStoreUnavailable):
                await better_auth_session.get_better_auth_user(str(ObjectId()))

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
    """The upload service catches its own failures and never raises, so that is
    where a file left behind has to be reported from."""

    @pytest.fixture
    def stored(self, tmp_path, monkeypatch):
        """A cover and an avatar on local disk, named as the service names them."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(file_upload_service, "get_cloud_storage_service", lambda: None)
        book_id, user_id = str(ObjectId()), "auth-closing"
        cover = tmp_path / "uploads" / "cover_images" / f"{book_id}_{'a' * 32}.png"
        avatar = tmp_path / "uploads" / "profile_pictures" / f"{user_id}_{'b' * 32}.png"
        for file in (cover, avatar):
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"image")
        return {"book_id": book_id, "user_id": user_id, "cover": cover, "avatar": avatar}

    async def test_a_cover_the_disk_would_not_let_go_of(self, stored, reports, monkeypatch):
        monkeypatch.setattr(Path, "unlink", MagicMock(side_effect=PermissionError("read-only file system")))

        await FileUploadService().delete_cover_image(stored["book_id"], f"/uploads/cover_images/{stored['cover'].name}")

        assert stored["cover"].exists()
        assert _kinds(reports) == ["delete-files"]

    async def test_an_avatar_the_disk_would_not_let_go_of(self, stored, reports, monkeypatch):
        monkeypatch.setattr(Path, "unlink", MagicMock(side_effect=PermissionError("read-only file system")))

        await FileUploadService().delete_profile_picture(
            stored["user_id"], f"/uploads/profile_pictures/{stored['avatar'].name}"
        )

        assert stored["avatar"].exists()
        assert _kinds(reports) == ["delete-files"]

    @pytest.mark.parametrize("which", ["cover", "avatar"])
    async def test_a_file_the_cloud_provider_did_not_delete(self, stored, reports, which):
        """The provider's own failure is caught a layer down and comes back as False."""
        service = FileUploadService()
        service.cloud_storage = MagicMock(delete_image=AsyncMock(return_value=False))

        if which == "cover":
            await service.delete_cover_image(stored["book_id"], f"https://cdn.invalid/{SENTINEL}.png")
        else:
            await service.delete_profile_picture(stored["user_id"], f"https://cdn.invalid/{SENTINEL}.png")

        assert _kinds(reports) == ["delete-files"]
        assert SENTINEL not in _said(reports)

    async def test_a_file_that_was_deleted_is_not_a_report(self, stored, reports):
        await FileUploadService().delete_cover_image(stored["book_id"], f"/uploads/cover_images/{stored['cover'].name}")

        assert not stored["cover"].exists()
        assert reports == []

    async def test_storage_that_cannot_even_be_set_up_when_a_book_is_deleted(self, reports):
        """The one way the callers' own handlers are reached: the service cannot be constructed."""
        with patch.object(FileUploadService, "__init__", MagicMock(side_effect=RuntimeError("no upload storage"))):
            await book_dao._delete_cover_files({"_id": ObjectId(), "cover_image_url": f"/uploads/{SENTINEL}.png"})

        assert _kinds(reports) == ["delete-files"]
        assert SENTINEL not in _said(reports)

    async def test_or_when_an_account_is_closed(self, motor_reinit_db, reports):
        await user_dao.create_user(
            {"auth_id": "auth-closing", "email": "closing@example.com", "avatar_url": f"/uploads/{SENTINEL}.png"}
        )
        with patch.object(FileUploadService, "__init__", MagicMock(side_effect=RuntimeError("no upload storage"))):
            closed = await user_dao.delete_user("auth-closing")

        assert closed is True, "the account is still closed; only the file was left behind"
        assert _kinds(reports) == ["delete-files"]
        assert SENTINEL not in _said(reports)


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

    @pytest.mark.parametrize(
        "delivery, kind",
        [
            ({"status": "a_status_stripe_added_later"}, "unknown-status"),
            ({"price_id": "price_nobody_configured"}, "price-not-matched"),
        ],
        ids=["a status this app does not know", "a paying subscription that matches no price"],
    )
    async def test_so_are_the_two_ways_a_paying_user_ends_up_on_the_wrong_plan(self, webhook_client, reports, delivery, kind):
        await stripe_tests._seed_pro_on("sub_A")

        await stripe_tests._post_signed(
            webhook_client, stripe_tests.event(event_id="evt_wrong_plan", subscription_id="sub_A", **delivery)
        )

        assert [r["fingerprint"] for r in reports] == [["stripe-webhook", kind]]
        assert "evt_wrong_plan" in reports[0]["message"]
        assert "auth-stripe-1" not in _said(reports) and "cus_test_1" not in _said(reports)
