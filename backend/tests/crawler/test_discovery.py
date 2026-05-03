"""Tests for the hackathon discovery crawler (discovery.py)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.crawler.discovery import discover_hackathons
from app.models import CrawledHackathon


def _make_mock_page(cards_data: list[dict]):
    """Create a mock Playwright page that returns given card data from evaluate()."""
    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value=cards_data)
    mock_page.goto = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.add_init_script = AsyncMock()
    mock_page.wait_for_function = AsyncMock(
        side_effect=Exception("no more content")  # Stop infinite scroll
    )
    return mock_page


def _make_mock_playwright(mock_page):
    """Create mock Playwright object that returns mock_page."""
    mock_browser = AsyncMock()
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_p = AsyncMock()
    mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_playwright_ctx = AsyncMock()
    mock_playwright_ctx.__aenter__ = AsyncMock(return_value=mock_p)
    mock_playwright_ctx.__aexit__ = AsyncMock(return_value=False)

    return mock_playwright_ctx


@pytest.mark.asyncio
async def test_discover_hackathons_inserts_new(db_session, engine):
    """New hackathon URLs should be inserted, duplicates skipped."""
    cards_data = [
        {
            "url": "https://disco-new-fest.devpost.com",
            "name": "New Fest 2025",
            "dates": "Jun 01 - Jun 03, 2025",
            "participants": 100,
        },
        {
            "url": "https://disco-known.devpost.com",
            "name": "Known Discovery 2024",
            "dates": "Jan 01 - Jan 03, 2024",
            "participants": 50,
        },
    ]

    # Seed DB with known hackathon
    db_session.add(
        CrawledHackathon(
            id=uuid.uuid4(),
            devpost_url="https://disco-known.devpost.com",
            name="Known Discovery 2024",
        )
    )
    await db_session.commit()

    mock_page = _make_mock_page(cards_data)

    test_async_session = AsyncMock()
    test_async_session.__aenter__ = AsyncMock(return_value=db_session)
    test_async_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.crawler.discovery.async_playwright", return_value=_make_mock_playwright(mock_page)),
        patch("app.crawler.discovery.async_session", return_value=test_async_session),
    ):
        result = await discover_hackathons()

        assert len(result) == 1  # Only the new one

    # Verify new hackathon inserted
    new_hack = await db_session.execute(
        select(CrawledHackathon).where(CrawledHackathon.devpost_url == "https://disco-new-fest.devpost.com")
    )
    new_row = new_hack.scalar_one_or_none()
    assert new_row is not None
    assert new_row.name == "New Fest 2025"

    # Verify duplicate was not re-inserted
    known_query = await db_session.execute(
        select(CrawledHackathon).where(CrawledHackathon.devpost_url == "https://disco-known.devpost.com")
    )
    assert len(known_query.scalars().all()) == 1


@pytest.mark.asyncio
async def test_discover_hackathons_empty_page(db_session):
    """Empty cards should return no new hackathons."""
    mock_page = _make_mock_page([])

    test_async_session = AsyncMock()
    test_async_session.__aenter__ = AsyncMock(return_value=db_session)
    test_async_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.crawler.discovery.async_playwright", return_value=_make_mock_playwright(mock_page)),
        patch("app.crawler.discovery.async_session", return_value=test_async_session),
    ):
        result = await discover_hackathons()
        assert len(result) == 0
