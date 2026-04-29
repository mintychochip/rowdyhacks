import pytest
from pydantic import ValidationError
from app.config import Settings


def test_settings_defaults():
    """Settings should have sensible defaults or be loadable from env."""
    s = Settings(
        _env_file=None,  # don't read .env
        database_url="postgresql+asyncpg://localhost:5432/hackverify",
        secret_key="test-secret-key-min-32-chars!!!!",
        github_token="",
        youtube_api_key="",
    )
    assert s.database_url == "postgresql+asyncpg://localhost:5432/hackverify"
    assert s.secret_key == "test-secret-key-min-32-chars!!!!"
    assert s.github_token == ""
    assert s.youtube_api_key == ""
    assert s.database_url.startswith("postgresql+asyncpg")


def test_secret_key_min_length():
    """secret_key must be at least 32 characters."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+asyncpg://localhost:5432/hackverify",
            secret_key="too-short",
        )


def test_crawler_schedule_default():
    """crawler_schedule should default to Sunday 3 AM UTC."""
    s = Settings(
        database_url="postgresql+asyncpg://localhost:5432/hackverify",
        secret_key="test-secret-key-min-32-chars!!!!",
    )
    assert s.crawler_schedule == "0 3 * * 0"


def test_crawler_refresh_window_default():
    """crawler_refresh_window_days should default to 30."""
    s = Settings(
        database_url="postgresql+asyncpg://localhost:5432/hackverify",
        secret_key="test-secret-key-min-32-chars!!!!",
    )
    assert s.crawler_refresh_window_days == 30


def test_crawler_schedule_override():
    """crawler_schedule should accept a valid override."""
    s = Settings(
        database_url="postgresql+asyncpg://localhost:5432/hackverify",
        secret_key="test-secret-key-min-32-chars!!!!",
        crawler_schedule="*/5 * * * *",
    )
    assert s.crawler_schedule == "*/5 * * * *"


def test_invalid_cron_raises():
    """An invalid cron expression should raise ValidationError."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+asyncpg://localhost:5432/hackverify",
            secret_key="test-secret-key-min-32-chars!!!!",
            crawler_schedule="not-valid",
        )


def test_invalid_refresh_window_raises():
    """A refresh window of 0 or negative should raise ValidationError."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+asyncpg://localhost:5432/hackverify",
            secret_key="test-secret-key-min-32-chars!!!!",
            crawler_refresh_window_days=0,
        )
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+asyncpg://localhost:5432/hackverify",
            secret_key="test-secret-key-min-32-chars!!!!",
            crawler_refresh_window_days=-1,
        )
