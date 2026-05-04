from apscheduler.triggers.cron import CronTrigger
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


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
    poolside_api_key: str = Field(
        default="",
        description="Poolside API key for AI-powered checks (free inference)",
    )
    poolside_api_url: str = Field(
        default="https://inference.poolside.ai/v1",
        description="Poolside inference endpoint",
    )
    poolside_model: str = Field(
        default="poolside/laguna-xs.2",
        description="Poolside model name for analysis checks",
    )

    # Assistant configuration
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant vector store URL",
    )
    assistant_model: str = Field(
        default="poolside/m.1",
        description="LLM model for assistant chat (poolside/m.1 is free)",
    )
    assistant_max_history: int = Field(
        default=10,
        description="Maximum conversation history messages to include in context",
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

    # Email configuration
    email_provider: str = Field(default="smtp", description='Email provider: "sendgrid" or "smtp"')
    sendgrid_api_key: str = Field(default="", description="SendGrid API key for email sending")
    smtp_host: str = Field(default="", description="SMTP server hostname")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    email_from: str = Field(default="noreply@hackthevalley.io", description="Default sender email address")

    model_config = {"env_prefix": "HACKVERIFY_", "env_file": ".env"}


settings = Settings()

# Email settings for backward compatibility with task spec
EMAIL_PROVIDER = settings.email_provider
SENDGRID_API_KEY = settings.sendgrid_api_key
SMTP_HOST = settings.smtp_host
SMTP_PORT = settings.smtp_port
SMTP_USER = settings.smtp_user
SMTP_PASSWORD = settings.smtp_password
EMAIL_FROM = settings.email_from
