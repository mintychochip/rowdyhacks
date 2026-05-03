import uuid
from datetime import UTC, datetime

import pytest
from app.models import CrawledHackathon, CrawledProject
from sqlalchemy import select
from sqlalchemy.orm import selectinload


@pytest.mark.asyncio
async def test_crawled_hackathon_creation(db_session):
    """Create a CrawledHackathon and verify it persists."""
    h = CrawledHackathon(
        id=uuid.uuid4(),
        devpost_url="https://devpost.com/hackathons/test-fest-2025",
        name="Test Fest 2025",
        start_date=datetime(2025, 6, 1, tzinfo=UTC),
        end_date=datetime(2025, 6, 3, tzinfo=UTC),
        submission_count=120,
    )
    db_session.add(h)
    await db_session.commit()

    result = await db_session.execute(
        select(CrawledHackathon).where(CrawledHackathon.devpost_url == "https://devpost.com/hackathons/test-fest-2025")
    )
    fetched = result.scalar_one()
    assert fetched.id is not None
    assert fetched.devpost_url == "https://devpost.com/hackathons/test-fest-2025"
    assert fetched.name == "Test Fest 2025"
    assert fetched.submission_count == 120
    assert fetched.last_crawled_at is None
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_crawled_project_creation(db_session):
    """Create a CrawledProject linked to a CrawledHackathon and verify it persists."""
    h = CrawledHackathon(
        id=uuid.uuid4(),
        devpost_url="https://devpost.com/hackathons/project-test-fest-2025",
        name="Test Fest 2025",
    )
    db_session.add(h)
    await db_session.flush()

    p = CrawledProject(
        id=uuid.uuid4(),
        devpost_url="https://devpost.com/software/test-project",
        hackathon_id=h.id,
        title="Test Project",
        description="A test project",
        claimed_tech=["python", "react"],
        team_members=[{"name": "Alice", "devpost_profile": "/alice", "github": "https://github.com/alice"}],
        github_url="https://github.com/alice/test-project",
        commit_hash="abc123def456",
        retry_count=0,
    )
    db_session.add(p)
    await db_session.commit()

    result = await db_session.execute(
        select(CrawledProject)
        .where(CrawledProject.devpost_url == "https://devpost.com/software/test-project")
        .options(selectinload(CrawledProject.hackathon))
    )
    fetched = result.scalar_one()
    assert fetched.id is not None
    assert fetched.devpost_url == "https://devpost.com/software/test-project"
    assert fetched.hackathon_id == h.id
    assert fetched.hackathon.name == "Test Fest 2025"
    assert fetched.retry_count == 0
    assert fetched.last_crawled_at is None


@pytest.mark.asyncio
async def test_crawled_project_unique_devpost_url(db_session):
    """Verify that duplicate devpost_url on CrawledProject raises an integrity error."""
    h = CrawledHackathon(
        id=uuid.uuid4(),
        devpost_url="https://devpost.com/hackathons/dup-project-fest",
        name="Duplicate Project Fest",
    )
    db_session.add(h)
    await db_session.flush()

    url = "https://devpost.com/software/duplicate-test"
    p1 = CrawledProject(id=uuid.uuid4(), devpost_url=url, hackathon_id=h.id)
    p2 = CrawledProject(id=uuid.uuid4(), devpost_url=url, hackathon_id=h.id)
    db_session.add_all([p1, p2])
    with pytest.raises(Exception):  # IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_crawled_hackathon_unique_devpost_url(db_session):
    """Verify that duplicate devpost_url on CrawledHackathon raises an integrity error."""
    url = "https://devpost.com/hackathons/unique-required"
    h1 = CrawledHackathon(id=uuid.uuid4(), devpost_url=url, name="First")
    h2 = CrawledHackathon(id=uuid.uuid4(), devpost_url=url, name="Second")
    db_session.add_all([h1, h2])
    with pytest.raises(Exception):  # IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_crawled_project_default_retry_count(db_session):
    """Verify retry_count defaults to 0."""
    h = CrawledHackathon(id=uuid.uuid4(), devpost_url="https://devpost.com/hackathons/defaults", name="Defaults")
    db_session.add(h)
    await db_session.flush()

    p = CrawledProject(
        id=uuid.uuid4(),
        devpost_url="https://devpost.com/software/defaults-test",
        hackathon_id=h.id,
    )
    db_session.add(p)
    await db_session.commit()

    assert p.retry_count == 0
