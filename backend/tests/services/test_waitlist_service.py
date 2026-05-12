"""Tests for WaitlistService."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hackathon, Registration, RegistrationStatus, User, UserRole
from app.services.waitlist_service import WaitlistService


@pytest_asyncio.fixture
async def hackathon_and_organizer(db_session: AsyncSession):
    """Create a hackathon and an organizer user."""
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
        max_participants=2,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    return hackathon, user


@pytest_asyncio.fixture
async def participant(db_session: AsyncSession):
    """Create a participant user."""
    uid = uuid.uuid4().hex[:8]
    user = User(
        id=f"part-{uid}",
        email=f"part-{uid}@example.com",
        name="Test Participant",
        role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def another_participant(db_session: AsyncSession):
    """Create another participant user."""
    uid = uuid.uuid4().hex[:8]
    user = User(
        id=f"part2-{uid}",
        email=f"part2-{uid}@example.com",
        name="Another Participant",
        role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def accepted_registrations(db_session: AsyncSession, hackathon_and_organizer):
    """Create two accepted registrations at capacity."""
    hackathon, _ = hackathon_and_organizer

    uid = uuid.uuid4().hex[:8]
    users = []
    for i in range(2):
        user = User(
            id=f"accepted-user-{i}-{uid}",
            email=f"accepted{i}-{uid}@example.com",
            name=f"Accepted User {i}",
            role=UserRole.participant,
        )
        db_session.add(user)
        users.append(user)

    await db_session.commit()

    regs = []
    for user in users:
        reg = Registration(
            hackathon_id=hackathon.id,
            user_id=user.id,
            status=RegistrationStatus.accepted,
            registered_at=datetime.now(UTC),
        )
        db_session.add(reg)
        regs.append(reg)

    await db_session.commit()
    return hackathon, regs


@pytest.mark.anyio
async def test_auto_waitlist_if_full_when_at_capacity(db_session: AsyncSession, accepted_registrations):
    """auto_waitlist_if_full must return True when hackathon is at capacity."""
    hackathon, _ = accepted_registrations
    service = WaitlistService()

    result = await service.auto_waitlist_if_full(hackathon.id, db_session)
    assert result is True


@pytest.mark.anyio
async def test_auto_waitlist_if_full_when_below_capacity(
    db_session: AsyncSession, hackathon_and_organizer, participant
):
    """auto_waitlist_if_full must return False when hackathon is below capacity."""
    hackathon, _ = hackathon_and_organizer
    service = WaitlistService()

    # No accepted registrations yet
    result = await service.auto_waitlist_if_full(hackathon.id, db_session)
    assert result is False


@pytest.mark.anyio
async def test_auto_waitlist_if_full_no_capacity_limit(db_session: AsyncSession, hackathon_and_organizer):
    """auto_waitlist_if_full must return False when hackathon has no max_participants."""
    hackathon, _ = hackathon_and_organizer
    hackathon.max_participants = None
    await db_session.commit()

    service = WaitlistService()
    result = await service.auto_waitlist_if_full(hackathon.id, db_session)
    assert result is False


@pytest.mark.anyio
async def test_get_waitlist_position(
    db_session: AsyncSession, hackathon_and_organizer, participant, another_participant
):
    """get_waitlist_position must return 1-based position for waitlisted registrations."""
    hackathon, _ = hackathon_and_organizer
    service = WaitlistService()

    reg1 = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.waitlisted,
        registered_at=datetime.now(UTC),
        declined_count=0,
    )
    reg2 = Registration(
        hackathon_id=hackathon.id,
        user_id=another_participant.id,
        status=RegistrationStatus.waitlisted,
        registered_at=datetime.now(UTC),
        declined_count=1,
    )
    db_session.add(reg1)
    db_session.add(reg2)
    await db_session.commit()
    await db_session.refresh(reg1)
    await db_session.refresh(reg2)

    # reg1 has lower declined_count so should be position 1
    pos1 = await service.get_waitlist_position(reg1.id, hackathon.id, db_session)
    assert pos1 == 1

    # reg2 has higher declined_count so should be position 2
    pos2 = await service.get_waitlist_position(reg2.id, hackathon.id, db_session)
    assert pos2 == 2


@pytest.mark.anyio
async def test_get_waitlist_position_not_waitlisted(db_session: AsyncSession, hackathon_and_organizer, participant):
    """get_waitlist_position must return None for non-waitlisted registrations."""
    hackathon, _ = hackathon_and_organizer
    service = WaitlistService()

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.pending,
        registered_at=datetime.now(UTC),
    )
    db_session.add(reg)
    await db_session.commit()
    await db_session.refresh(reg)

    pos = await service.get_waitlist_position(reg.id, hackathon.id, db_session)
    assert pos is None


@pytest.mark.anyio
async def test_get_waitlist_position_empty_waitlist(db_session: AsyncSession, hackathon_and_organizer, participant):
    """get_waitlist_position must return None when waitlist is empty."""
    hackathon, _ = hackathon_and_organizer
    service = WaitlistService()

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.waitlisted,
        registered_at=datetime.now(UTC),
    )
    db_session.add(reg)
    await db_session.commit()
    await db_session.refresh(reg)

    # Querying a different hackathon with no waitlisted entries
    fake_id = uuid.uuid4()
    pos = await service.get_waitlist_position(reg.id, fake_id, db_session)
    assert pos is None


@pytest.mark.anyio
async def test_promote_from_waitlist_success(db_session: AsyncSession, accepted_registrations, participant):
    """promote_from_waitlist must promote top waitlisted registration to offered."""
    hackathon, _ = accepted_registrations
    service = WaitlistService()

    # Create a waitlisted registration
    waitlisted_reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.waitlisted,
        registered_at=datetime.now(UTC),
        declined_count=0,
    )
    db_session.add(waitlisted_reg)
    await db_session.commit()
    await db_session.refresh(waitlisted_reg)

    # Make room for promotion
    hackathon.max_participants = 3
    await db_session.commit()

    with patch("app.services.waitlist_service.send_email", new_callable=AsyncMock):
        promoted = await service.promote_from_waitlist(hackathon.id, db_session)

    assert promoted is not None
    assert promoted.id == waitlisted_reg.id
    assert promoted.status == RegistrationStatus.offered
    assert promoted.offered_at is not None
    assert promoted.offer_expires_at is not None


@pytest.mark.anyio
async def test_promote_from_waitlist_at_capacity_no_spot(db_session: AsyncSession, accepted_registrations, participant):
    """promote_from_waitlist must return None when hackathon is at capacity."""
    hackathon, _ = accepted_registrations
    service = WaitlistService()

    # Fill capacity beyond max (hackathon has max=2, add one more accepted)
    extra_uid = uuid.uuid4().hex[:8]
    extra_user = User(
        id=f"extra-{extra_uid}",
        email=f"extra-{extra_uid}@example.com",
        name="Extra User",
        role=UserRole.participant,
    )
    db_session.add(extra_user)
    await db_session.commit()

    extra_reg = Registration(
        hackathon_id=hackathon.id,
        user_id=extra_user.id,
        status=RegistrationStatus.accepted,
        registered_at=datetime.now(UTC),
    )
    db_session.add(extra_reg)
    await db_session.commit()

    # Create a waitlisted registration
    waitlisted_reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.waitlisted,
        registered_at=datetime.now(UTC),
        declined_count=0,
    )
    db_session.add(waitlisted_reg)
    await db_session.commit()

    promoted = await service.promote_from_waitlist(hackathon.id, db_session)
    assert promoted is None


@pytest.mark.anyio
async def test_promote_from_waitlist_empty_waitlist(db_session: AsyncSession, accepted_registrations):
    """promote_from_waitlist must return None when waitlist is empty."""
    hackathon, _ = accepted_registrations
    service = WaitlistService()

    promoted = await service.promote_from_waitlist(hackathon.id, db_session)
    assert promoted is None


@pytest.mark.anyio
async def test_promote_from_waitlist_sends_email(db_session: AsyncSession, accepted_registrations, participant):
    """promote_from_waitlist must send a spot-offered email."""
    hackathon, _ = accepted_registrations
    service = WaitlistService()

    waitlisted_reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.waitlisted,
        registered_at=datetime.now(UTC),
        declined_count=0,
    )
    db_session.add(waitlisted_reg)
    await db_session.commit()
    await db_session.refresh(waitlisted_reg)

    # Make room for promotion
    hackathon.max_participants = 3
    await db_session.commit()

    with patch("app.services.waitlist_service.send_email", new_callable=AsyncMock) as mock_send:
        promoted = await service.promote_from_waitlist(hackathon.id, db_session)

    assert promoted is not None
    mock_send.assert_awaited_once()
    call_kwargs = mock_send.await_args.kwargs
    assert call_kwargs["to_email"] == participant.email
    assert call_kwargs["email_type"] == "spot_offered"


@pytest.mark.anyio
async def test_promote_from_waitlist_priority_order(
    db_session: AsyncSession, hackathon_and_organizer, participant, another_participant
):
    """promote_from_waitlist must promote registration with lower declined_count first."""
    hackathon, _ = hackathon_and_organizer
    service = WaitlistService()

    # Add one accepted registration to make room for promotion logic
    # (max_participants=2, so one accepted leaves room for one promotion)
    accepted_user = User(
        id=f"accepted-{uuid.uuid4().hex[:8]}",
        email="accepted@example.com",
        name="Accepted User",
        role=UserRole.participant,
    )
    db_session.add(accepted_user)
    await db_session.commit()

    accepted_reg = Registration(
        hackathon_id=hackathon.id,
        user_id=accepted_user.id,
        status=RegistrationStatus.accepted,
        registered_at=datetime.now(UTC),
    )
    db_session.add(accepted_reg)
    await db_session.commit()

    # reg1 has lower declined_count (0) so should be promoted first
    reg1 = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.waitlisted,
        registered_at=datetime.now(UTC),
        declined_count=0,
    )
    reg2 = Registration(
        hackathon_id=hackathon.id,
        user_id=another_participant.id,
        status=RegistrationStatus.waitlisted,
        registered_at=datetime.now(UTC),
        declined_count=1,
    )
    db_session.add(reg1)
    db_session.add(reg2)
    await db_session.commit()
    await db_session.refresh(reg1)
    await db_session.refresh(reg2)

    with patch("app.services.waitlist_service.send_email", new_callable=AsyncMock):
        promoted = await service.promote_from_waitlist(hackathon.id, db_session)

    assert promoted is not None
    assert promoted.id == reg1.id


@pytest.mark.anyio
async def test_backward_compatible_wrapper_functions(db_session: AsyncSession, hackathon_and_organizer, participant):
    """app.waitlist wrapper functions must delegate to WaitlistService."""
    hackathon, _ = hackathon_and_organizer

    from app.waitlist import auto_waitlist_if_full, get_waitlist_position, promote_from_waitlist

    # auto_waitlist_if_full
    result = await auto_waitlist_if_full(hackathon.id, db_session)
    assert result is False

    # get_waitlist_position
    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.waitlisted,
        registered_at=datetime.now(UTC),
    )
    db_session.add(reg)
    await db_session.commit()
    await db_session.refresh(reg)

    pos = await get_waitlist_position(reg.id, hackathon.id, db_session)
    assert pos == 1

    # promote_from_waitlist
    with patch("app.services.waitlist_service.send_email", new_callable=AsyncMock):
        promoted = await promote_from_waitlist(hackathon.id, db_session)
    assert promoted is not None
    assert promoted.status == RegistrationStatus.offered
