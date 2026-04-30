from apscheduler.triggers.cron import CronTrigger
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/hackverify",
        description="PostgreSQL connection string (asyncpg driver)",
    )
    secret_key: str = Field(
        default="change-me-to-a-secret-key-at-least-32-chars",
        description="JWT signing key (min 32 chars)",
    )
    # OAuth provider credentials
    google_client_id: str = Field(default="", description="Google OAuth client ID")
    google_client_secret: str = Field(default="", description="Google OAuth client secret")
    github_client_id: str = Field(default="", description="GitHub OAuth client ID")
    github_client_secret: str = Field(default="", description="GitHub OAuth client secret")
    discord_client_id: str = Field(default="", description="Discord OAuth client ID")
    discord_client_secret: str = Field(default="", description="Discord OAuth client secret")
    apple_client_id: str = Field(default="", description="Apple Sign In service ID")
    apple_team_id: str = Field(default="", description="Apple Developer Team ID")
    apple_key_id: str = Field(default="", description="Apple private key ID")
    apple_private_key_path: str = Field(default="", description="Path to Apple .p8 private key file")

    github_token: str = Field(
        default="",
        description="GitHub personal access token (optional, increases API rate limit)",
    )
    youtube_api_key: str = Field(
        default="",
        description="YouTube Data API key (optional, enables video timestamp check)",
    )
    llm_api_key: str = Field(
        default="",
        description="API key for LLM-powered checks (Anthropic-compatible endpoint)",
    )
    llm_api_url: str = Field(
        default="https://api.anthropic.com/v1/messages",
        description="LLM API URL (Anthropic Messages endpoint)",
    )
    llm_fast_model: str = Field(
        default="claude-sonnet-4-5",
        description="LLM model name",
    )
    poolside_api_key: str = Field(
        default="",
        description="Poolside API key (OpenAI-compatible)",
    )
    poolside_api_url: str = Field(
        default="https://inference.poolside.ai/v1",
        description="Poolside inference endpoint",
    )
    poolside_model: str = Field(
        default="poolside/laguna-xs.2",
        description="Poolside model name",
    )
    llm_model: str = Field(
        default="claude-sonnet-4-5",
        description="LLM model name",
    )
    llm_fast_model: str = Field(
        default="deepseek-v4-flash",
        description="Faster/cheaper LLM model for alignment checks",
    )

    base_url: str = Field(default="http://localhost:8000", description="Public base URL for QR code and pass links")
    frontend_url: str = Field(default="http://localhost:8000", description="Frontend origin for OAuth redirects (defaults to base_url in production)")
    wallet_logo_url: str = Field(default="", description="Public URL for wallet pass logo image")
    apple_pass_cert_path: str = Field(default="", description="Path to Apple Pass Type ID .p12 certificate")
    apple_pass_cert_password: str = Field(default="", description="Password for the .p12 certificate")
    apple_pass_type_identifier: str = Field(default="pass.com.hackverify.checkin", description="Apple pass type identifier")
    apple_team_identifier: str = Field(default="", description="Apple Developer Team ID")
    google_wallet_credentials_path: str = Field(default="", description="Path to Google Wallet service account JSON")
    google_wallet_issuer_id: str = Field(default="", description="Google Wallet issuer ID")

    crawler_schedule: str = Field(
        default="0 3 * * 0",  # Sunday 3 AM UTC
        description="Cron expression for the weekly crawl (APScheduler format)",
    )
    crawler_refresh_window_days: int = Field(
        default=30,
        gt=0,
        description="Days after hackathon end to keep refreshing for late submissions",
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
