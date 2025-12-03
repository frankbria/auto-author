from pydantic_settings import BaseSettings
from pydantic import field_validator, Field
from typing import List, Union


class Settings(BaseSettings):
    DATABASE_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "auto_author_test"
    OPENAI_AUTOAUTHOR_API_KEY: str = "test-key"  # Default for testing

    # Clerk Authentication Settings
    CLERK_API_KEY: str = "test-clerk-api-key"
    CLERK_PUBLISHABLE_KEY: str = "pk_test_test"
    CLERK_JWT_PUBLIC_KEY: str | None = None  # Optional: Will fetch from JWKS if not provided
    CLERK_FRONTEND_API: str = "clerk.test.api"
    CLERK_BACKEND_API: str = "clerk.test.backend"
    CLERK_JWT_ALGORITHM: str = "RS256"
    CLERK_SECRET_KEY: str = ""  # Secret key for Clerk
    CLERK_WEBHOOK_SECRET: str = ""  # Secret for validating webhooks

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: Union[List[str], str] = Field(
        default=[
            # Development origins
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:3002",
            "http://localhost:3003",
            # Staging origins
            "https://dev.autoauthor.app",
            "https://api.dev.autoauthor.app",
            # Production origins
            "https://autoauthor.app",
            "https://api.autoauthor.app",
        ],
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

    @property
    def clerk_jwt_public_key_pem(self):
        if self.CLERK_JWT_PUBLIC_KEY:
            return self.CLERK_JWT_PUBLIC_KEY.replace("\\n", "\n")
        return None
    
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

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
