from pydantic_settings import BaseSettings
from pydantic import field_validator, Field, ValidationError
from typing import List, Union
import os


class Settings(BaseSettings):
    DATABASE_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "auto_author_test"
    OPENAI_AUTOAUTHOR_API_KEY: str = "test-key"  # Default for testing

    # Better Auth Settings
    # CRITICAL: BETTER_AUTH_SECRET must be set in .env file
    # Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'
    BETTER_AUTH_SECRET: str = Field(
        ...,  # Required - no default value for security
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

    # AWS Settings (Optional - for transcription and storage)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = ""

    # Cloudinary Settings (Optional - for image storage)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

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

        # Reject known weak/test secrets
        weak_secrets = [
            "test-better-auth-secret-key",
            "secret",
            "changeme",
            "development",
            "test",
            "password",
            "123456",
        ]
        if v.lower() in weak_secrets or any(weak in v.lower() for weak in ["test", "changeme", "secret", "password"]):
            raise ValueError(
                "BETTER_AUTH_SECRET cannot be a weak/default value. "
                "This appears to be a test secret. "
                "Generate a strong secret with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # Warn if running in production without proper secret
        if os.getenv("NODE_ENV") == "production" and len(v) < 64:
            import warnings
            warnings.warn(
                "BETTER_AUTH_SECRET should be at least 64 characters in production. "
                "Current length: {len(v)}. Recommend regenerating with stronger secret."
            )

        return v

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
