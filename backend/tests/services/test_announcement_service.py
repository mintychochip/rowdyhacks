"""Tests for AnnouncementService."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Announcement, Hackathon, User, UserRole
from app.services.announcement_service import AnnouncementService


@pytest_asyncio.fixture
async def hackathon_and_organizer(db_session: AsyncSession):
    """Create a hackathon and an organizer user."""
    from datetime import UTC, datetime

    uid = uuid.uuid4().hex[:8]
    user = User(
        id=f"org-{uid}",
        email=f"org-{uid}@example.com",
        name="Test Organizer",
        role=UserRole.organizer,
    )
    db_session.add(user)

    hackathon = Hackathon(
        name="Test Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=user.id,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    return hackathon, user


@pytest.mark.anyio
async def test_create_announcement(db_session: AsyncSession, hackathon_and_organizer):
    """AnnouncementService.create_announcement must create and return an announcement."""
    hackathon, user = hackathon_and_organizer
    service = AnnouncementService()

    with patch("app.services.event_service.publish_event", new_callable=AsyncMock):
        announcement = await service.create_announcement(db_session, hackathon.id, user.id, "Hello", "World", "high")

    assert announcement.title == "Hello"
    assert announcement.content == "World"
    assert announcement.priority == "high"
    assert announcement.hackathon_id == hackathon.id
    assert announcement.sent_by == user.id


@pytest.mark.anyio
async def test_list_announcements_as_organizer(db_session: AsyncSession, hackathon_and_organizer):
    """list_announcements for organizer must include draft announcements."""
    hackathon, user = hackathon_and_organizer
    service = AnnouncementService()

    a1 = Announcement(hackathon_id=hackathon.id, title="Public", content="Body", priority="normal", sent_by=user.id)
    a2 = Announcement(hackathon_id=hackathon.id, title="Draft", content="Secret", priority="draft", sent_by=user.id)
    db_session.add_all([a1, a2])
    await db_session.commit()

    announcements = await service.list_announcements(db_session, hackathon.id, is_organizer=True)
    assert len(announcements) == 2
    titles = {a.title for a in announcements}
    assert titles == {"Public", "Draft"}


@pytest.mark.anyio
async def test_list_announcements_as_participant(db_session: AsyncSession, hackathon_and_organizer):
    """list_announcements for non-organizer must filter out draft announcements."""
    hackathon, user = hackathon_and_organizer
    service = AnnouncementService()

    a1 = Announcement(hackathon_id=hackathon.id, title="Public", content="Body", priority="normal", sent_by=user.id)
    a2 = Announcement(hackathon_id=hackathon.id, title="Draft", content="Secret", priority="draft", sent_by=user.id)
    db_session.add_all([a1, a2])
    await db_session.commit()

    announcements = await service.list_announcements(db_session, hackathon.id, is_organizer=False)
    assert len(announcements) == 1
    assert announcements[0].title == "Public"
