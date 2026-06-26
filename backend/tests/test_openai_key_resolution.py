"""The OpenAI key resolves preferring the canonical OPENAI_API_KEY, falling back
to the legacy app-specific OPENAI_AUTOAUTHOR_API_KEY (see config.openai_api_key).

This is the fix for staging using a stale/invalid key: the deploy provides the
valid key as OPENAI_API_KEY, and the service now reads it natively.
"""

from app.core.config import Settings


def test_prefers_standard_openai_api_key():
    s = Settings(OPENAI_API_KEY="sk-standard", OPENAI_AUTOAUTHOR_API_KEY="sk-legacy")
    assert s.openai_api_key == "sk-standard"


def test_falls_back_to_legacy_when_standard_unset():
    s = Settings(OPENAI_API_KEY="", OPENAI_AUTOAUTHOR_API_KEY="sk-legacy")
    assert s.openai_api_key == "sk-legacy"
