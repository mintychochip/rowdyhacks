from apscheduler.triggers.cron import CronTrigger
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/hackverify",
        description="PostgreSQL connection string (asyncpg driver)",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL (optional, for caching)",
    )
    secret_key: str = Field(
        default="change-me-to-a-secret-key-at-least-32-chars",
        description="JWT signing key (min 32 chars)",
    )
    # OAuth provider credentials (all free)
    google_client_id: str = Field(default="", description="Google OAuth client ID")
    google_client_secret: str = Field(default="", description="Google OAuth client secret")
    github_client_id: str = Field(default="", description="GitHub OAuth client ID")
    github_client_secret: str = Field(default="", description="GitHub OAuth client secret")
    discord_client_id: str = Field(default="", description="Discord OAuth client ID")
    discord_client_secret: str = Field(default="", description="Discord OAuth client secret")

    github_token: str = Field(
        default="",
        description="GitHub personal access token (optional, increases API rate limit)",
    )

    discord_bot_token: str = Field(default="", description="Discord bot token for application management")
    base_url: str = Field(default="http://localhost:8000", description="Public base URL for QR code links")
    frontend_url: str = Field(default="http://localhost:8000", description="Frontend origin for OAuth redirects")

    crawler_schedule: str = Field(
        default="0 3 * * 0",  # Sunday 3 AM UTC
        description="Cron expression for the weekly crawl (APScheduler format)",
    )
    crawler_refresh_window_days: int = Field(
        default=30,
        gt=0,
        description="Days after hackathon end to keep refreshing for late submissions",
    )

    # Monitoring & Observability
    sentry_dsn: str = Field(
        default="",
        description="Sentry DSN for error tracking",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    json_logs: bool = Field(
        default=False,
        description="Enable JSON structured logging (for production)",
    )

    @field_validator("secret_key")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("secret_key must be at least 32 characters")
        return v

    @field_validator("crawler_schedule")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        try:
            CronTrigger.from_crontab(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid cron expression: {e}") from e
        return v

    model_config = {"env_prefix": "HACKVERIFY_", "env_file": ".env"}


settings = Settings()
