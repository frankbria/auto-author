from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from typing import List, Union
import os


def is_production_env() -> bool:
    """True when the deployment marker says production.

    PM2 sets ENVIRONMENT (not NODE_ENV) on the backend process, while the
    frontend/legacy path sets NODE_ENV — check both so the production
    fail-safes fire on the real deployment (issue #176). Staging
    (ENVIRONMENT=staging) intentionally does not match.
    """
    return "production" in (os.getenv("ENVIRONMENT"), os.getenv("NODE_ENV"))


class Settings(BaseSettings):
    # MongoDB connection - MONGODB_URI takes precedence over DATABASE_URL
    MONGODB_URI: str = ""  # Standard env var name (e.g., for Atlas)
    DATABASE_URL: str = "mongodb://localhost:27017"  # Fallback/legacy
    DATABASE_NAME: str = "auto_author_test"

    @property
    def mongo_connection_string(self) -> str:
        """Get MongoDB connection string, preferring MONGODB_URI over DATABASE_URL."""
        return self.MONGODB_URI if self.MONGODB_URI else self.DATABASE_URL
    # OpenAI key. OPENAI_API_KEY is the canonical/standard name (matches the
    # GitHub env secret); OPENAI_AUTOAUTHOR_API_KEY is the legacy app-specific
    # name kept for backward compatibility. Use `settings.openai_api_key`.
    OPENAI_API_KEY: str = ""
    OPENAI_AUTOAUTHOR_API_KEY: str = "test-key"  # Default for testing

    @property
    def openai_api_key(self) -> str:
        """Resolve the OpenAI key, preferring the standard OPENAI_API_KEY."""
        return self.OPENAI_API_KEY or self.OPENAI_AUTOAUTHOR_API_KEY

    # Better Auth Settings
    # CRITICAL: BETTER_AUTH_SECRET must be set in .env file
    # Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'
    # For CI/testing: use "test-secret-for-ci-minimum-32-characters-long-safe-for-testing"
    BETTER_AUTH_SECRET: str = Field(
        default="test-secret-for-ci-minimum-32-characters-long-safe-for-testing",
        min_length=32,
        description="JWT signing secret - MUST be strong random value, minimum 32 characters"
    )
    BETTER_AUTH_URL: str = "http://localhost:3000"  # Base URL of the application
    BETTER_AUTH_ISSUER: str = "better-auth"  # Issuer identifier for JWT tokens
    JWT_ALGORITHM: str = "HS256"  # Changed from RS256 (Clerk) to HS256 (better-auth)

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        json_schema_extra={"env_parse_none_str": "null"}
    )

    # E2E Testing Settings
    BYPASS_AUTH: bool = False  # Set to True for E2E tests to bypass authentication

    # Redis Cache Settings
    REDIS_URL: str = "redis://localhost:6379/0"
    AI_CACHE_TTL: int = 86400  # 24 hours in seconds
    AI_CACHE_ENABLED: bool = True
    AI_MAX_RETRIES: int = 3

    # Max times a single question may be regenerated (per-question abuse cap,
    # complementing the endpoint rate limit)
    MAX_QUESTION_REGENERATION_COUNT: int = 5

    # Per-user AI generation quota (cost control). Every AI generation endpoint
    # increments a per-user counter; at the cap the endpoint returns 429. Limits
    # are configurable per environment; a limit <= 0 disables that window.
    # Keys off the user's auth_id today; swap to plan/entitlement when P0.2 lands.
    AI_QUOTA_ENABLED: bool = True
    AI_QUOTA_DAILY_LIMIT: int = 50
    AI_QUOTA_MONTHLY_LIMIT: int = 500

    # Plan/entitlement enforcement (issue #174, P0.2). When True, AI endpoints
    # check the caller's plan against app.core.entitlements before running. Free
    # beta users are entitled to everything, so this is safe to leave on; it is
    # bypassed alongside BYPASS_AUTH in tests/E2E. Set False to disable the gate.
    PLAN_ENFORCEMENT_ENABLED: bool = True

    # Export Settings
    EXPORT_TIMEOUT_SECONDS: int = 120  # Hard cap on a single export's generation

    # AWS Settings (Optional - for transcription and storage)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = ""

    # Cloudinary Settings (Optional - for image storage)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Stripe billing (issue #220). STRIPE_WEBHOOK_SECRET verifies webhook
    # payloads (raw-body HMAC); unset => POST /webhooks/stripe fails closed
    # with 503. STRIPE_PRICE_ID_PRO maps that Stripe price to the "pro" plan
    # (app.core.entitlements.resolve_plan_for_price). The Stripe API key is
    # deliberately NOT added until checkout (#221) consumes it.
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_PRO: str = ""

    @field_validator("STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_ID_PRO", mode="before")
    @classmethod
    def strip_stripe_values(cls, v):
        # A trailing newline from `.env`/`$(cat secret)` would make every
        # webhook fail signature verification with no obvious cause.
        return v.strip() if isinstance(v, str) else v

    @field_validator('BACKEND_CORS_ORIGINS', mode='before')
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith('['):
            return [i.strip() for i in v.split(',')]
        elif isinstance(v, str):
            import json
            return json.loads(v)
        elif isinstance(v, list):
            return v
        raise ValueError(v)

    @field_validator('BETTER_AUTH_SECRET')
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret strength and reject weak/default values."""
        # Check minimum length (already enforced by Field, but double-check)
        if len(v) < 32:
            raise ValueError(
                "BETTER_AUTH_SECRET must be at least 32 characters. "
                "Generate a strong secret with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # Allow specific test secret for CI/testing environments
        ci_test_secret = "test-secret-for-ci-minimum-32-characters-long-safe-for-testing"
        if v == ci_test_secret:
            # Only allow in test/CI environments, not production
            if is_production_env():
                raise ValueError(
                    "FATAL: Cannot use test secret in production environment. "
                    "Generate a strong secret with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            return v  # Allow in test/CI

        # Reject known weak/test secrets (except our specific CI secret)
        weak_secrets = [
            "test-better-auth-secret-key",
            "secret",
            "changeme",
            "development",
            "password",
            "123456",
        ]
        # More permissive check - only reject if it's exactly a weak secret or very short "test"
        if v.lower() in weak_secrets or v.lower() == "test":
            raise ValueError(
                "BETTER_AUTH_SECRET cannot be a weak/default value. "
                "Generate a strong secret with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # Warn if running in production without proper secret
        if is_production_env() and len(v) < 64:
            import warnings
            warnings.warn(
                f"BETTER_AUTH_SECRET should be at least 64 characters in production. "
                f"Current length: {len(v)}. Recommend regenerating with stronger secret."
            )

        return v

    @field_validator('BYPASS_AUTH')
    @classmethod
    def validate_bypass_auth(cls, v: bool) -> bool:
        """Validate BYPASS_AUTH is not enabled in production environment.

        BYPASS_AUTH allows skipping authentication for E2E testing but must
        NEVER be enabled in production as it would expose all user data.
        """
        if v is True and is_production_env():
            raise ValueError(
                "FATAL SECURITY ERROR: BYPASS_AUTH cannot be enabled in production environment. "
                "This would allow unauthorized access to all user data and features. "
                "Remove BYPASS_AUTH=true from your production configuration."
            )
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
