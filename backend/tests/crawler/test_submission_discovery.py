"""Tests for the submission discovery crawler (submission_discovery.py)."""
import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy import select
from app.models import CrawledHackathon, CrawledProject
from app.crawler.submission_discovery import discover_submissions


def _make_mock_page(links_data: list[str]):
    """Create a mock Playwright page that returns given submission URLs."""
    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value=links_data)
    mock_page.goto = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.add_init_script = AsyncMock()
    mock_page.wait_for_function = AsyncMock(
        side_effect=Exception("no more content")
    )
    return mock_page


def _make_mock_playwright(mock_page):
    mock_browser = AsyncMock()
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()
    mock_p = AsyncMock()
    mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_p)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_ctx


def _make_mock_session(db_session):
    mock_sess = AsyncMock()
    mock_sess.__aenter__ = AsyncMock(return_value=db_session)
    mock_sess.__aexit__ = AsyncMock(return_value=False)
    return mock_sess


@pytest.mark.asyncio
async def test_discover_submissions_inserts_urls(db_session):
    """New submission URLs should be inserted."""
    hackathon_id = uuid.uuid4()
    db_session.add(CrawledHackathon(
        id=hackathon_id,
        devpost_url="https://test-subs-{}.devpost.com".format(uuid.uuid4().hex[:6]),
        name="Test Fest",
    ))
    await db_session.commit()

    links = [
        "https://devpost.com/software/foo",
        "https://devpost.com/software/bar",
    ]
    mock_page = _make_mock_page(links)

    with (
        patch("app.crawler.submission_discovery.async_playwright", return_value=_make_mock_playwright(mock_page)),
        patch("app.crawler.submission_discovery.async_session", return_value=_make_mock_session(db_session)),
    ):
        result = await discover_submissions(hackathon_id, "https://test-subs.devpost.com")
        assert len(result) == 2

    rows = await db_session.execute(
        select(CrawledProject).where(CrawledProject.hackathon_id == hackathon_id)
    )
    assert len(rows.scalars().all()) == 2


@pytest.mark.asyncio
async def test_discover_submissions_deduplicates(db_session):
    """Known URLs should be skipped."""
    hackathon_id = uuid.uuid4()
    db_session.add(CrawledHackathon(
        id=hackathon_id,
        devpost_url="https://test-subs-{}.devpost.com".format(uuid.uuid4().hex[:6]),
        name="Test Fest",
    ))
    await db_session.commit()

    existing_url = "https://devpost.com/software/existing"
    db_session.add(CrawledProject(
        id=uuid.uuid4(),
        devpost_url=existing_url,
        hackathon_id=hackathon_id,
    ))
    await db_session.commit()

    links = [existing_url, "https://devpost.com/software/new-project"]
    mock_page = _make_mock_page(links)

    with (
        patch("app.crawler.submission_discovery.async_playwright", return_value=_make_mock_playwright(mock_page)),
        patch("app.crawler.submission_discovery.async_session", return_value=_make_mock_session(db_session)),
    ):
        result = await discover_submissions(hackathon_id, "https://test-subs.devpost.com")
        assert len(result) == 1  # Only the new one


@pytest.mark.asyncio
async def test_discover_submissions_empty_page(db_session):
    """Empty gallery should return no submissions."""
    hackathon_id = uuid.uuid4()
    db_session.add(CrawledHackathon(
        id=hackathon_id,
        devpost_url="https://test-subs-{}.devpost.com".format(uuid.uuid4().hex[:6]),
        name="Test Fest",
    ))
    await db_session.commit()

    mock_page = _make_mock_page([])

    with (
        patch("app.crawler.submission_discovery.async_playwright", return_value=_make_mock_playwright(mock_page)),
        patch("app.crawler.submission_discovery.async_session", return_value=_make_mock_session(db_session)),
    ):
        result = await discover_submissions(hackathon_id, "https://test-subs.devpost.com")
        assert len(result) == 0
