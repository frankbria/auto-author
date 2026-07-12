"""Autospec'd OpenAI client mocks (issue #202).

``create_autospec(OpenAI, instance=True)`` cannot be used directly: the real
client reaches ``chat.completions`` through ``cached_property`` descriptors,
which autospec can't traverse (accessing ``.chat.completions`` raises
``AttributeError``). Instead we autospec the real *bound*
``chat.completions.create`` method, which enforces the real SDK signature on
every call — an unknown or missing kwarg raises ``TypeError`` instead of
sailing through a bare ``Mock``.
"""
from types import SimpleNamespace
from unittest.mock import create_autospec

from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice


def make_chat_completion(
    content: str = "stub response",
    finish_reason: str = "stop",
    model: str = "gpt-4",
) -> ChatCompletion:
    """A real typed ChatCompletion so response parsing exercises the true SDK shape."""
    return ChatCompletion(
        id="chatcmpl-test",
        object="chat.completion",
        created=1,
        model=model,
        choices=[
            Choice(
                index=0,
                finish_reason=finish_reason,
                message=ChatCompletionMessage(role="assistant", content=content),
            )
        ],
    )


def autospec_openai_client(
    content: str = "stub response", finish_reason: str = "stop"
) -> SimpleNamespace:
    """Mock OpenAI client whose ``chat.completions.create`` validates kwargs
    against the real openai SDK signature.

    Constructing a real ``OpenAI`` client is offline (no network at init); it
    exists only to obtain the bound method whose signature we spec against.
    """
    real_create = OpenAI(api_key="autospec-test-key").chat.completions.create
    mock_create = create_autospec(
        real_create,
        return_value=make_chat_completion(content=content, finish_reason=finish_reason),
    )
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=mock_create))
    )
