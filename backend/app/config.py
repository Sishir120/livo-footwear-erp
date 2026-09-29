import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "LIVO GROUP OF INDUSTRIES Footwear ERP"
    VERSION: str = "1.0.0"
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

