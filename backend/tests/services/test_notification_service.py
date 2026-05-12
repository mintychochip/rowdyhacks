"""Tests for NotificationService."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Hackathon,
    Notification,
    NotificationType,
    Registration,
    RegistrationStatus,
    User,
    UserRole,
)
from app.services.notification_service import NotificationService


@pytest_asyncio.fixture
async def hackathon_and_user(db_session: AsyncSession):
    """Create a hackathon and user with accepted registration (unique IDs per test)."""
    from datetime import UTC, datetime

    uid = uuid.uuid4().hex[:8]
    user = User(
        id=f"user-{uid}",
        email=f"{uid}@example.com",
        name="User One",
        role=UserRole.participant,
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
async def test_create_notification(db_session: AsyncSession, hackathon_and_user):
    """create_notification must persist a notification with correct fields."""
    hackathon, user = hackathon_and_user
    service = NotificationService()

    notification = await service.create_notification(
        db_session,
        user_id=user.id,
        title="Hello",
        message="World",
        type=NotificationType.success,
        hackathon_id=hackathon.id,
        action_url="https://example.com",
        action_text="Go",
    )

    assert notification.title == "Hello"
    assert notification.message == "World"
    assert notification.type == NotificationType.success
    assert notification.user_id == user.id
    assert notification.hackathon_id == hackathon.id
    assert notification.action_url == "https://example.com"
    assert notification.action_text == "Go"
    assert notification.read_at is None
    assert notification.created_at is not None


@pytest.mark.anyio
async def test_mark_as_read(db_session: AsyncSession, hackathon_and_user):
    """mark_as_read must set read_at for an owned notification."""
    hackathon, user = hackathon_and_user
    service = NotificationService()

    notification = await service.create_notification(db_session, user_id=user.id, title="T", message="M")
    assert notification.read_at is None

    updated = await service.mark_as_read(db_session, notification.id, user.id)
    assert updated.read_at is not None

    # Verify in DB
    result = await db_session.execute(select(Notification).where(Notification.id == notification.id))
    row = result.scalar_one()
    assert row.read_at is not None


@pytest.mark.anyio
async def test_mark_as_read_rejects_other_user(db_session: AsyncSession, hackathon_and_user):
    """mark_as_read must reject a notification owned by another user."""
    hackathon, user = hackathon_and_user
    service = NotificationService()

    notification = await service.create_notification(db_session, user_id=user.id, title="T", message="M")

    with pytest.raises(ValueError, match="Notification not found"):
        await service.mark_as_read(db_session, notification.id, "other-user-id")


@pytest.mark.anyio
async def test_mark_all_as_read(db_session: AsyncSession, hackathon_and_user):
    """mark_all_as_read must mark all unread notifications for a user as read."""
    hackathon, user = hackathon_and_user
    service = NotificationService()

    await service.create_notification(db_session, user_id=user.id, title="A", message="1")
    await service.create_notification(db_session, user_id=user.id, title="B", message="2")

    count = await service.mark_all_as_read(db_session, user_id=user.id)
    assert count == 2

    unread = await service.get_unread_count(db_session, user_id=user.id)
    assert unread == 0


@pytest.mark.anyio
async def test_mark_all_as_read_by_hackathon(db_session: AsyncSession, hackathon_and_user):
    """mark_all_as_read must restrict to a hackathon when provided."""
    hackathon, user = hackathon_and_user
    service = NotificationService()

    # Create another hackathon
    from datetime import UTC, datetime

    hackathon2 = Hackathon(
        name="Other Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=user.id,
    )
    db_session.add(hackathon2)
    await db_session.commit()
    await db_session.refresh(hackathon2)

    await service.create_notification(db_session, user_id=user.id, title="H1", message="m", hackathon_id=hackathon.id)
    await service.create_notification(db_session, user_id=user.id, title="H2", message="m", hackathon_id=hackathon2.id)

    count = await service.mark_all_as_read(db_session, user_id=user.id, hackathon_id=hackathon.id)
    assert count == 1

    unread = await service.get_unread_count(db_session, user_id=user.id)
    assert unread == 1


@pytest.mark.anyio
async def test_get_unread_count(db_session: AsyncSession, hackathon_and_user):
    """get_unread_count must return the correct number of unread notifications."""
    hackathon, user = hackathon_and_user
    service = NotificationService()

    assert await service.get_unread_count(db_session, user_id=user.id) == 0

    await service.create_notification(db_session, user_id=user.id, title="A", message="1")
    assert await service.get_unread_count(db_session, user_id=user.id) == 1

    await service.create_notification(db_session, user_id=user.id, title="B", message="2")
    assert await service.get_unread_count(db_session, user_id=user.id) == 2


@pytest.mark.anyio
async def test_list_notifications(db_session: AsyncSession, hackathon_and_user):
    """list_notifications must paginate and filter correctly."""
    hackathon, user = hackathon_and_user
    service = NotificationService()

    n1 = await service.create_notification(db_session, user_id=user.id, title="First", message="1")
    n2 = await service.create_notification(db_session, user_id=user.id, title="Second", message="2")

    # Default ordering is newest first
    items = await service.list_notifications(db_session, user_id=user.id)
    assert len(items) == 2
    assert items[0].id == n2.id
    assert items[1].id == n1.id

    # Limit
    items = await service.list_notifications(db_session, user_id=user.id, limit=1)
    assert len(items) == 1
    assert items[0].id == n2.id

    # Offset
    items = await service.list_notifications(db_session, user_id=user.id, limit=1, offset=1)
    assert len(items) == 1
    assert items[0].id == n1.id


@pytest.mark.anyio
async def test_list_notifications_unread_only(db_session: AsyncSession, hackathon_and_user):
    """list_notifications with unread_only must exclude read items."""
    hackathon, user = hackathon_and_user
    service = NotificationService()

    n1 = await service.create_notification(db_session, user_id=user.id, title="Unread", message="1")
    n2 = await service.create_notification(db_session, user_id=user.id, title="Read", message="2")
    await service.mark_as_read(db_session, n2.id, user.id)

    items = await service.list_notifications(db_session, user_id=user.id, unread_only=True)
    assert len(items) == 1
    assert items[0].id == n1.id


@pytest.mark.anyio
async def test_delete_notification(db_session: AsyncSession, hackathon_and_user):
    """delete_notification must remove an owned notification."""
    hackathon, user = hackathon_and_user
    service = NotificationService()

    n = await service.create_notification(db_session, user_id=user.id, title="T", message="M")
    await service.delete_notification(db_session, n.id, user.id)

    result = await db_session.execute(select(Notification).where(Notification.id == n.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.anyio
async def test_delete_notification_rejects_other_user(db_session: AsyncSession, hackathon_and_user):
    """delete_notification must reject a notification owned by another user."""
    hackathon, user = hackathon_and_user
    service = NotificationService()

    n = await service.create_notification(db_session, user_id=user.id, title="T", message="M")

    with pytest.raises(ValueError, match="Notification not found"):
        await service.delete_notification(db_session, n.id, "other-user-id")


@pytest.mark.anyio
async def test_broadcast_to_hackathon(db_session: AsyncSession, hackathon_and_user):
    """broadcast_to_hackathon must create a notification for every accepted registrant."""
    hackathon, user = hackathon_and_user
    service = NotificationService()

    # Add second accepted registrant
    uid2 = uuid.uuid4().hex[:8]
    user2 = User(
        id=f"user-{uid2}",
        email=f"{uid2}@example.com",
        name="User Two",
        role=UserRole.participant,
    )
    db_session.add(user2)
    reg2 = Registration(
        hackathon_id=hackathon.id,
        user_id=user2.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg2)
    await db_session.commit()

    count = await service.broadcast_to_hackathon(
        db_session,
        hackathon_id=hackathon.id,
        title="Broadcast",
        message="Hello everyone",
        type=NotificationType.warning,
    )
    assert count == 2

    result = await db_session.execute(select(Notification).where(Notification.hackathon_id == hackathon.id))
    notifications = result.scalars().all()
    assert len(notifications) == 2
    user_ids = {n.user_id for n in notifications}
    assert user_ids == {user.id, user2.id}
    for n in notifications:
        assert n.title == "Broadcast"
        assert n.message == "Hello everyone"
        assert n.type == NotificationType.warning


@pytest.mark.anyio
async def test_broadcast_to_hackathon_skips_non_accepted(db_session: AsyncSession, hackathon_and_user):
    """broadcast_to_hackathon must skip registrants who are not accepted."""
    hackathon, user = hackathon_and_user
    service = NotificationService()

    # Add pending registrant
    uid2 = uuid.uuid4().hex[:8]
    user2 = User(
        id=f"user-{uid2}",
        email=f"{uid2}@example.com",
        name="User Two",
        role=UserRole.participant,
    )
    db_session.add(user2)
    reg2 = Registration(
        hackathon_id=hackathon.id,
        user_id=user2.id,
        status=RegistrationStatus.pending,
    )
    db_session.add(reg2)
    await db_session.commit()

    count = await service.broadcast_to_hackathon(
        db_session,
        hackathon_id=hackathon.id,
        title="Broadcast",
        message="Hello",
    )
    assert count == 1

    result = await db_session.execute(select(Notification).where(Notification.hackathon_id == hackathon.id))
    notifications = result.scalars().all()
    assert len(notifications) == 1
    assert notifications[0].user_id == user.id
