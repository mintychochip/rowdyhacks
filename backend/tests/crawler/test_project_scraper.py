"""Tests for the per-project scraper (project_scraper.py)."""

import uuid
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.models import CrawledHackathon, CrawledProject
from app.crawler.project_scraper import scrape_projects


@pytest.mark.asyncio
async def test_scrape_projects_fills_metadata(db_session, engine):
    """Projects with last_crawled_at=NULL and retry_count<3 should get scraped."""
    h = CrawledHackathon(
        id=uuid.uuid4(),
        devpost_url="https://devpost.com/hackathons/project-scraper-fest",
        name="Project Scraper Fest",
    )
    db_session.add(h)
    await db_session.commit()

    p = CrawledProject(
        id=uuid.uuid4(),
        devpost_url="https://devpost.com/software/scraper-test-project",
        hackathon_id=h.id,
        retry_count=0,
    )
    db_session.add(p)
    await db_session.commit()

    mock_scraped = MagicMock()
    mock_scraped.title = "Test Project"
    mock_scraped.description = "A test"
    mock_scraped.claimed_tech = ["python"]
    mock_scraped.team_members = [{"name": "Alice", "devpost_profile": "/alice", "github": None}]
    mock_scraped.github_url = "https://github.com/alice/test"
    mock_scraped.video_url = None
    mock_scraped.slides_url = None

    test_async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    with (
        patch("app.crawler.project_scraper.scrape_devpost", return_value=mock_scraped),
        patch("app.crawler.project_scraper._get_head_commit", return_value="abc123"),
        patch("app.crawler.project_scraper.async_session", test_async_session),
    ):
        await scrape_projects(batch_size=10)

    await db_session.refresh(p)
    assert p.title == "Test Project"
    assert p.github_url == "https://github.com/alice/test"
    assert p.commit_hash == "abc123"
    assert p.retry_count == 0
    assert p.last_crawled_at is not None


@pytest.mark.asyncio
async def test_scrape_projects_increments_retry_on_failure(db_session, engine):
    """Failed scrapes should increment retry_count, not set last_crawled_at."""
    h = CrawledHackathon(
        id=uuid.uuid4(),
        devpost_url="https://devpost.com/hackathons/retry-fest",
        name="Retry Fest",
    )
    db_session.add(h)
    await db_session.commit()

    p = CrawledProject(
        id=uuid.uuid4(),
        devpost_url="https://devpost.com/software/failing-project",
        hackathon_id=h.id,
        retry_count=0,
    )
    db_session.add(p)
    await db_session.commit()

    test_async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    with (
        patch("app.crawler.project_scraper.scrape_devpost", side_effect=Exception("boom")),
        patch("app.crawler.project_scraper._get_head_commit", return_value="abc123"),
        patch("app.crawler.project_scraper.async_session", test_async_session),
    ):
        await scrape_projects(batch_size=10)

    await db_session.refresh(p)
    assert p.retry_count == 1
    assert p.last_crawled_at is None


@pytest.mark.asyncio
async def test_scrape_projects_skips_max_retries(db_session, engine):
    """Projects with retry_count >= 3 should be skipped."""
    h = CrawledHackathon(
        id=uuid.uuid4(),
        devpost_url="https://devpost.com/hackathons/skip-fest",
        name="Skip Fest",
    )
    db_session.add(h)
    await db_session.commit()

    p = CrawledProject(
        id=uuid.uuid4(),
        devpost_url="https://devpost.com/software/skipped-project",
        hackathon_id=h.id,
        retry_count=3,
    )
    db_session.add(p)
    await db_session.commit()

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return MagicMock(title="X", description="", claimed_tech=[], team_members=[], github_url=None, video_url=None, slides_url=None)

    test_async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    with (
        patch("app.crawler.project_scraper.scrape_devpost", side_effect=side_effect),
        patch("app.crawler.project_scraper._get_head_commit", return_value="abc123"),
        patch("app.crawler.project_scraper.async_session", test_async_session),
    ):
        await scrape_projects(batch_size=10)

    # The project with retry_count=3 should not have been modified
    await db_session.refresh(p)
    assert p.retry_count == 3
    assert p.last_crawled_at is None
