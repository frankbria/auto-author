"""The settings object does not print its secrets (#930).

A pydantic model's repr prints every field. A test that read a setting before
it existed failed with the developer's AWS keys, OpenAI key and signing secret
in the pytest output, because the failure rendered ``settings``. A log line or
an f-string that names ``settings`` does the same.
"""

import re

import pytest

from app.core.config import Settings

# A setting whose name ends in, or contains as a whole word, one of these holds
# a credential, an address that can carry one, or somebody's email address.
SECRET_NAME = re.compile(r"(^|_)(KEY|SECRET|PASSWORD|DSN|TOKEN|URI|URL|EMAILS?)(_|$)")
SECRETS = [name for name in Settings.model_fields if SECRET_NAME.search(name)]


def _sentinel(name: str) -> str:
    return f"SENTINEL-for-{name}-padded-to-pass-the-length-rule"


@pytest.fixture
def configured() -> Settings:
    """Settings with a recognisable value in every secret field, read from no file."""
    return Settings(_env_file=None, ENVIRONMENT="test", **{name: _sentinel(name) for name in SECRETS})


class TestSecretsAreNotPrinted:
    def test_the_sweep_finds_the_secrets_it_is_meant_to(self):
        assert set(SECRETS) >= {
            "MONGODB_URI", "DATABASE_URL", "OPENAI_API_KEY", "OPENAI_AUTOAUTHOR_API_KEY",
            "AI_API_KEY", "BETTER_AUTH_SECRET", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
            "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET", "STRIPE_WEBHOOK_SECRET",
            "STRIPE_SECRET_KEY", "SENTRY_DSN", "E2E_EXEMPT_EMAILS",
        }  # fmt: skip
        assert "AI_MAX_OUTPUT_TOKENS_DEFAULT" not in SECRETS, "a token budget is not a token"

    @pytest.mark.parametrize("name", SECRETS)
    def test_a_new_secret_cannot_be_added_without_hiding_it(self, name):
        assert Settings.model_fields[name].repr is False, (
            f"{name} looks like a credential by its name: declare it with Field(..., repr=False)"
        )

    @pytest.mark.parametrize("render", [repr, str], ids=["repr", "str"])
    def test_no_secret_is_in_what_the_settings_print(self, configured, render):
        printed = render(configured)

        assert [name for name in SECRETS if getattr(configured, name) != _sentinel(name)] == []
        assert [name for name in SECRETS if _sentinel(name) in printed] == []

    def test_reading_a_setting_that_does_not_exist_prints_none_either(self, configured):
        with pytest.raises(AttributeError) as failure:
            configured.NOT_A_SETTING_YET

        assert "SENTINEL" not in str(failure.value)

    def test_what_is_not_a_secret_is_still_printed(self, configured):
        printed = repr(configured)

        assert "ENVIRONMENT='test'" in printed
        assert "API_V1_PREFIX=" in printed
        assert "BILLING_ENABLED=True" in printed
