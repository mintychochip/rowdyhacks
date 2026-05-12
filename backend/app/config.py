"""Application settings loaded from environment variables.

Centralizes all runtime configuration for the hackathon platform,
including database, cache, OAuth, LLM, email, S3, and branding.
Values are read from the environment with the ``HACKVERIFY_`` prefix
and validated on import.
"""

from apscheduler.triggers.cron import CronTrigger
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    Groups settings by concern (database, OAuth, LLM, storage, email,
    branding) and validates critical values such as the JWT secret
    key length and the crawler cron expression on instantiation.
    """

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
    admin_email: str = Field(default="", description="First-run admin email (bootstrap)")
    admin_password: str = Field(default="", description="First-run admin password (bootstrap)")
    # Clerk (deprecated — kept for backward compatibility with existing routes/tests)
    clerk_secret_key: str = Field(default="", description="Clerk secret key (legacy, no longer required)")
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
        description="Poolside API key for AI-powered checks (free inference). Falls back to llm_api_key if not set.",
    )
    llm_api_key: str = Field(
        default="",
        description="Generic LLM API key (Anthropic/Poolside). Used as fallback for poolside_api_key if not set.",
    )
    llm_base_url: str = Field(
        default="",
        description="Generic LLM API base URL (OpenAI-compatible). Falls back to poolside_api_url if not set.",
    )
    llm_model: str = Field(
        default="",
        description="Generic LLM model name. Falls back to assistant_model if not set.",
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
        default="poolside/laguna-xs.2",
        description="LLM model for assistant chat (deprecated, use assistant_models)",
    )
    assistant_fast_model: str = Field(
        default="poolside/laguna-xs.2",
        description="Fast/cheap model for quick responses",
    )
    assistant_thinking_model: str = Field(
        default="poolside/laguna-m.1",
        description="Thinking model for complex reasoning",
    )
    assistant_max_history: int = Field(
        default=10,
        description="Maximum conversation history messages to include in context",
    )

    discord_bot_token: str = Field(default="", description="Discord bot token for application management")
    base_url: str = Field(default="http://localhost:8000", description="Public base URL for QR code links")
    frontend_url: str = Field(default="http://localhost:8000", description="Frontend origin for OAuth redirects")

    # S3/MinIO Blob Storage
    s3_endpoint: str = Field(default="", description="S3-compatible endpoint URL (e.g., http://minio:9000)")
    s3_access_key: str = Field(default="", description="S3 access key / MinIO root user")
    s3_secret_key: str = Field(default="", description="S3 secret key / MinIO root password")
    s3_bucket: str = Field(default="hackverify-files", description="Default S3 bucket for file storage")
    s3_region: str = Field(default="us-east-1", description="S3 region (for AWS S3 compatibility)")
    s3_use_ssl: bool = Field(default=False, description="Use SSL/TLS for S3 connections")
    s3_public_url: str = Field(
        default="", description="Public base URL for serving uploaded files (falls back to s3_endpoint)"
    )

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
        """Ensure the secret_key setting meets the minimum length requirement.

        Behavior:
        1. Measure the length of the provided string.
        2. If shorter than 32 characters, raise a ValueError.
        3. Otherwise, return the value unchanged.

        Raises: ValueError if the secret_key is fewer than 32 characters.
        Side Effects: None (read-only validation).
        Dependencies: pydantic.field_validator.
        Consumers: Pydantic Settings instantiation on app startup.
        """
        if len(v) < 32:
            raise ValueError("secret_key must be at least 32 characters")
        return v

    @field_validator("crawler_schedule")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Ensure the crawler_schedule setting is a valid APScheduler cron expression.

        Behavior:
        1. Attempt to parse the string with CronTrigger.from_crontab().
        2. If parsing raises ValueError or TypeError, wrap it in a descriptive ValueError and re-raise.
        3. Otherwise, return the expression unchanged.

        Raises: ValueError if the cron expression is invalid or unparseable.
        Side Effects: None (read-only validation).
        Dependencies: apscheduler.triggers.cron.CronTrigger.
        Consumers: Pydantic Settings instantiation on app startup.
        """
        try:
            CronTrigger.from_crontab(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid cron expression: {e}") from e
        return v

    # Branding configuration (self-hosted hackathon identity)
    hackathon_name: str = Field(default="OpenHack", description="Hackathon display name")
    hackathon_tagline: str = Field(
        default="The open-source hackathon framework", description="Short tagline shown in UI"
    )
    hackathon_email: str = Field(default="noreply@example.com", description="Default sender email address")
    hackathon_primary_color: str = Field(default="#2563eb", description="Primary brand color (hex)")
    hackathon_logo_url: str = Field(default="/logo.png", description="URL to logo image")
    hackathon_favicon_url: str = Field(default="/logo.png", description="URL to favicon")
    hackathon_year: int = Field(default=2025, description="Current hackathon year")

    # Email configuration
    email_provider: str = Field(default="smtp", description='Email provider: "sendgrid" or "smtp"')
    sendgrid_api_key: str = Field(default="", description="SendGrid API key for email sending")
    smtp_host: str = Field(default="", description="SMTP server hostname")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    smtp_use_tls: bool = Field(default=True, description="Enable STARTTLS for SMTP")
    email_from: str = Field(
        default="", description="[Deprecated] Use hackathon_email instead. Default sender email address"
    )

    model_config = {"env_prefix": "HACKVERIFY_", "env_file": ".env", "extra": "ignore"}

    def get_poolside_key(self) -> str:
        """Return the Poolside API key, falling back to the generic LLM key if empty.

        Behavior:
        1. Return poolside_api_key if it is truthy.
        2. Otherwise, return llm_api_key as the fallback.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: None.
        Consumers: app.assistant.llm.LLMClient initialization.
        """
        return self.poolside_api_key or self.llm_api_key

    def get_llm_key(self) -> str:
        """Return the generic LLM API key, falling back to Poolside key.

        Behavior:
        1. Return llm_api_key if it is truthy.
        2. Otherwise, return poolside_api_key as the fallback.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: None.
        Consumers: get_llm_client factory.
        """
        return self.llm_api_key or self.poolside_api_key


settings = Settings()

# Email settings for backward compatibility with task spec
EMAIL_PROVIDER = settings.email_provider
SENDGRID_API_KEY = settings.sendgrid_api_key
SMTP_HOST = settings.smtp_host
SMTP_PORT = settings.smtp_port
SMTP_USER = settings.smtp_user
SMTP_PASSWORD = settings.smtp_password
SMTP_USE_TLS = settings.smtp_use_tls
EMAIL_FROM = settings.email_from or settings.hackathon_email
