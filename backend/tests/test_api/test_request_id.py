"""One id names a request everywhere it leaves a trace (#810).

The middleware minted an id, put it on successful responses and in two of its
own log lines, and nothing else used it. A 500 carried no id, and no CORS
headers either, so a page on the frontend's origin could not read a 500 at
all. Structured errors carried a second, unrelated random id. So the
"Reference ID" a user could quote matched nothing on the server.
"""

import logging
import uuid

import pytest
import sentry_sdk
from fastapi.testclient import TestClient

from app import main
from app.core.config import settings
from app.main import app
from app.utils.error_handlers import generate_request_id, handle_book_not_found

PROBE = "/__request_id_probe"
ORIGIN = {"Origin": settings.BACKEND_CORS_ORIGINS[0]}

log = logging.getLogger("app.probe")


async def _ok():
    log.warning("working on it")
    return {"id_seen_inside": generate_request_id()}


async def _not_found():
    raise handle_book_not_found("507f1f77bcf86cd799439011")


async def _fail():
    log.warning("about to fail")
    raise RuntimeError("unexpected")


@pytest.fixture
def api():
    app.add_api_route(PROBE, _ok, methods=["GET"])
    app.add_api_route(PROBE + "/missing", _not_found, methods=["GET"])
    app.add_api_route(PROBE + "/fail", _fail, methods=["GET"])
    yield TestClient(app, raise_server_exceptions=False)
    del app.router.routes[-3:]


def _is_an_id(value) -> bool:
    return isinstance(value, str) and str(uuid.UUID(value)) == value


class TestEveryResponseNamesItsRequest:
    def test_a_success_carries_the_id_in_a_header(self, api):
        response = api.get(PROBE)

        assert _is_an_id(response.headers["x-request-id"])

    def test_two_requests_get_two_ids(self, api):
        assert api.get(PROBE).headers["x-request-id"] != api.get(PROBE).headers["x-request-id"]

    def test_a_500_carries_it_in_the_header_and_the_body(self, api):
        response = api.get(PROBE + "/fail")

        assert response.status_code == 500
        assert _is_an_id(response.headers["x-request-id"])
        assert response.json() == {
            "detail": "An unexpected error occurred",
            "request_id": response.headers["x-request-id"],
        }

    def test_a_structured_error_carries_the_same_id_not_one_of_its_own(self, api):
        response = api.get(PROBE + "/missing")

        assert response.status_code == 404
        assert response.headers["x-request-id"] in response.text

    def test_code_inside_the_request_can_ask_for_it(self, api):
        response = api.get(PROBE)

        assert response.json() == {"id_seen_inside": response.headers["x-request-id"]}

    def test_outside_a_request_there_is_still_an_id_to_give(self):
        assert generate_request_id().startswith("req_")


class TestAPageOnTheFrontendsOriginCanReadIt:
    @pytest.mark.parametrize("path", [PROBE, PROBE + "/missing", PROBE + "/fail"], ids=["200", "404", "500"])
    def test_the_response_is_readable_and_the_header_is_exposed(self, api, path):
        response = api.get(path, headers=ORIGIN)

        assert response.headers.get("access-control-allow-origin") == ORIGIN["Origin"]
        assert "X-Request-ID" in response.headers.get("access-control-expose-headers", "")

    def test_a_500_keeps_the_security_headers_every_other_response_has(self, api):
        response = api.get(PROBE + "/fail")

        assert response.headers["x-content-type-options"] == "nosniff"
        assert "default-src 'self'" in response.headers["content-security-policy"]


class TestLogLinesCarryIt:
    def test_a_line_written_while_handling_a_request_names_the_request(self, api, caplog):
        with caplog.at_level(logging.INFO):
            response = api.get(PROBE)

        line = next(r for r in caplog.records if r.getMessage() == "working on it")
        assert line.request_id == response.headers["x-request-id"]

    def test_so_do_the_lines_of_a_request_that_fails(self, api, caplog):
        with caplog.at_level(logging.INFO):
            response = api.get(PROBE + "/fail")

        mine = [r for r in caplog.records if r.name.startswith("app.")]
        assert {r.request_id for r in mine} == {response.headers["x-request-id"]}
        assert any(r.levelno == logging.ERROR for r in mine)

    def test_a_request_that_failed_is_not_also_logged_as_completed(self, api, caplog):
        with caplog.at_level(logging.INFO):
            api.get(PROBE + "/fail")
            api.get(PROBE)

        said = [r.getMessage().split(":")[0] for r in caplog.records if r.name == "app.api.request_validation"]
        assert said == ["Request started", "Request failed", "Request started", "Request completed"]

    def test_a_line_written_outside_any_request_says_so(self, api, caplog):
        api.get(PROBE)
        with caplog.at_level(logging.INFO):
            log.info("at startup")

        assert caplog.records[-1].request_id == "-"

    def test_the_format_prints_it(self):
        formats = [h.formatter._fmt for h in logging.getLogger().handlers if h.formatter]

        assert any("%(request_id)s" in f for f in formats)


class TestTheErrorReportCarriesIt:
    @pytest.fixture
    def events(self, monkeypatch):
        """The SDK as the app starts it, sending to a list. Inert again afterwards."""
        sent: list = []
        real_init = sentry_sdk.init
        monkeypatch.setattr(settings, "SENTRY_DSN", "https://key@sentry.invalid/1")
        monkeypatch.setattr(sentry_sdk, "init", lambda **options: real_init(**options, transport=sent.append))
        main._init_sentry()
        yield sent
        real_init()

    def test_the_report_of_a_500_is_tagged_with_the_id_the_user_was_given(self, api, events):
        response = api.get(PROBE + "/fail")

        assert len(events) == 1
        assert events[0]["tags"]["request_id"] == response.json()["request_id"]

    def test_the_next_request_does_not_inherit_the_tag(self, api, events):
        first = api.get(PROBE + "/fail").json()["request_id"]
        second = api.get(PROBE + "/fail").json()["request_id"]

        assert [e["tags"]["request_id"] for e in events] == [first, second]
