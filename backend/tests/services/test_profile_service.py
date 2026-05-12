"""Tests for ProfileService."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hackathon, Registration, RegistrationStatus, User, UserRole
from app.services.profile_service import ProfileService


@pytest_asyncio.fixture
async def hackathon_and_user(db_session: AsyncSession):
    """Create a hackathon and user with accepted registration."""
    from datetime import UTC, datetime

    uid = uuid.uuid4().hex[:8]
    user = User(
        id=f"user-{uid}",
        email=f"{uid}@example.com",
        name="User One",
        role=UserRole.participant,
        bio="Original bio",
        skills=["python"],
        links={"github": "https://github.com/test"},
        availability="Evenings",
        looking_for_team=False,
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

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=user.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg)
    await db_session.commit()

    return hackathon, user


@pytest.mark.anyio
async def test_get_profile(db_session: AsyncSession, hackathon_and_user):
    """ProfileService.get_profile must return the user by ID."""
    _, user = hackathon_and_user
    service = ProfileService()

    profile = await service.get_profile(db_session, user.id)
    assert profile is not None
    assert profile.id == user.id
    assert profile.bio == "Original bio"


@pytest.mark.anyio
async def test_get_profile_missing(db_session: AsyncSession):
    """ProfileService.get_profile must return None for missing user."""
    service = ProfileService()
    profile = await service.get_profile(db_session, "nonexistent-id")
    assert profile is None


@pytest.mark.anyio
async def test_update_profile(db_session: AsyncSession, hackathon_and_user):
    """ProfileService.update_profile must apply selective updates."""
    _, user = hackathon_and_user
    service = ProfileService()

    updated = await service.update_profile(
        db_session,
        user.id,
        bio="Updated bio",
        skills=["go", "rust"],
        links={"portfolio": "https://portfolio.dev"},
        availability="Weekends",
        looking_for_team=True,
    )
    assert updated.bio == "Updated bio"
    assert updated.skills == ["go", "rust"]
    assert updated.links == {"portfolio": "https://portfolio.dev"}
    assert updated.availability == "Weekends"
    assert updated.looking_for_team is True


@pytest.mark.anyio
async def test_update_profile_partial(db_session: AsyncSession, hackathon_and_user):
    """ProfileService.update_profile must leave unspecified fields unchanged."""
    _, user = hackathon_and_user
    service = ProfileService()

    updated = await service.update_profile(db_session, user.id, bio="Only bio changed")
    assert updated.bio == "Only bio changed"
    assert updated.skills == ["python"]
    assert updated.looking_for_team is False


@pytest.mark.anyio
async def test_update_profile_missing_user(db_session: AsyncSession):
    """ProfileService.update_profile must raise ValueError for missing user."""
    service = ProfileService()
    with pytest.raises(ValueError, match="User not found"):
        await service.update_profile(db_session, "nonexistent-id", bio="Nope")


@pytest.mark.anyio
async def test_list_participants(db_session: AsyncSession, hackathon_and_user):
    """ProfileService.list_participants must return accepted participants."""
    hackathon, user = hackathon_and_user
    service = ProfileService()

    participants = await service.list_participants(db_session, hackathon.id)
    assert len(participants) == 1
    assert participants[0].id == user.id
    assert participants[0].bio == "Original bio"
