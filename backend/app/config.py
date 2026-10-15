import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "LIVO GROUP OF INDUSTRIES Footwear ERP"
    VERSION: str = "1.0.0"
    BUILD_COMMIT: str = (
        os.getenv("BUILD_COMMIT")
        or os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("GIT_COMMIT")
        or "dev"
    )[:8]
    API_V1_STR: str = "/api/v1"

    # Security — SECRET_KEY MUST be provided via environment variable.
    # No fallback: a missing key causes an explicit startup crash rather than
    # silently running on an insecure committed default (RULES.md §4).
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day session

    # Cookie security — defaults True (production-safe).
    # Set LIVO_DEV_MODE=true in local .env to allow non-HTTPS dev sessions only.
    LIVO_DEV_MODE: bool = os.getenv("LIVO_DEV_MODE", "false").lower() == "true"

    @property
    def COOKIE_SECURE(self) -> bool:
        """True in production (HTTPS required); False only in explicit dev mode."""
        return not self.LIVO_DEV_MODE

    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax")

    # CORS - configurable via comma-separated string or list from env
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Environment mode (development, staging, production)
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT in ("production", "prod")

    # Explicit opt-in for demo user seeding (strictly disabled by default, strictly forbidden in production)
    ENABLE_DEMO_SEEDING: bool = os.getenv("ENABLE_DEMO_SEEDING", "false").lower() == "true"

    # Database auto-migration on application startup (defaults True, can be disabled for release-phase migrations)
    AUTO_MIGRATE: bool = os.getenv("AUTO_MIGRATE", "true").lower() == "true"

    # Trusted reverse proxy IPs / CIDRs for secure client IP extraction (X-Forwarded-For traversal)
    TRUSTED_PROXIES: Union[List[str], str] = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1")

    @field_validator("TRUSTED_PROXIES", mode="before")
    @classmethod
    def assemble_trusted_proxies(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["127.0.0.1", "::1"]

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./livo_dev.db"
    )

    # Storage (Backblaze B2 / R2 S3-compatible)
    STORAGE_ENDPOINT_URL: str = os.getenv("STORAGE_ENDPOINT_URL", "")
    STORAGE_ACCESS_KEY: str = os.getenv("STORAGE_ACCESS_KEY", "")
    STORAGE_SECRET_KEY: str = os.getenv("STORAGE_SECRET_KEY", "")
    STORAGE_BUCKET_NAME: str = os.getenv("STORAGE_BUCKET_NAME", "livo-erp-storage")

    model_config = {
        "env_file": [".env", "backend/.env", "../backend/.env"],
        "extra": "allow"
    }

settings = Settings()

# Fail fast on missing SECRET_KEY — do not start with an empty signing key.
# A startup crash here is the correct behavior; a running app on "" is not.
if not settings.SECRET_KEY:
    raise ValueError(
        "SECRET_KEY environment variable is not set. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\" "
        "and set it in your .env file or deployment environment. "
        "The app will not start without it (RULES.md §4)."
    )

