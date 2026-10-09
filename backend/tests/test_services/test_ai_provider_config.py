"""Configurable AI provider and per-flow models (#917).

The wire tests run a real HTTP server speaking the OpenAI chat-completions
shape, so the SDK's actual base_url/auth/request handling is exercised.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from app.core.config import Settings, settings
from app.services.ai_errors import AIServiceError
from app.services.ai_service import AIService
from tests.test_services.openai_autospec import autospec_openai_client
from tests.test_services.test_toc_token_budget import _toc

AI_SETTINGS = (
    "AI_BASE_URL",
    "AI_API_KEY",
    "AI_MODEL_DEFAULT",
    "AI_MODEL_LONG_OUTPUT",
    "AI_MAX_OUTPUT_TOKENS_DEFAULT",
    "AI_MAX_OUTPUT_TOKENS_LONG",
)
SUMMARY = "A practical guide for first-time engineering managers. " * 5
RESPONSES = [{"question": "Who reads it?", "answer": "New managers."}]


@pytest.fixture
def unset_ai_settings(monkeypatch):
    """Every AI_* setting at its declared default, whatever the local .env says."""
    for name in AI_SETTINGS:
        monkeypatch.setattr(settings, name, Settings.model_fields[name].default)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)


@pytest.fixture
def stub():
    """A local OpenAI-compatible endpoint that records every request."""
    state = SimpleNamespace(requests=[], status=200, content=_toc(3, 2), finish_reason="stop")

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state.requests.append(
                {"path": self.path, "auth": self.headers.get("Authorization"), "body": body}
            )
            if state.status == 200:
                payload = {
                    "id": "chatcmpl-stub",
                    "object": "chat.completion",
                    "created": 1,
                    "model": body["model"],
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": state.finish_reason,
                            "message": {"role": "assistant", "content": state.content},
                        }
                    ],
                }
            else:
                payload = {"error": {"message": "add usage credits", "type": "api_error"}}
            data = json.dumps(payload).encode()
            self.send_response(state.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    state.url = f"http://127.0.0.1:{server.server_port}/v1"
    yield state
    server.shutdown()
    server.server_close()


@pytest.fixture
def stub_service(stub, unset_ai_settings, monkeypatch):
    monkeypatch.setattr(settings, "AI_BASE_URL", stub.url)
    monkeypatch.setattr(settings, "AI_API_KEY", "stub-key")
    monkeypatch.setattr(settings, "AI_MODEL_DEFAULT", "cheap-default")
    monkeypatch.setattr(settings, "AI_MODEL_LONG_OUTPUT", "cheap-long")
    return AIService()


def _sent(svc):
    kwargs = svc.client.chat.completions.create.call_args.kwargs
    return kwargs["model"], kwargs["max_tokens"]


class TestDefaultsMatchTodaysRequests:
    """With nothing configured, every flow sends exactly what it sent before #917."""

    def test_client_targets_openai(self, unset_ai_settings):
        assert str(AIService().client.base_url) == "https://api.openai.com/v1/"

    def test_ai_api_key_takes_precedence(self, unset_ai_settings, monkeypatch):
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-openai")
        assert settings.openai_api_key == "sk-openai"
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-other-provider")
        assert settings.openai_api_key == "sk-other-provider"

    @pytest.mark.asyncio
    async def test_default_flow_params(self, unset_ai_settings):
        svc = AIService()
        svc.client = autospec_openai_client(content="READINESS: Ready")
        await svc.analyze_summary_for_toc(SUMMARY)
        assert _sent(svc) == ("gpt-4", 1000)

        svc.client = autospec_openai_client(content="Enhanced text.")
        await svc.enhance_text("Some text to enhance.", "clarity")
        assert _sent(svc) == ("gpt-4", 4000)

    @pytest.mark.asyncio
    async def test_long_output_flow_params(self, unset_ai_settings):
        svc = AIService()
        svc.client = autospec_openai_client(content=_toc(3, 2))
        await svc.generate_toc_from_summary_and_responses(SUMMARY, RESPONSES)
        assert _sent(svc) == ("gpt-4o", 6000)

        svc.client = autospec_openai_client(content="Draft body.")
        result = await svc.generate_chapter_draft("Ch", "Desc", RESPONSES, target_length=5000)
        assert _sent(svc) == ("gpt-4o", 8000)
        assert result["metadata"]["model_used"] == "gpt-4o"


class TestAlternateProviderOnTheWire:
    @pytest.mark.asyncio
    async def test_stub_receives_configured_models_and_key(self, stub, stub_service):
        analysis = await stub_service.analyze_summary_for_toc(SUMMARY)
        toc = await stub_service.generate_toc_from_summary_and_responses(SUMMARY, RESPONSES)
        draft = await stub_service.generate_chapter_draft("Ch", "Desc", RESPONSES)

        assert "error" not in analysis
        assert toc["chapters_count"] == 3
        assert draft["metadata"]["model_used"] == "cheap-long"
        assert [r["body"]["model"] for r in stub.requests] == [
            "cheap-default",
            "cheap-long",
            "cheap-long",
        ]
        assert {r["path"] for r in stub.requests} == {"/v1/chat/completions"}
        assert {r["auth"] for r in stub.requests} == {"Bearer stub-key"}

    @pytest.mark.asyncio
    async def test_output_budgets_cap_each_class(self, stub, stub_service, monkeypatch):
        monkeypatch.setattr(settings, "AI_MAX_OUTPUT_TOKENS_DEFAULT", 500)
        monkeypatch.setattr(settings, "AI_MAX_OUTPUT_TOKENS_LONG", 4096)
        svc = AIService()

        await svc.analyze_summary_for_toc(SUMMARY)
        await svc.generate_toc_from_summary_and_responses(SUMMARY, RESPONSES)

        assert [r["body"]["max_tokens"] for r in stub.requests] == [500, 4096]

    @pytest.mark.asyncio
    async def test_payment_required_maps_to_provider_quota(self, stub, stub_service):
        stub.status = 402  # Ollama cloud, OpenRouter: out of credit

        with pytest.raises(AIServiceError) as exc:
            await stub_service.generate_toc_from_summary_and_responses(SUMMARY, RESPONSES)

        assert exc.value.error_code == "AI_PROVIDER_QUOTA_EXHAUSTED"
        assert exc.value.retryable is False
        assert len(stub.requests) == 1

    @pytest.mark.asyncio
    async def test_truncation_detected_on_alternate_provider(self, stub, stub_service):
        stub.finish_reason = "length"

        with pytest.raises(AIServiceError) as exc:
            await stub_service.generate_toc_from_summary_and_responses(SUMMARY, RESPONSES)

        assert exc.value.error_code == "AI_RESPONSE_TRUNCATED"
