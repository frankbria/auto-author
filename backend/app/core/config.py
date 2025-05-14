from pydantic import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URI: str
    DATABASE_NAME: str
    OPENAI_API_KEY: str

    # Clerk Authentication Settings
    CLERK_API_KEY: str
    CLERK_JWT_PUBLIC_KEY: str
    CLERK_FRONTEND_API: str
    CLERK_JWT_ALGORITHM: str = "RS256"
    CLERK_WEBHOOK_SECRET: str = ""  # Secret for validating webhooks

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
