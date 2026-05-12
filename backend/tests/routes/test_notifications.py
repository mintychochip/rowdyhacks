"""Tests for notification routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, Notification, Registration, RegistrationStatus, User, UserRole
from app.routes.notifications import router as notifications_router
from app.routes.notifications import hackathon_router as hackathon_notifications_router

app = FastAPI()
app.include_router(notifications_router)
app.include_router(hackathon_notifications_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


async def _override_require_hackathon_organizer(hackathon_id=None):
    return {
        "user": type(
            "FakeUser",
            (),
            {
                "role": UserRole.organizer,
                "id": "test-organizer-id",
                "email": "organizer@test.com",
                "name": "Test Organizer",
            },
        )(),
        "sub": "test-organizer-id",
        "email": "organizer@test.com",
        "payload": {},
    }


@pytest_asyncio.fixture
async def notification_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_clerk_user, require_hackathon_organizer

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user] = _override_require_clerk_user
    app.dependency_overrides[require_hackathon_organizer] = _override_require_hackathon_organizer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def hackathon_with_reg(db_session: AsyncSession):
    from datetime import UTC, datetime
    from sqlalchemy import delete

    await db_session.execute(delete(Notification))
    await db_session.execute(delete(Registration))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(
        id="test-user-id",
        email="test@example.com",
        name="Test User",
        role=UserRole.participant,
    )
    db_session.add(user)

    hackathon = Hackathon(
        name="Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-organizer-id",
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
async def test_list_notifications(notification_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    # Create a notification via the service to avoid setup noise
    from app.services.notification_service import NotificationService

    service = NotificationService()
    from app.database import async_session

    async with async_session() as db:
        # This won't work because notification_client uses a different engine
        # Instead, use the POST broadcast endpoint and then list
        pass

    # Use broadcast to seed a notification for test-user-id
    resp = await notification_client.post(
        f"/api/hackathons/{hackathon.id}/notifications/broadcast",
        json={"title": "Broadcast", "message": "Hello"},
    )
    assert resp.status_code == 200

    resp = await notification_client.get("/api/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Broadcast"
    assert data[0]["type"] == "info"
    assert data[0]["read_at"] is None


@pytest.mark.anyio
async def test_mark_as_read(notification_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    await notification_client.post(
        f"/api/hackathons/{hackathon.id}/notifications/broadcast",
        json={"title": "T", "message": "M"},
    )

    # Get the notification ID
    list_resp = await notification_client.get("/api/notifications")
    notification_id = list_resp.json()[0]["id"]

    resp = await notification_client.post(f"/api/notifications/{notification_id}/read")
    assert resp.status_code == 200
    data = resp.json()
    assert data["read_at"] is not None


@pytest.mark.anyio
async def test_mark_all_as_read(notification_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    await notification_client.post(
        f"/api/hackathons/{hackathon.id}/notifications/broadcast",
        json={"title": "A", "message": "1"},
    )
    await notification_client.post(
        f"/api/hackathons/{hackathon.id}/notifications/broadcast",
        json={"title": "B", "message": "2"},
    )

    resp = await notification_client.post("/api/notifications/read-all")
    assert resp.status_code == 200
    assert resp.json()["marked_as_read"] == 2

    count_resp = await notification_client.get("/api/notifications/unread-count")
    assert count_resp.json()["unread_count"] == 0


@pytest.mark.anyio
async def test_unread_count(notification_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    resp = await notification_client.get("/api/notifications/unread-count")
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 0

    await notification_client.post(
        f"/api/hackathons/{hackathon.id}/notifications/broadcast",
        json={"title": "T", "message": "M"},
    )

    resp = await notification_client.get("/api/notifications/unread-count")
    assert resp.json()["unread_count"] == 1


@pytest.mark.anyio
async def test_delete_notification(notification_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    await notification_client.post(
        f"/api/hackathons/{hackathon.id}/notifications/broadcast",
        json={"title": "T", "message": "M"},
    )

    list_resp = await notification_client.get("/api/notifications")
    notification_id = list_resp.json()[0]["id"]

    resp = await notification_client.delete(f"/api/notifications/{notification_id}")
    assert resp.status_code == 204

    list_resp = await notification_client.get("/api/notifications")
    assert len(list_resp.json()) == 0


@pytest.mark.anyio
async def test_broadcast_to_hackathon(notification_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    resp = await notification_client.post(
        f"/api/hackathons/{hackathon.id}/notifications/broadcast",
        json={
            "title": "Urgent",
            "message": "Please check in",
            "type": "warning",
            "action_url": "/checkin",
            "action_text": "Check In",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["broadcast_count"] == 1

    list_resp = await notification_client.get("/api/notifications")
    notifications = list_resp.json()
    assert len(notifications) == 1
    assert notifications[0]["title"] == "Urgent"
    assert notifications[0]["type"] == "warning"
    assert notifications[0]["action_url"] == "/checkin"
    assert notifications[0]["action_text"] == "Check In"


@pytest.mark.anyio
async def test_list_notifications_filter_unread_only(notification_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    await notification_client.post(
        f"/api/hackathons/{hackathon.id}/notifications/broadcast",
        json={"title": "Unread", "message": "1"},
    )
    await notification_client.post(
        f"/api/hackathons/{hackathon.id}/notifications/broadcast",
        json={"title": "Read", "message": "2"},
    )

    # Mark the second one as read
    list_resp = await notification_client.get("/api/notifications")
    read_id = [n for n in list_resp.json() if n["title"] == "Read"][0]["id"]
    await notification_client.post(f"/api/notifications/{read_id}/read")

    resp = await notification_client.get("/api/notifications?unread_only=true")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Unread"


@pytest.mark.anyio
async def test_list_notifications_pagination(notification_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    for i in range(3):
        await notification_client.post(
            f"/api/hackathons/{hackathon.id}/notifications/broadcast",
            json={"title": f"Msg {i}", "message": str(i)},
        )

    resp = await notification_client.get("/api/notifications?limit=1&offset=0")
    assert len(resp.json()) == 1

    resp = await notification_client.get("/api/notifications?limit=1&offset=1")
    assert len(resp.json()) == 1

    resp = await notification_client.get("/api/notifications?limit=10&offset=0")
    assert len(resp.json()) == 3


@pytest.mark.anyio
async def test_mark_as_read_404(notification_client):
    import uuid as uuid_module

    fake_id = str(uuid_module.uuid4())
    resp = await notification_client.post(f"/api/notifications/{fake_id}/read")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_notification_404(notification_client):
    import uuid as uuid_module

    fake_id = str(uuid_module.uuid4())
    resp = await notification_client.delete(f"/api/notifications/{fake_id}")
    assert resp.status_code == 404
