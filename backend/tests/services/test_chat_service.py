"""Tests for ChatService."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, Hackathon, Registration, RegistrationStatus, User, UserRole
from app.services.chat_service import ChatService


@pytest_asyncio.fixture
async def hackathon_with_chat_users(db_session: AsyncSession):
    """Create a hackathon with an organizer and two participants for chat tests (unique per test)."""
    from datetime import UTC, datetime

    uid = uuid.uuid4().hex[:8]
    organizer = User(
        id=f"chat-org-{uid}",
        email=f"chat-org-{uid}@example.com",
        name="Chat Organizer",
        role=UserRole.organizer,
    )
    db_session.add(organizer)

    hackathon = Hackathon(
        name=f"Chat Hack {uid}",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=organizer.id,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    p1 = User(
        id=f"chat-p1-{uid}",
        email=f"chat-p1-{uid}@example.com",
        name="Participant 1",
        role=UserRole.participant,
    )
    p2 = User(
        id=f"chat-p2-{uid}",
        email=f"chat-p2-{uid}@example.com",
        name="Participant 2",
        role=UserRole.participant,
    )
    db_session.add_all([p1, p2])

    reg1 = Registration(hackathon_id=hackathon.id, user_id=p1.id, status=RegistrationStatus.accepted)
    reg2 = Registration(hackathon_id=hackathon.id, user_id=p2.id, status=RegistrationStatus.accepted)
    db_session.add_all([reg1, reg2])
    await db_session.commit()

    return hackathon, organizer, p1, p2


@pytest.mark.anyio
async def test_send_message(db_session: AsyncSession, hackathon_with_chat_users):
    """send_message must create a ChatMessage row."""
    hackathon, _, p1, _ = hackathon_with_chat_users
    service = ChatService()

    msg = await service.send_message(db_session, hackathon.id, p1.id, None, "Hello organizers!")
    assert msg.message == "Hello organizers!"
    assert msg.sender_id == p1.id
    assert msg.hackathon_id == hackathon.id
    assert msg.read_at is None

    result = await db_session.execute(select(ChatMessage))
    all_msgs = result.scalars().all()
    assert len(all_msgs) == 1


@pytest.mark.anyio
async def test_get_chat_history(db_session: AsyncSession, hackathon_with_chat_users):
    """get_chat_history must return messages where the user is sender or recipient."""
    hackathon, org, p1, p2 = hackathon_with_chat_users
    service = ChatService()

    m1 = await service.send_message(db_session, hackathon.id, p1.id, org.id, "To organizer")
    m2 = await service.send_message(db_session, hackathon.id, p2.id, org.id, "Also to organizer")
    m3 = await service.send_message(db_session, hackathon.id, org.id, p1.id, "Reply to p1")

    p1_history = await service.get_chat_history(db_session, hackathon.id, p1.id)
    assert len(p1_history) == 2
    p1_ids = {str(m.id) for m in p1_history}
    assert str(m1.id) in p1_ids
    assert str(m3.id) in p1_ids

    p2_history = await service.get_chat_history(db_session, hackathon.id, p2.id)
    assert len(p2_history) == 1
    assert p2_history[0].id == m2.id


@pytest.mark.anyio
async def test_get_organizer_chat_view(db_session: AsyncSession, hackathon_with_chat_users):
    """get_organizer_chat_view must return all hackathon messages."""
    hackathon, _, p1, p2 = hackathon_with_chat_users
    service = ChatService()

    await service.send_message(db_session, hackathon.id, p1.id, None, "Msg 1")
    await service.send_message(db_session, hackathon.id, p2.id, None, "Msg 2")

    all_msgs = await service.get_organizer_chat_view(db_session, hackathon.id)
    assert len(all_msgs) == 2


@pytest.mark.anyio
async def test_mark_as_read(db_session: AsyncSession, hackathon_with_chat_users):
    """mark_as_read must set read_at on a message."""
    hackathon, _, p1, _ = hackathon_with_chat_users
    service = ChatService()

    msg = await service.send_message(db_session, hackathon.id, p1.id, None, "Please read me")
    assert msg.read_at is None

    updated = await service.mark_as_read(db_session, msg.id, "reader-id")
    assert updated is not None
    assert updated.read_at is not None

    # Idempotent: calling again should not fail
    updated2 = await service.mark_as_read(db_session, msg.id, "reader-id")
    assert updated2.read_at is not None


@pytest.mark.anyio
async def test_mark_as_read_missing_message(db_session: AsyncSession):
    """mark_as_read must return None for a nonexistent message."""
    service = ChatService()
    result = await service.mark_as_read(db_session, uuid.uuid4(), "reader-id")
    assert result is None


@pytest.mark.anyio
async def test_is_hackathon_participant(db_session: AsyncSession, hackathon_with_chat_users):
    """is_hackathon_participant must return True for accepted/checked_in users."""
    hackathon, _, p1, _ = hackathon_with_chat_users
    service = ChatService()

    assert await service.is_hackathon_participant(db_session, hackathon.id, p1.id) is True
    assert await service.is_hackathon_participant(db_session, hackathon.id, "random-id") is False
