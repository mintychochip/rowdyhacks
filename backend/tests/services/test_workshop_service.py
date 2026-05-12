"""Tests for WorkshopService."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hackathon, User, UserRole, WorkshopRSVPStatus
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


@pytest_asyncio.fixture
async def participant(db_session: AsyncSession):
    uid = uuid.uuid4().hex[:8]
    user = User(id=f"user-{uid}", email=f"{uid}@example.com", name="Participant", role=UserRole.participant)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


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


# --- RSVP tests ---


@pytest.mark.anyio
async def test_register_for_workshop(db_session: AsyncSession, hackathon, participant):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="RSVP Workshop",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
        max_capacity=10,
    )
    rsvp = await service.register_for_workshop(db_session, ws.id, participant.id, hackathon.id)
    assert rsvp.user_id == participant.id
    assert rsvp.workshop_id == ws.id
    assert rsvp.status == WorkshopRSVPStatus.registered


@pytest.mark.anyio
async def test_register_already_registered(db_session: AsyncSession, hackathon, participant):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="RSVP Workshop",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    await service.register_for_workshop(db_session, ws.id, participant.id, hackathon.id)
    with pytest.raises(ValueError, match="Already registered"):
        await service.register_for_workshop(db_session, ws.id, participant.id, hackathon.id)


@pytest.mark.anyio
async def test_register_at_capacity(db_session: AsyncSession, hackathon, participant):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="Full Workshop",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
        max_capacity=1,
    )
    await service.register_for_workshop(db_session, ws.id, participant.id, hackathon.id)
    other_user = User(id="other-user", email="other@example.com", name="Other", role=UserRole.participant)
    db_session.add(other_user)
    await db_session.commit()
    with pytest.raises(ValueError, match="at capacity"):
        await service.register_for_workshop(db_session, ws.id, other_user.id, hackathon.id)


@pytest.mark.anyio
async def test_register_workshop_not_found(db_session: AsyncSession, hackathon, participant):
    service = WorkshopService()
    with pytest.raises(ValueError, match="Workshop not found"):
        await service.register_for_workshop(db_session, uuid.uuid4(), participant.id, hackathon.id)


@pytest.mark.anyio
async def test_cancel_rsvp(db_session: AsyncSession, hackathon, participant):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="Cancel Workshop",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    await service.register_for_workshop(db_session, ws.id, participant.id, hackathon.id)
    rsvp = await service.cancel_rsvp(db_session, ws.id, participant.id)
    assert rsvp.status == WorkshopRSVPStatus.cancelled


@pytest.mark.anyio
async def test_cancel_rsvp_not_found(db_session: AsyncSession, hackathon, participant):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="Cancel Workshop",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    with pytest.raises(ValueError, match="RSVP not found"):
        await service.cancel_rsvp(db_session, ws.id, participant.id)


@pytest.mark.anyio
async def test_mark_attended(db_session: AsyncSession, hackathon, participant):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="Attend Workshop",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    await service.register_for_workshop(db_session, ws.id, participant.id, hackathon.id)
    rsvp = await service.mark_attended(db_session, ws.id, participant.id)
    assert rsvp.status == WorkshopRSVPStatus.attended
    assert rsvp.attended_at is not None


@pytest.mark.anyio
async def test_mark_attended_not_found(db_session: AsyncSession, hackathon, participant):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="Attend Workshop",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    with pytest.raises(ValueError, match="RSVP not found"):
        await service.mark_attended(db_session, ws.id, participant.id)


@pytest.mark.anyio
async def test_list_rsvps_for_workshop(db_session: AsyncSession, hackathon, participant):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="List RSVP Workshop",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    await service.register_for_workshop(db_session, ws.id, participant.id, hackathon.id)
    rsvps = await service.list_rsvps_for_workshop(db_session, ws.id)
    assert len(rsvps) == 1
    assert rsvps[0].user_id == participant.id


@pytest.mark.anyio
async def test_list_rsvps_for_workshop_excludes_cancelled(db_session: AsyncSession, hackathon, participant):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="List RSVP Workshop",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    await service.register_for_workshop(db_session, ws.id, participant.id, hackathon.id)
    await service.cancel_rsvp(db_session, ws.id, participant.id)
    rsvps = await service.list_rsvps_for_workshop(db_session, ws.id)
    assert len(rsvps) == 0


@pytest.mark.anyio
async def test_list_rsvps_for_user(db_session: AsyncSession, hackathon, participant):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="User RSVP Workshop",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    await service.register_for_workshop(db_session, ws.id, participant.id, hackathon.id)
    rsvps = await service.list_rsvps_for_user(db_session, participant.id, hackathon.id)
    assert len(rsvps) == 1
    assert rsvps[0].workshop_id == ws.id


@pytest.mark.anyio
async def test_get_workshop_capacity_status(db_session: AsyncSession, hackathon, participant):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="Capacity Workshop",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
        max_capacity=5,
    )
    status = await service.get_workshop_capacity_status(db_session, ws.id)
    assert status["max_capacity"] == 5
    assert status["current_count"] == 0
    assert status["available"] == 5
    assert status["is_full"] is False

    await service.register_for_workshop(db_session, ws.id, participant.id, hackathon.id)
    status = await service.get_workshop_capacity_status(db_session, ws.id)
    assert status["current_count"] == 1
    assert status["available"] == 4
    assert status["is_full"] is False


@pytest.mark.anyio
async def test_get_workshop_capacity_status_no_limit(db_session: AsyncSession, hackathon, participant):
    from datetime import UTC, datetime

    service = WorkshopService()
    ws = await service.create_workshop(
        db_session,
        hackathon_id=hackathon.id,
        title="Unlimited Workshop",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    status = await service.get_workshop_capacity_status(db_session, ws.id)
    assert status["max_capacity"] is None
    assert status["current_count"] == 0
    assert status["available"] is None
    assert status["is_full"] is False
