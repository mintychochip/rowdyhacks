"""Tests for the crawler trigger route (routes/crawler.py)."""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.routes.crawler import _require_organizer


async def _override_organizer():
    return {"sub": "test-user-id", "role": "organizer"}


@pytest.mark.asyncio
async def test_trigger_crawl_returns_409_when_running():
    """POST /api/crawler/trigger returns 409 when a crawl is already in progress."""
    app.dependency_overrides[_require_organizer] = _override_organizer
    try:
        with patch("app.routes.crawler.is_crawling", return_value=True):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/crawler/trigger")
                assert response.status_code == 409
                data = response.json()
                assert "already in progress" in data["detail"]
    finally:
        app.dependency_overrides.pop(_require_organizer, None)


@pytest.mark.asyncio
async def test_trigger_crawl_starts_crawl():
    """POST /api/crawler/trigger returns 202 and starts a crawl."""
    app.dependency_overrides[_require_organizer] = _override_organizer
    try:
        with patch("app.routes.crawler.is_crawling", return_value=False):
            mock_run = AsyncMock(return_value={"new_hackathons": 0, "new_submissions": 0, "scraped_projects": 0})
            with patch("app.routes.crawler.run_crawl", mock_run):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post("/api/crawler/trigger")
                    assert response.status_code == 202
                    data = response.json()
                    assert data["status"] == "started"
                    # Yield to event loop so the fire-and-forget task can execute
                    await asyncio.sleep(0)
                    mock_run.assert_awaited_once()
    finally:
        app.dependency_overrides.pop(_require_organizer, None)
