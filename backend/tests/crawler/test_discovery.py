"""Tests for the hackathon discovery crawler (discovery.py)."""

import uuid
import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.models import CrawledHackathon
from app.crawler.discovery import discover_hackathons


@pytest.mark.asyncio
async def test_discover_hackathons_inserts_new(db_session, engine):
    """New hackathon URLs should be inserted, duplicates skipped."""
    page_html = """
    <html><body>
    <div class="hackathon-card">
        <a href="/hackathons/new-fest-2025">New Fest 2025</a>
        <span class="date">Jun 1 - Jun 3, 2025</span>
    </div>
    <div class="hackathon-card">
        <a href="/hackathons/known-discovery-2024">Known Discovery 2024</a>
        <span class="date">Jan 1 - Jan 3, 2024</span>
    </div>
    </body></html>
    """

    # Seed DB with known hackathon to test dedup
    db_session.add(CrawledHackathon(
        id=uuid.uuid4(),
        devpost_url="https://devpost.com/hackathons/known-discovery-2024",
        name="Known Discovery 2024",
    ))
    await db_session.commit()

    # Create a session maker that uses the test engine (same as conftest)
    test_async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    mock_to_thread = AsyncMock(return_value=page_html)
    with (
        patch("app.crawler.discovery.asyncio.to_thread", mock_to_thread),
        patch("app.crawler.discovery.async_session", test_async_session),
    ):
        result = await discover_hackathons()
        # Only the NEW hackathon (new-fest-2025) should be returned
        assert len(result) == 1

    # Verify the new hackathon was inserted in the DB
    new_hack = await db_session.execute(
        select(CrawledHackathon).where(
            CrawledHackathon.devpost_url == "https://devpost.com/hackathons/new-fest-2025"
        )
    )
    assert new_hack.scalar_one_or_none() is not None

    # Verify the duplicate was NOT inserted again
    known_query = await db_session.execute(
        select(CrawledHackathon).where(
            CrawledHackathon.devpost_url == "https://devpost.com/hackathons/known-discovery-2024"
        )
    )
    known_rows = known_query.scalars().all()
    assert len(known_rows) == 1  # Only the one we seeded
