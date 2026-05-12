"""Tests for CrawlerService."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CrawledHackathon, CrawledProject
from app.services.crawler_service import CrawlerService


@pytest.mark.anyio
async def test_create_hackathon(db_session: AsyncSession):
    """CrawlerService.create_hackathon must persist a new CrawledHackathon."""
    service = CrawlerService()
    hackathon = await service.create_hackathon(
        db=db_session,
        devpost_url="https://testhack.devpost.com",
        name="Test Hackathon",
        start_date=datetime(2025, 1, 1, tzinfo=UTC),
        end_date=datetime(2025, 1, 3, tzinfo=UTC),
    )
    assert hackathon.id is not None
    assert hackathon.devpost_url == "https://testhack.devpost.com"
    assert hackathon.name == "Test Hackathon"
    assert hackathon.last_crawled_at is not None

    # Verify in DB
    result = await db_session.execute(select(CrawledHackathon).where(CrawledHackathon.id == hackathon.id))
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.name == "Test Hackathon"


@pytest.mark.anyio
async def test_list_hackathons_with_counts(db_session: AsyncSession):
    """list_hackathons must include project counts."""
    service = CrawlerService()
    hk = await service.create_hackathon(db_session, "https://hk1.devpost.com", "HK One", datetime.now(UTC))
    await db_session.commit()

    # Add two projects
    p1 = CrawledProject(devpost_url="https://p1.devpost.com", hackathon_id=hk.id, title="Project 1")
    p2 = CrawledProject(devpost_url="https://p2.devpost.com", hackathon_id=hk.id, title="Project 2")
    db_session.add_all([p1, p2])
    await db_session.commit()

    rows = await service.list_hackathons(db_session)
    hk_row = next(r for r in rows if r["id"] == str(hk.id))
    assert hk_row["project_count"] == 2


@pytest.mark.anyio
async def test_list_projects_pagination(db_session: AsyncSession):
    """list_projects must return paginated projects for a hackathon."""
    service = CrawlerService()
    hk = await service.create_hackathon(db_session, "https://hk2.devpost.com", "HK Two", datetime.now(UTC))
    await db_session.commit()

    for i in range(5):
        db_session.add(
            CrawledProject(devpost_url=f"https://proj{i}.devpost.com", hackathon_id=hk.id, title=f"Proj {i}")
        )
    await db_session.commit()

    data = await service.list_projects(db_session, hk.id, offset=0, limit=3)
    assert data["total"] == 5
    assert len(data["projects"]) == 3
    assert data["hackathon"]["id"] == str(hk.id)


@pytest.mark.anyio
async def test_list_projects_invalid_hackathon(db_session: AsyncSession):
    """list_projects must raise ValueError for missing hackathon."""
    service = CrawlerService()
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Hackathon not found"):
        await service.list_projects(db_session, fake_id)


@pytest.mark.anyio
async def test_search_projects_by_title(db_session: AsyncSession):
    """search_projects must filter by title."""
    service = CrawlerService()
    hk = await service.create_hackathon(db_session, "https://hk3.devpost.com", "HK Three", datetime.now(UTC))
    await db_session.commit()

    db_session.add_all(
        [
            CrawledProject(devpost_url="https://alpha.devpost.com", hackathon_id=hk.id, title="Alpha Bot"),
            CrawledProject(devpost_url="https://beta.devpost.com", hackathon_id=hk.id, title="Beta App"),
        ]
    )
    await db_session.commit()

    data = await service.search_projects(db_session, query_str="alpha", offset=0, limit=10)
    assert data["total"] == 1
    assert data["projects"][0]["title"] == "Alpha Bot"


@pytest.mark.anyio
async def test_get_hackathon(db_session: AsyncSession):
    """get_hackathon must return a CrawledHackathon by UUID."""
    service = CrawlerService()
    hk = await service.create_hackathon(db_session, "https://hk4.devpost.com", "HK Four", datetime.now(UTC))
    await db_session.commit()

    fetched = await service.get_hackathon(db_session, hk.id)
    assert fetched is not None
    assert fetched.id == hk.id

    missing = await service.get_hackathon(db_session, uuid.uuid4())
    assert missing is None
