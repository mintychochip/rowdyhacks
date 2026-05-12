"""Tests for chat routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ChatMessage, Hackathon, Registration, RegistrationStatus, User, UserRole
from app.routes.chat import router as chat_router

app = FastAPI()
app.include_router(chat_router)


async def _override_require_clerk_user_with_db():
    fake_user = type(
        "FakeUser",
        (),
        {
            "role": UserRole.participant,
            "id": "test-user-id",
            "email": "test@example.com",
            "name": "Test User",
        },
    )()
    return {
        "user": fake_user,
        "sub": "test-user-id",
        "email": "test@example.com",
        "payload": {},
    }


async def _override_require_clerk_user_with_db_organizer():
    fake_user = type(
        "FakeUser",
        (),
        {
            "role": UserRole.organizer,
            "id": "test-organizer-id",
            "email": "organizer@test.com",
            "name": "Test Organizer",
        },
    )()
    return {
        "user": fake_user,
        "sub": "test-organizer-id",
        "email": "organizer@test.com",
        "payload": {},
    }


@pytest_asyncio.fixture
async def chat_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_clerk_user_with_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user_with_db] = _override_require_clerk_user_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def organizer_chat_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_clerk_user_with_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user_with_db] = _override_require_clerk_user_with_db_organizer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def chat_hackathon(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(ChatMessage))
    await db_session.execute(delete(Registration))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    organizer = User(
        id="test-organizer-id",
        email="organizer@test.com",
        name="Test Organizer",
        role=UserRole.organizer,
    )
    db_session.add(organizer)

    hackathon = Hackathon(
        name="Chat Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=organizer.id,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    participant = User(
        id="test-user-id",
        email="test@example.com",
        name="Test User",
        role=UserRole.participant,
    )
    db_session.add(participant)

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg)
    await db_session.commit()

    return hackathon, organizer, participant


@pytest.mark.anyio
async def test_send_chat_message(chat_client, chat_hackathon):
    hackathon, _, _ = chat_hackathon
    resp = await chat_client.post(
        f"/api/hackathons/{hackathon.id}/chat",
        json={"message": "Hello organizers!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Hello organizers!"
    assert data["sender_id"] == "test-user-id"
    assert "id" in data


@pytest.mark.anyio
async def test_send_chat_message_not_participant(chat_client, db_session: AsyncSession):
    from datetime import UTC, datetime

    from sqlalchemy import delete

    await db_session.execute(delete(ChatMessage))
    await db_session.execute(delete(Registration))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    hackathon = Hackathon(
        name="Closed Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="someone-else",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    resp = await chat_client.post(
        f"/api/hackathons/{hackathon.id}/chat",
        json={"message": "Hello!"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_get_chat_history(chat_client, chat_hackathon):
    hackathon, _, _ = chat_hackathon
    await chat_client.post(
        f"/api/hackathons/{hackathon.id}/chat",
        json={"message": "First message"},
    )
    await chat_client.post(
        f"/api/hackathons/{hackathon.id}/chat",
        json={"message": "Second message"},
    )

    resp = await chat_client.get(f"/api/hackathons/{hackathon.id}/chat")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["message"] == "Second message"
    assert data[1]["message"] == "First message"


@pytest.mark.anyio
async def test_get_organizer_chat(organizer_chat_client, chat_hackathon):
    hackathon, _, participant = chat_hackathon
    # Send a message as participant using a client override
    from app.clerk_auth import require_clerk_user_with_db

    async def participant_override():
        fake_user = type(
            "FakeUser",
            (),
            {
                "role": UserRole.participant,
                "id": participant.id,
                "email": participant.email,
                "name": participant.name,
            },
        )()
        return {
            "user": fake_user,
            "sub": participant.id,
            "email": participant.email,
            "payload": {},
        }

    app.dependency_overrides[require_clerk_user_with_db] = participant_override
    await organizer_chat_client.post(
        f"/api/hackathons/{hackathon.id}/chat",
        json={"message": "Participant msg"},
    )

    # Switch back to organizer override
    app.dependency_overrides[require_clerk_user_with_db] = _override_require_clerk_user_with_db_organizer

    resp = await organizer_chat_client.get(f"/api/hackathons/{hackathon.id}/organizer-chat")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["message"] == "Participant msg"


@pytest.mark.anyio
async def test_mark_message_read(chat_client, chat_hackathon):
    hackathon, _, _ = chat_hackathon
    create_resp = await chat_client.post(
        f"/api/hackathons/{hackathon.id}/chat",
        json={"message": "Please read me"},
    )
    msg_id = create_resp.json()["id"]

    read_resp = await chat_client.post(f"/api/chat/{msg_id}/read")
    assert read_resp.status_code == 200
    data = read_resp.json()
    assert data["read_at"] is not None


@pytest.mark.anyio
async def test_mark_message_read_not_found(chat_client):
    import uuid

    resp = await chat_client.post(f"/api/chat/{uuid.uuid4()}/read")
    assert resp.status_code == 404
