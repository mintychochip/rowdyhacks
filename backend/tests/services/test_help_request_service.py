"""Tests for HelpRequestService."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hackathon, User, UserRole
from app.services.help_request_service import HelpRequestService


@pytest_asyncio.fixture
async def hackathon_and_requester(db_session: AsyncSession):
    from datetime import UTC, datetime

    uid = uuid.uuid4().hex[:8]
    user = User(id=f"req-{uid}", email=f"{uid}@example.com", name="Req", role=UserRole.participant)
    db_session.add(user)

    hackathon = Hackathon(
        name="Help Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=user.id,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)
    return hackathon, user


@pytest.mark.anyio
async def test_create_help_request(db_session: AsyncSession, hackathon_and_requester):
    hackathon, user = hackathon_and_requester
    service = HelpRequestService()
    req = await service.create_help_request(
        db_session,
        hackathon_id=hackathon.id,
        requester_id=user.id,
        title="Need help with React",
        description="Stuck on hooks",
    )
    assert req.title == "Need help with React"
    assert req.status == "open"
    assert req.requester_id == user.id


@pytest.mark.anyio
async def test_list_open_requests(db_session: AsyncSession, hackathon_and_requester):
    hackathon, user = hackathon_and_requester
    service = HelpRequestService()
    await service.create_help_request(db_session, hackathon.id, user.id, "A")
    await service.create_help_request(db_session, hackathon.id, user.id, "B")
    open_reqs = await service.list_open_requests(db_session, hackathon.id)
    assert len(open_reqs) == 2


@pytest.mark.anyio
async def test_claim_help_request(db_session: AsyncSession, hackathon_and_requester):
    hackathon, user = hackathon_and_requester
    service = HelpRequestService()
    req = await service.create_help_request(db_session, hackathon.id, user.id, "Claim Me")

    mentor = User(id="mentor-1", email="m@example.com", name="Mentor", role=UserRole.participant)
    db_session.add(mentor)
    await db_session.commit()

    claimed = await service.claim_help_request(db_session, req.id, mentor.id)
    assert claimed.status == "claimed"
    assert claimed.mentor_id == mentor.id
    assert claimed.claimed_at is not None


@pytest.mark.anyio
async def test_resolve_help_request(db_session: AsyncSession, hackathon_and_requester):
    hackathon, user = hackathon_and_requester
    service = HelpRequestService()
    req = await service.create_help_request(db_session, hackathon.id, user.id, "Resolve Me")
    resolved = await service.resolve_help_request(db_session, req.id)
    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None


@pytest.mark.anyio
async def test_delete_help_request(db_session: AsyncSession, hackathon_and_requester):
    hackathon, user = hackathon_and_requester
    service = HelpRequestService()
    req = await service.create_help_request(db_session, hackathon.id, user.id, "Delete Me")
    await service.delete_help_request(db_session, req.id)
    found = await service.get_help_request(db_session, req.id)
    assert found is None
