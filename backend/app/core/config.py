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

    # CORS (S-9)
    # In production ALLOWED_ORIGINS must be a real domain — no localhost, no wildcard.
    # Example: ALLOWED_ORIGINS=["https://ticketsystem.example.com"]
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

    # ── Email ingestion (IMAP) ─────────────────────────────────────────────────
    # Set IMAP_ENABLED=true and fill in the remaining IMAP_* vars to have the
    # application poll an IMAP mailbox for incoming emails and convert matching
    # messages into ticket comments.
    #
    # Subject format — any of the following patterns is recognised (case-insensitive):
    #   [Ticket #123]         ← canonical reply-subject format
    #   [Ticket-123]
    #   Ticket #123 …
    #   Ticket 123: …
    #
    # Attachments (images and PDFs) are automatically saved to the ticket.
    # The comment author is resolved as follows:
    #   1. A registered, active user whose email matches the message From: address.
    #   2. If IMAP_REQUIRE_REGISTERED_SENDER=true (default): message is REJECTED.
    #   2. If IMAP_REQUIRE_REGISTERED_SENDER=false: falls back to the user
    #      configured via IMAP_SYSTEM_USER_EMAIL.  Messages with no resolvable
    #      author are always discarded regardless of this setting.
    #
    IMAP_ENABLED: bool = False
    IMAP_HOST: str = ""
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""
    IMAP_MAILBOX: str = "INBOX"
    IMAP_USE_SSL: bool = True
    # How often (in seconds) to poll for new messages.  60 s is a sensible default.
    IMAP_POLL_INTERVAL_SECONDS: int = 60
    # Maximum raw message size accepted before parsing (DoS guard).
    # Messages exceeding this limit are marked SEEN and skipped.
    IMAP_MAX_MESSAGE_SIZE_MB: int = 10
    # Security: when True (the default) only emails from registered, active user
    # accounts are accepted.  Messages from unknown senders are silently discarded.
    # Set to False only in controlled environments where you trust all senders in
    # the mailbox and want unrecognised senders attributed to IMAP_SYSTEM_USER_EMAIL.
    IMAP_REQUIRE_REGISTERED_SENDER: bool = True
    # Optional: email address of the system user to attribute ingested comments to
    # when IMAP_REQUIRE_REGISTERED_SENDER=false and the sender is not registered.
    # Has no effect (and is never used) when IMAP_REQUIRE_REGISTERED_SENDER=true.
    IMAP_SYSTEM_USER_EMAIL: str = ""

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
        # S-9: reject localhost-only or wildcard ALLOWED_ORIGINS in production
        if self.ENVIRONMENT == "production":
            _bad = {"*", "http://localhost:3000", "http://localhost:8080", "http://localhost"}
            if not self.ALLOWED_ORIGINS or all(o in _bad for o in self.ALLOWED_ORIGINS):
                raise ValueError(
                    "ALLOWED_ORIGINS must be set to real domain(s) in production. "
                    "Example: ALLOWED_ORIGINS=[\"https://ticketsystem.example.com\"]"
                )
            if self.IMAP_ENABLED and not self.IMAP_USE_SSL:
                raise ValueError(
                    "IMAP_USE_SSL must be True in production — plaintext IMAP connections "
                    "expose credentials. Set IMAP_USE_SSL=true in your environment."
                )
        return self


settings = Settings()
