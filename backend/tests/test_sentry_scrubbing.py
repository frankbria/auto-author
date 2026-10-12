"""What a backend error report carries to Sentry, and what it must not (#808).

The SDK ran on its defaults: frame locals, request bodies, every INFO log line
as a breadcrumb. A probe found manuscript text, a session cookie and an email
address in one event, and two events for one failed request. These tests start
the real SDK the way the app does, with a list in place of the network.
"""

import json
import logging
import os
from pathlib import Path

import pytest
import sentry_sdk
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from pydantic import BaseModel

from app import main
from app.core.config import settings
from app.main import app

REPO = Path(__file__).resolve().parents[2]
PROBE = "/__sentry_probe"

LOCAL = "LOCAL-SENTINEL a paragraph of the manuscript"
BODY = "BODY-SENTINEL the chapter being saved"
CRUMB = "CRUMB-SENTINEL@example.com"
KEYED = "KEYED-SENTINEL the draft"
DUPLICATE = "DUPLICATE-SENTINEL@example.com"
COOKIE = "COOKIE-SENTINEL"
QUERY = "QUERY-SENTINEL"
REJECTED = "REJECTED-SENTINEL"
LOGGED = "LOGGED-SENTINEL the question about chapter two"
REFERER = "REFERER-SENTINEL"
STORED = "STORED-SENTINEL the chapter as saved"
PROMPT = "PROMPT-SENTINEL the chapter sent to the model"

log = logging.getLogger("app.probe")


class _Chapter(BaseModel):
    words: int


def _scratch(collection: str):
    """A collection in the test database, on a client made after the SDK started,
    as the app's is: the SDK watches only the clients created after it."""
    uri = os.environ.get("TEST_MONGO_URI", "mongodb://localhost:27017/auto-author-test")
    return AsyncIOMotorClient(uri).get_default_database()[collection]


async def _fail(payload: dict):
    manuscript = LOCAL  # noqa: F841 - a frame local, which is where the probe found text
    log.info("signed in %s", CRUMB)
    # What 133 lines in the app do, some of them with what the user wrote.
    log.error(f"Question dict: {{'question_text': '{LOGGED}'}}")
    # Attached by key and nested, so the scrubber has to look inside.
    sentry_sdk.add_breadcrumb(category="chapter", data={"chapter": {"content": KEYED}})
    # MongoDB's own duplicate-key error, which quotes the colliding value.
    users = _scratch("sentry_probe_users")
    await users.create_index("email", unique=True)
    await users.insert_one({"email": DUPLICATE})
    try:
        await users.insert_one({"email": DUPLICATE})
    finally:
        await users.drop()


async def _work_then_fail():
    """What a real request does before it fails: writes the chapter, asks the model."""
    chapters = _scratch("sentry_probe")
    await chapters.insert_one({"title": STORED, "content": STORED})
    await chapters.update_one({"title": STORED}, {"$set": {"content": STORED + " again"}})
    await chapters.drop()
    try:  # nothing listens on port 1; the app handles a model failure like this
        await AsyncOpenAI(api_key="k", base_url="http://127.0.0.1:1/v1", max_retries=0).chat.completions.create(
            model="m", messages=[{"role": "user", "content": PROMPT}]
        )
    except Exception:
        pass
    raise RuntimeError("after the work")


async def _reject():
    _Chapter.model_validate({"words": REJECTED})


@pytest.fixture
def events(monkeypatch):
    """The SDK as the app starts it, sending to a list. Inert again afterwards."""
    sent: list = []
    real_init = sentry_sdk.init
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://key@sentry.invalid/1")
    monkeypatch.setattr(sentry_sdk, "init", lambda **options: real_init(**options, transport=sent.append))
    main._init_sentry()
    yield sent
    real_init()


@pytest.fixture
def api():
    app.add_api_route(PROBE, _fail, methods=["POST"])
    app.add_api_route(PROBE + "/rejected", _reject, methods=["GET"])
    app.add_api_route(PROBE + "/work", _work_then_fail, methods=["POST"])
    yield TestClient(app, raise_server_exceptions=False)
    del app.router.routes[-3:]


def _fail_a_request(api: TestClient):
    return api.post(
        f"{PROBE}?q={QUERY}",
        # Under a name the scrubber does not know: only not sending bodies keeps it out.
        json={"notes": BODY},
        headers={
            "Cookie": f"better-auth.session_token={COOKIE}",
            "Referer": f"https://app.example/reset-password?token={REFERER}",
        },
    )


class TestAFailedRequestIsReportedOnce:
    def test_one_event_for_one_500(self, api, events):
        assert _fail_a_request(api).status_code == 500

        assert len(events) == 1
        assert events[0]["exception"]["values"][-1]["type"] == "DuplicateKeyError"


class TestTheReportCarriesNothingTheUserWrote:
    @pytest.mark.parametrize(
        "sentinel",
        [LOCAL, BODY, CRUMB, LOGGED, KEYED, DUPLICATE, COOKIE, QUERY, REFERER],
        ids=[
            "frame local", "request body", "info log line", "error log line", "keyed value",
            "duplicate key", "cookie", "query", "referer",
        ],  # fmt: skip
    )
    def test_it_is_absent_from_the_event_and_its_breadcrumbs(self, api, events, sentinel):
        _fail_a_request(api)

        assert events, "nothing was reported, so nothing was checked"
        assert sentinel.split()[0] not in json.dumps(events, default=str)

    @pytest.mark.parametrize("sentinel", [STORED, PROMPT], ids=["database write", "model prompt"])
    def test_nor_does_what_the_request_stored_or_sent_to_the_model(self, api, events, sentinel):
        """Real MongoDB and the real model client: both record what they did
        as breadcrumbs, and the model client reports its own failure."""
        assert api.post(PROBE + "/work").status_code == 500

        crumbs = [c.get("category") for e in events for c in e["breadcrumbs"]["values"]]
        assert "query" in crumbs, "the database commands were not recorded, so nothing was checked"
        assert sentinel.split()[0] not in json.dumps(events, default=str)

    def test_what_is_left_still_says_what_failed_and_where(self, api, events):
        _fail_a_request(api)

        failure = events[0]["exception"]["values"][-1]
        assert failure["value"].startswith("E11000 duplicate key error collection:")
        assert failure["value"].endswith("sentry_probe_users index: email_1")
        assert "_fail" in [frame["function"] for frame in failure["stacktrace"]["frames"]]
        assert events[0]["request"]["url"].endswith(PROBE)


class TestTheReleaseIsTheCommit:
    @pytest.fixture
    def commit(self, monkeypatch):
        monkeypatch.setattr(settings, "GIT_SHA", "0123abc")

    def test_the_event_names_the_commit_the_image_was_built_from(self, commit, api, events):
        _fail_a_request(api)

        assert events[0]["release"] == "0123abc"

    def test_the_image_build_passes_the_commit_in(self):
        """Read as text: the container has no git, so the build has to say."""
        dockerfile = (REPO / "backend" / "Dockerfile").read_text()
        workflow = (REPO / ".github" / "workflows" / "build-images.yml").read_text()

        assert "ARG GIT_SHA" in dockerfile and "GIT_SHA=${GIT_SHA}" in dockerfile
        assert "GIT_SHA=${{ github.sha }}" in workflow


class TestARefusedRequestIsNotAnError:
    def test_a_422_is_logged_below_error_without_the_value_and_not_reported(self, api, events, caplog):
        with caplog.at_level(logging.INFO):
            response = api.post(PROBE, json=REJECTED)

        assert response.status_code == 422
        assert [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR] == []
        assert REJECTED not in caplog.text
        assert events == []

    def test_a_model_rejected_inside_a_handler_is_the_same(self, api, events, caplog):
        with caplog.at_level(logging.INFO):
            response = api.get(PROBE + "/rejected")

        assert response.status_code == 422
        assert "words" in caplog.text, "the log still says which field"
        assert [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR] == []
        assert REJECTED not in caplog.text
        assert events == []
