"""Tests for volunteer management routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, User, UserRole
from app.routes.volunteers import router as volunteers_router

app = FastAPI()
app.include_router(volunteers_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest_asyncio.fixture
async def volunteer_client(engine):
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
async def hackathon_with_volunteer(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    org = User(id="test-user-id", email="test@example.com", name="Test User", role=UserRole.organizer)
    db_session.add(org)

    volunteer = User(id="vol-1", email="vol@example.com", name="Volunteer", role=UserRole.volunteer)
    db_session.add(volunteer)

    hackathon = Hackathon(
        name="Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-user-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)
    return hackathon, volunteer


@pytest.mark.anyio
async def test_add_volunteer(volunteer_client, hackathon_with_volunteer):
    hackathon, volunteer = hackathon_with_volunteer
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    resp = await volunteer_client.post(
        f"/api/hackathons/{hackathon.id}/volunteers",
        json={
            "volunteer_id": volunteer.id,
            "shift_name": "Registration Desk",
            "start_time": now,
            "end_time": now,
            "location": "Lobby",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["volunteer_id"] == volunteer.id
    assert data["shift_name"] == "Registration Desk"
    assert data["location"] == "Lobby"


@pytest.mark.anyio
async def test_list_volunteers(volunteer_client, hackathon_with_volunteer):
    hackathon, volunteer = hackathon_with_volunteer
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    await volunteer_client.post(
        f"/api/hackathons/{hackathon.id}/volunteers",
        json={
            "volunteer_id": volunteer.id,
            "shift_name": "Registration Desk",
            "start_time": now,
            "end_time": now,
        },
    )
    resp = await volunteer_client.get(f"/api/hackathons/{hackathon.id}/volunteers")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["shift_name"] == "Registration Desk"


@pytest.mark.anyio
async def test_checkin_volunteer(volunteer_client, hackathon_with_volunteer):
    hackathon, volunteer = hackathon_with_volunteer
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    create_resp = await volunteer_client.post(
        f"/api/hackathons/{hackathon.id}/volunteers",
        json={
            "volunteer_id": volunteer.id,
            "shift_name": "Registration Desk",
            "start_time": now,
            "end_time": now,
        },
    )
    shift_id = create_resp.json()["id"]

    resp = await volunteer_client.post(f"/api/hackathons/volunteers/{shift_id}/checkin")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checked_in_at"] is not None


@pytest.mark.anyio
async def test_list_my_shifts(volunteer_client, hackathon_with_volunteer):
    hackathon, volunteer = hackathon_with_volunteer
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    create_resp = await volunteer_client.post(
        f"/api/hackathons/{hackathon.id}/volunteers",
        json={
            "volunteer_id": volunteer.id,
            "shift_name": "Registration Desk",
            "start_time": now,
            "end_time": now,
        },
    )
    resp = await volunteer_client.get(f"/api/hackathons/volunteers/{volunteer.id}/shifts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    shift_ids = [s["id"] for s in data]
    assert create_resp.json()["id"] in shift_ids
