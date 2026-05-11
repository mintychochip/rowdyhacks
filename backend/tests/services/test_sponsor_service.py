"""Tests for SponsorService."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hackathon, User, UserRole
from app.services.sponsor_service import SponsorService


@pytest_asyncio.fixture
async def hackathon(db_session: AsyncSession):
    from datetime import UTC, datetime

    uid = uuid.uuid4().hex[:8]
    user = User(id=f"org-{uid}", email=f"{uid}@example.com", name="Org", role=UserRole.organizer)
    db_session.add(user)

    hackathon = Hackathon(
        name="Sponsor Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=user.id,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)
    return hackathon


@pytest.mark.anyio
async def test_create_sponsor(db_session: AsyncSession, hackathon):
    service = SponsorService()
    s = await service.create_sponsor(
        db_session,
        hackathon_id=hackathon.id,
        name="Acme Corp",
        tier="gold",
        website_url="https://acme.com",
    )
    assert s.name == "Acme Corp"
    assert s.tier == "gold"
    assert s.hackathon_id == hackathon.id


@pytest.mark.anyio
async def test_list_sponsors(db_session: AsyncSession, hackathon):
    service = SponsorService()
    await service.create_sponsor(db_session, hackathon.id, "Z Corp", tier="bronze")
    await service.create_sponsor(db_session, hackathon.id, "A Corp", tier="platinum")
    await service.create_sponsor(db_session, hackathon.id, "B Corp", tier="platinum")
    sponsors = await service.list_sponsors(db_session, hackathon.id)
    names = [s.name for s in sponsors]
    # Ordered alphabetically by tier, then name: bronze < platinum
    assert names == ["Z Corp", "A Corp", "B Corp"]


@pytest.mark.anyio
async def test_get_sponsor(db_session: AsyncSession, hackathon):
    service = SponsorService()
    s = await service.create_sponsor(db_session, hackathon.id, "Get Me")
    found = await service.get_sponsor(db_session, s.id)
    assert found is not None
    assert found.name == "Get Me"


@pytest.mark.anyio
async def test_update_sponsor(db_session: AsyncSession, hackathon):
    service = SponsorService()
    s = await service.create_sponsor(db_session, hackathon.id, "Old")
    updated = await service.update_sponsor(db_session, s.id, name="New", tier="silver")
    assert updated.name == "New"
    assert updated.tier == "silver"


@pytest.mark.anyio
async def test_delete_sponsor(db_session: AsyncSession, hackathon):
    service = SponsorService()
    s = await service.create_sponsor(db_session, hackathon.id, "Delete Me")
    await service.delete_sponsor(db_session, s.id)
    found = await service.get_sponsor(db_session, s.id)
    assert found is None
