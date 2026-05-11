"""Tests for workshop routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, User, UserRole
from app.routes.workshops import router as workshops_router

app = FastAPI()
app.include_router(workshops_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest_asyncio.fixture
async def workshop_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_clerk_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user] = _override_require_clerk_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def hackathon(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="test-user-id", email="test@example.com", name="Test User", role=UserRole.organizer)
    db_session.add(user)

    hackathon = Hackathon(
        name="Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-user-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)
    return hackathon


@pytest.mark.anyio
async def test_create_workshop(workshop_client, hackathon):
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    resp = await workshop_client.post(
        "/api/workshops",
        json={
            "hackathon_id": str(hackathon.id),
            "title": "Intro to Python",
            "start_time": now,
            "end_time": now,
            "location": "Room A",
            "speaker_name": "Alice",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Intro to Python"
    assert data["location"] == "Room A"


@pytest.mark.anyio
async def test_list_workshops(workshop_client, hackathon):
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    await workshop_client.post(
        "/api/workshops",
        json={
            "hackathon_id": str(hackathon.id),
            "title": "WS1",
            "start_time": now,
            "end_time": now,
        },
    )
    resp = await workshop_client.get(f"/api/workshops?hackathon_id={hackathon.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "WS1"


@pytest.mark.anyio
async def test_get_workshop(workshop_client, hackathon):
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    create_resp = await workshop_client.post(
        "/api/workshops",
        json={
            "hackathon_id": str(hackathon.id),
            "title": "Get Me",
            "start_time": now,
            "end_time": now,
        },
    )
    ws_id = create_resp.json()["id"]
    resp = await workshop_client.get(f"/api/workshops/{ws_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Get Me"


@pytest.mark.anyio
async def test_update_workshop(workshop_client, hackathon):
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    create_resp = await workshop_client.post(
        "/api/workshops",
        json={
            "hackathon_id": str(hackathon.id),
            "title": "Old",
            "start_time": now,
            "end_time": now,
        },
    )
    ws_id = create_resp.json()["id"]
    resp = await workshop_client.put(f"/api/workshops/{ws_id}", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"


@pytest.mark.anyio
async def test_delete_workshop(workshop_client, hackathon):
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    create_resp = await workshop_client.post(
        "/api/workshops",
        json={
            "hackathon_id": str(hackathon.id),
            "title": "Delete Me",
            "start_time": now,
            "end_time": now,
        },
    )
    ws_id = create_resp.json()["id"]
    resp = await workshop_client.delete(f"/api/workshops/{ws_id}")
    assert resp.status_code == 204

    get_resp = await workshop_client.get(f"/api/workshops/{ws_id}")
    assert get_resp.status_code == 404
