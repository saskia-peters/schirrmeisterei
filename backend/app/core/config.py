from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "TicketSystem"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # Security
    SECRET_KEY: str = "change-me-in-production-use-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://ticketsystem:ticketsystem@localhost:5432/ticketsystem"

    # Database connection pool
    # Current defaults are sized for ≤30 concurrent users (single replica).
    # See SCALING.md for recommended values at each growth tier.
    DB_POOL_SIZE: int = 5           # raise to 20 at ~100 users (single replica)
    DB_MAX_OVERFLOW: int = 10       # max extra connections beyond pool_size
    DB_POOL_RECYCLE: int = 1800     # seconds — recycle idle connections to avoid stale sockets
    DB_POOL_PRE_PING: bool = True   # validate connection before use; negligible overhead

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # File uploads
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # Rate limiting (S-5)
    # Default: in-memory per-process. Set RATE_LIMIT_STORAGE_URI=redis://redis:6379/1
    # at Tier-3 scale (100+ users / multi-replica) for shared counters. See SCALING.md § 3.2.
    RATE_LIMIT_STORAGE_URI: str = "memory://"

    # Refresh-token cookie (S-7)
    # Set to True in production (HTTPS). Browsers will NOT send Secure cookies over HTTP,
    # so this MUST remain False during local development (Vite proxy / HTTP).
    COOKIE_SECURE: bool = False

    # 2FA
    TOTP_ISSUER: str = "TicketSystem"

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        """Ensure SECRET_KEY has been changed from the default in non-development environments."""
        _default = "change-me-in-production-use-long-random-string"
        if self.SECRET_KEY == _default and self.ENVIRONMENT != "development":
            raise ValueError(
                "SECRET_KEY must be changed from the default value "
                "in non-development environments"
            )
        if self.ENVIRONMENT == "production" and not self.COOKIE_SECURE:
            raise ValueError(
                "COOKIE_SECURE must be True in production (refresh token cookie "
                "requires HTTPS). Set COOKIE_SECURE=true in your environment."
            )
        return self


settings = Settings()
