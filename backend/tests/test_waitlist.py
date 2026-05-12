"""Tests for waitlist management logic."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import uuid

from app.models import Hackathon, Registration, RegistrationStatus, User, UserRole
from app.waitlist import (
    auto_waitlist_if_full,
    get_waitlist_position,
    promote_from_waitlist,
)


@pytest_asyncio.fixture
async def waitlist_hackathon(db_session):
    """Create a hackathon with a capacity of 2 participants."""
    uid = uuid.uuid4().hex[:8]
    hackathon = Hackathon(
        name=f"Waitlist Hack {uid}",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=f"org-{uid}",
        max_participants=2,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)
    return hackathon


@pytest_asyncio.fixture
async def waitlist_users(db_session, waitlist_hackathon):
    """Create users and registrations: one accepted, two waitlisted (FIFO)."""
    hackathon = waitlist_hackathon
    uid = uuid.uuid4().hex[:8]

    user1 = User(
        id=f"u1-{uid}",
        email=f"u1-{uid}@example.com",
        name="User 1",
        role=UserRole.participant,
    )
    user2 = User(
        id=f"u2-{uid}",
        email=f"u2-{uid}@example.com",
        name="User 2",
        role=UserRole.participant,
    )
    user3 = User(
        id=f"u3-{uid}",
        email=f"u3-{uid}@example.com",
        name="User 3",
        role=UserRole.participant,
    )
    db_session.add_all([user1, user2, user3])
    await db_session.commit()

    reg1 = Registration(
        hackathon_id=hackathon.id,
        user_id=user1.id,
        status=RegistrationStatus.accepted,
    )
    reg2 = Registration(
        hackathon_id=hackathon.id,
        user_id=user2.id,
        status=RegistrationStatus.waitlisted,
        registered_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    reg3 = Registration(
        hackathon_id=hackathon.id,
        user_id=user3.id,
        status=RegistrationStatus.waitlisted,
        registered_at=datetime.now(UTC),
    )
    db_session.add_all([reg1, reg2, reg3])
    await db_session.commit()
    await db_session.refresh(reg2)
    await db_session.refresh(reg3)

    return user1, user2, user3, reg1, reg2, reg3


@pytest.mark.anyio
async def test_promote_from_waitlist_no_waitlisted(db_session, waitlist_hackathon):
    """When nobody is waitlisted, promotion returns None."""
    with patch("app.services.waitlist_service.send_email", new=AsyncMock()):
        result = await promote_from_waitlist(waitlist_hackathon.id, db_session)
    assert result is None


@pytest.mark.anyio
async def test_promote_from_waitlist_at_capacity(db_session, waitlist_hackathon, waitlist_users):
    """When the hackathon is full, promotion returns None."""
    hackathon = waitlist_hackathon
    user1, user2, user3, reg1, reg2, reg3 = waitlist_users

    # Fill capacity (2 accepted)
    uid = uuid.uuid4().hex[:8]
    user4 = User(
        id=f"u4-{uid}",
        email=f"u4-{uid}@example.com",
        name="User 4",
        role=UserRole.participant,
    )
    db_session.add(user4)
    await db_session.commit()

    reg4 = Registration(
        hackathon_id=hackathon.id,
        user_id=user4.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg4)
    await db_session.commit()

    with patch("app.services.waitlist_service.send_email", new=AsyncMock()):
        result = await promote_from_waitlist(hackathon.id, db_session)
    assert result is None


@pytest.mark.anyio
async def test_promote_from_waitlist_success(db_session, waitlist_hackathon, waitlist_users):
    """The top waitlisted registration (earliest FIFO) is promoted to offered."""
    hackathon = waitlist_hackathon
    user1, user2, user3, reg1, reg2, reg3 = waitlist_users

    with patch("app.services.waitlist_service.send_email", new=AsyncMock()) as mock_email:
        result = await promote_from_waitlist(hackathon.id, db_session)

    assert result is not None
    assert result.id == reg2.id
    assert result.status == RegistrationStatus.offered
    assert result.offered_at is not None
    assert result.offer_expires_at is not None
    assert result.offer_expires_at > result.offered_at
    mock_email.assert_awaited_once()


@pytest.mark.anyio
async def test_get_waitlist_position_not_waitlisted(db_session, waitlist_hackathon, waitlist_users):
    """An accepted registration has no waitlist position."""
    hackathon = waitlist_hackathon
    user1, user2, user3, reg1, reg2, reg3 = waitlist_users
    pos = await get_waitlist_position(reg1.id, hackathon.id, db_session)
    assert pos is None


@pytest.mark.anyio
async def test_get_waitlist_position_first(db_session, waitlist_hackathon, waitlist_users):
    """Waitlist position is 1-indexed; reg3 is second in line."""
    hackathon = waitlist_hackathon
    user1, user2, user3, reg1, reg2, reg3 = waitlist_users
    pos = await get_waitlist_position(reg3.id, hackathon.id, db_session)
    assert pos == 2


@pytest.mark.anyio
async def test_get_waitlist_position_ordered_by_declined_count(db_session, waitlist_hackathon):
    """Lower declined_count takes precedence over registration time."""
    hackathon = waitlist_hackathon
    uid = uuid.uuid4().hex[:8]

    user1 = User(
        id=f"u1-{uid}",
        email=f"u1-{uid}@example.com",
        name="U1",
        role=UserRole.participant,
    )
    user2 = User(
        id=f"u2-{uid}",
        email=f"u2-{uid}@example.com",
        name="U2",
        role=UserRole.participant,
    )
    db_session.add_all([user1, user2])
    await db_session.commit()

    reg1 = Registration(
        hackathon_id=hackathon.id,
        user_id=user1.id,
        status=RegistrationStatus.waitlisted,
        declined_count=1,
        registered_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    reg2 = Registration(
        hackathon_id=hackathon.id,
        user_id=user2.id,
        status=RegistrationStatus.waitlisted,
        declined_count=0,
        registered_at=datetime.now(UTC),
    )
    db_session.add_all([reg1, reg2])
    await db_session.commit()

    pos1 = await get_waitlist_position(reg1.id, hackathon.id, db_session)
    pos2 = await get_waitlist_position(reg2.id, hackathon.id, db_session)
    assert pos1 == 2
    assert pos2 == 1


@pytest.mark.anyio
async def test_auto_waitlist_if_full_no_capacity(db_session, waitlist_hackathon):
    """If max_participants is None, the hackathon is never considered full."""
    hackathon = waitlist_hackathon
    hackathon.max_participants = None
    await db_session.commit()
    result = await auto_waitlist_if_full(hackathon.id, db_session)
    assert result is False


@pytest.mark.anyio
async def test_auto_waitlist_if_full_under_capacity(db_session, waitlist_hackathon, waitlist_users):
    """With 1 accepted out of 2 max, the hackathon is not full."""
    hackathon = waitlist_hackathon
    result = await auto_waitlist_if_full(hackathon.id, db_session)
    assert result is False


@pytest.mark.anyio
async def test_auto_waitlist_if_full_at_capacity(db_session, waitlist_hackathon, waitlist_users):
    """With 2 accepted out of 2 max, the hackathon is full."""
    hackathon = waitlist_hackathon
    uid = uuid.uuid4().hex[:8]

    user4 = User(
        id=f"u4-{uid}",
        email=f"u4-{uid}@example.com",
        name="User 4",
        role=UserRole.participant,
    )
    db_session.add(user4)
    await db_session.commit()

    reg4 = Registration(
        hackathon_id=hackathon.id,
        user_id=user4.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg4)
    await db_session.commit()

    result = await auto_waitlist_if_full(hackathon.id, db_session)
    assert result is True
