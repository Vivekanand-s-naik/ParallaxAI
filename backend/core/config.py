"""
Centralized environment configuration for ParallaxAI.
Loads configuration from environment variables and .env file with validation.
"""

from functools import lru_cache
from typing import List, Union
import json
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    APP_NAME: str = "ParallaxAI — AI Governance Command Center"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # PostgreSQL
    POSTGRES_USER: str = "parallaxai"
    POSTGRES_PASSWORD: str = "parallaxai_dev_pass"
    POSTGRES_DB: str = "parallaxai_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433

    DATABASE_URL: str = (
        "postgresql+asyncpg://parallaxai:parallaxai_dev_pass@localhost:5433/parallaxai_db"
    )
    DATABASE_URL_SYNC: str = (
        "postgresql+psycopg://parallaxai:parallaxai_dev_pass@localhost:5433/parallaxai_db"
    )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT & Session
    JWT_SECRET_KEY: str = "parallaxai-dev-jwt-secret-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SESSION_SECRET: str = "parallaxai-default-secret-change-in-production"

    # CORS & Cookies
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ]
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5
    RATE_LIMIT_REGISTER_PER_HOUR: int = 3
    RATE_LIMIT_PASSWORD_RESET_PER_HOUR: int = 3
    RATE_LIMIT_API_PER_MINUTE: int = 100
    RATE_LIMIT_AI_PER_MINUTE: int = 10
    RATE_LIMIT_UPLOAD_PER_HOUR: int = 10

    # Google OAuth 2.0 / OIDC
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # AI Provider API Keys (optional)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("["):
                return json.loads(v_str)
            return [i.strip() for i in v_str.split(",") if i.strip()]
        return v

    @property
    def is_google_oauth_configured(self) -> bool:
        return bool(
            self.GOOGLE_CLIENT_ID.strip()
            and self.GOOGLE_CLIENT_SECRET.strip()
            and self.GOOGLE_REDIRECT_URI.strip()
        )

    @property
    def google_oauth_enabled(self) -> bool:
        return self.is_google_oauth_configured

    @property
    def email_provider_configured(self) -> bool:
        return False

    @property
    def ENVIRONMENT(self) -> str:
        return self.APP_ENV

    @property
    def DEFAULT_REGISTRATION_ROLE(self) -> str:
        return "VIEWER"

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def REFRESH_TOKEN_EXPIRE_DAYS(self) -> int:
        return self.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    @property
    def RATE_LIMIT_GENERAL_PER_MINUTE(self) -> int:
        return self.RATE_LIMIT_API_PER_MINUTE


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

