"""Tests for the submission discovery crawler (submission_discovery.py)."""

import uuid
import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.models import CrawledHackathon, CrawledProject
from app.crawler.submission_discovery import discover_submissions


@pytest.mark.asyncio
async def test_discover_submissions_inserts_urls(db_session, engine):
    """New submission URLs should be discovered and inserted; duplicates skipped."""
    hackathon_id = uuid.uuid4()
    page_html = """
    <html><body>
    <a href="/software/foo">Foo Project</a>
    <a href="/software/bar">Bar Project</a>
    <a href="/hackathons/test-fest">Hackathon link (not a submission)</a>
    </body></html>
    """

    # Seed parent CrawledHackathon for FK constraint
    db_session.add(CrawledHackathon(
        id=hackathon_id,
        devpost_url="https://devpost.com/hackathons/test-fest",
        name="Test Fest",
    ))
    await db_session.commit()

    # Create a session maker that uses the test engine
    test_async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    mock_to_thread = AsyncMock(return_value=page_html)
    with (
        patch("app.crawler.submission_discovery.asyncio.to_thread", mock_to_thread),
        patch("app.crawler.submission_discovery.async_session", test_async_session),
    ):
        result = await discover_submissions(hackathon_id, "https://devpost.com/hackathons/test-fest")
        # Expect 2 submission URLs (/software/foo and /software/bar),
        # but NOT the /hackathons/ link
        assert len(result) == 2

    # Verify the submissions were inserted in the DB with correct FK
    projects = await db_session.execute(
        select(CrawledProject).where(CrawledProject.hackathon_id == hackathon_id)
    )
    rows = projects.scalars().all()
    assert len(rows) == 2

    urls = {r.devpost_url for r in rows}
    assert "https://devpost.com/software/foo" in urls
    assert "https://devpost.com/software/bar" in urls


@pytest.mark.asyncio
async def test_discover_submissions_deduplicates(db_session, engine):
    """Already-known submission URLs should be skipped."""
    hackathon_id = uuid.uuid4()

    page_html = """
    <html><body>
    <a href="/software/known">Known Project</a>
    <a href="/software/new">New Project</a>
    </body></html>
    """

    # Seed parent hackathon
    db_session.add(CrawledHackathon(
        id=hackathon_id,
        devpost_url="https://devpost.com/hackathons/test-fest-2",
        name="Test Fest 2",
    ))
    await db_session.commit()

    # Seed a known project already in the DB
    db_session.add(CrawledProject(
        devpost_url="https://devpost.com/software/known",
        hackathon_id=hackathon_id,
    ))
    await db_session.commit()

    test_async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    mock_to_thread = AsyncMock(return_value=page_html)
    with (
        patch("app.crawler.submission_discovery.asyncio.to_thread", mock_to_thread),
        patch("app.crawler.submission_discovery.async_session", test_async_session),
    ):
        result = await discover_submissions(hackathon_id, "https://devpost.com/hackathons/test-fest-2")
        # Only "new" should be returned; "known" should be skipped
        assert len(result) == 1

    # Verify only 2 total projects exist (1 pre-seeded + 1 new)
    projects = await db_session.execute(
        select(CrawledProject).where(CrawledProject.hackathon_id == hackathon_id)
    )
    rows = projects.scalars().all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_discover_submissions_empty_page_stops(db_session, engine):
    """An empty page with no new URLs should stop pagination."""
    hackathon_id = uuid.uuid4()

    # First page has content, second page has no submission links
    page1_html = """
    <html><body>
    <a href="/software/project-a">Project A</a>
    </body></html>
    """
    page2_html = """
    <html><body>
    <p>No more submissions</p>
    </body></html>
    """

    db_session.add(CrawledHackathon(
        id=hackathon_id,
        devpost_url="https://devpost.com/hackathons/empty-test",
        name="Empty Test",
    ))
    await db_session.commit()

    test_async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Return different HTML on each call (first call -> page1, second -> page2)
    mock_to_thread = AsyncMock(side_effect=[page1_html, page2_html])
    with (
        patch("app.crawler.submission_discovery.asyncio.to_thread", mock_to_thread),
        patch("app.crawler.submission_discovery.async_session", test_async_session),
    ):
        result = await discover_submissions(hackathon_id, "https://devpost.com/hackathons/empty-test")
        assert len(result) == 1
        # Should only have made 2 HTTP calls (page 1 found something, page 2 did not)
        assert mock_to_thread.call_count == 2
