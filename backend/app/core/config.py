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
    DATABASE_URL: str = "sqlite+aiosqlite:///./ticketsystem.db"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # File uploads
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # 2FA
    TOTP_ISSUER: str = "TicketSystem"

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        _default = "change-me-in-production-use-long-random-string"
        if self.SECRET_KEY == _default and self.ENVIRONMENT != "development":
            raise ValueError(
                "SECRET_KEY must be changed from the default value "
                "in non-development environments"
            )
        return self


settings = Settings()
