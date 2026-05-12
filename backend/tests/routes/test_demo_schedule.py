"""Tests for demo schedule routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, User, UserRole
from app.routes.demo_schedule import router as demo_schedule_router

app = FastAPI()
app.include_router(demo_schedule_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest_asyncio.fixture
async def demo_client(engine):
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
async def test_create_demo_slot(demo_client, hackathon):
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    resp = await demo_client.post(
        f"/api/hackathons/{hackathon.id}/demo-slots",
        json={"start_time": now, "end_time": now, "room": "Room A", "judge_panel_id": "panel-1"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["room"] == "Room A"
    assert data["judge_panel_id"] == "panel-1"
    assert data["status"] == "scheduled"


@pytest.mark.anyio
async def test_list_demo_slots(demo_client, hackathon):
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    await demo_client.post(
        f"/api/hackathons/{hackathon.id}/demo-slots",
        json={"start_time": now, "end_time": now, "room": "Room A"},
    )
    resp = await demo_client.get(f"/api/hackathons/{hackathon.id}/demo-slots")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["room"] == "Room A"


@pytest.mark.anyio
async def test_auto_assign_demo_slots(demo_client, hackathon):
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    await demo_client.post(
        f"/api/hackathons/{hackathon.id}/demo-slots",
        json={"start_time": now, "end_time": now, "room": "Room A"},
    )
    resp = await demo_client.post(f"/api/hackathons/{hackathon.id}/demo-slots/assign")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_get_my_demo_slot_not_found(demo_client, hackathon):
    from uuid import uuid4

    resp = await demo_client.get(f"/api/hackathons/{hackathon.id}/my-demo-slot?team_id={uuid4()}")
    assert resp.status_code == 404
