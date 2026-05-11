"""Tests for WorkshopService."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hackathon, User, UserRole
from app.services.workshop_service import WorkshopService


@pytest_asyncio.fixture
async def hackathon(db_session: AsyncSession):
    from datetime import UTC, datetime

    uid = uuid.uuid4().hex[:8]
    user = User(id=f"org-{uid}", email=f"{uid}@example.com", name="Org", role=UserRole.organizer)
    db_session.add(user)

    hackathon = Hackathon(
        name="Workshop Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=user.id,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)
    return hackathon


@pytest.mark.anyio
async def test_create_workshop(db_session: AsyncSession, hackathon):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="Intro to Python",
        description="Basics",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
        location="Room A",
        speaker_name="Alice",
    )
    assert ws.title == "Intro to Python"
    assert ws.location == "Room A"
    assert ws.hackathon_id == hackathon.id


@pytest.mark.anyio
async def test_list_workshops(db_session: AsyncSession, hackathon):
    from datetime import UTC, datetime

    service = WorkshopService()
    await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="WS1",
        start_time=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
    )
    await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="WS2",
        start_time=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
    )
    workshops = await service.list_workshops(db_session, hackathon.id)
    assert len(workshops) == 2
    titles = [w.title for w in workshops]
    assert titles == ["WS2", "WS1"]  # Ordered by start_time


@pytest.mark.anyio
async def test_get_workshop(db_session: AsyncSession, hackathon):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="Get Me",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    found = await service.get_workshop(db_session, ws.id)
    assert found is not None
    assert found.title == "Get Me"


@pytest.mark.anyio
async def test_update_workshop(db_session: AsyncSession, hackathon):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="Old",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    updated = await service.update_workshop(db_session, ws.id, title="New")
    assert updated.title == "New"


@pytest.mark.anyio
async def test_delete_workshop(db_session: AsyncSession, hackathon):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="Delete Me",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    await service.delete_workshop(db_session, ws.id)
    found = await service.get_workshop(db_session, ws.id)
    assert found is None
