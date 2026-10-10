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


def test_ai_api_key_takes_precedence():
    s = Settings(AI_BASE_URL="", AI_API_KEY="sk-other", OPENAI_API_KEY="sk-standard")
    assert s.openai_api_key == "sk-other"


def test_openai_key_never_goes_to_another_endpoint():
    """#917: AI_BASE_URL without AI_API_KEY must not fall back to the OpenAI key."""
    s = Settings(AI_BASE_URL="https://other.example/v1", AI_API_KEY="", OPENAI_API_KEY="sk-standard")
    assert s.openai_api_key == ""
