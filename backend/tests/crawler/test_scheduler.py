"""Tests for the crawl scheduler (scheduler.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.scheduler import run_crawl


def _make_mock_session() -> AsyncMock:
    """Create a mocked async session whose execute returns an empty scalars result."""
    session = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute.return_value = result_mock
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    return session


@pytest.mark.asyncio
async def test_run_crawl_prevents_concurrent_runs():
    """When already running, second call should raise RuntimeError."""
    with patch("app.crawler.scheduler._crawler_running", True):
        with pytest.raises(RuntimeError, match="already in progress"):
            await run_crawl()


@pytest.mark.asyncio
async def test_run_crawl_sets_and_clears_flag():
    """After a successful crawl, _crawler_running should be False."""
    mock_session = _make_mock_session()
    with patch("app.crawler.scheduler.discover_hackathons", new_callable=AsyncMock) as mock_discover:
        with patch("app.crawler.scheduler.discover_submissions", new_callable=AsyncMock) as mock_disc_sub:
            with patch("app.crawler.scheduler.scrape_projects", new_callable=AsyncMock) as mock_scrape:
                with patch("app.crawler.scheduler.async_session", return_value=mock_session):
                    mock_discover.return_value = []
                    mock_disc_sub.return_value = []
                    mock_scrape.return_value = 0

                    await run_crawl()

                    from app.crawler.scheduler import _crawler_running

                    assert _crawler_running is False
