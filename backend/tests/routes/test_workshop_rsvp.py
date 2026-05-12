"""Tests for workshop RSVP routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, User, UserRole, Workshop
from app.routes.workshops import router as workshops_router

app = FastAPI()
app.include_router(workshops_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


async def _override_require_organizer():
    return {
        "sub": "test-organizer-id",
        "email": "organizer@test.com",
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
        "payload": {},
    }


@pytest_asyncio.fixture
async def rsvp_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_clerk_user, require_organizer

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user] = _override_require_clerk_user
    app.dependency_overrides[require_organizer] = _override_require_organizer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def hackathon_with_workshop(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(Workshop))
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

    participant = User(
        id="test-user-id",
        email="test@example.com",
        name="Test User",
        role=UserRole.participant,
    )
    db_session.add(participant)

    hackathon = Hackathon(
        name="Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-organizer-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    workshop = Workshop(
        hackathon_id=hackathon.id,
        title="Intro to Python",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
        location="Room A",
        max_capacity=10,
    )
    db_session.add(workshop)
    await db_session.commit()
    await db_session.refresh(workshop)

    return hackathon, workshop


@pytest.mark.anyio
async def test_register_for_workshop(rsvp_client, hackathon_with_workshop):
    hackathon, workshop = hackathon_with_workshop
    resp = await rsvp_client.post(f"/api/workshops/{workshop.id}/rsvp?hackathon_id={hackathon.id}")
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] == "test-user-id"
    assert data["workshop_id"] == str(workshop.id)
    assert data["status"] == "registered"


@pytest.mark.anyio
async def test_register_already_registered(rsvp_client, hackathon_with_workshop):
    hackathon, workshop = hackathon_with_workshop
    first = await rsvp_client.post(f"/api/workshops/{workshop.id}/rsvp?hackathon_id={hackathon.id}")
    assert first.status_code == 201

    second = await rsvp_client.post(f"/api/workshops/{workshop.id}/rsvp?hackathon_id={hackathon.id}")
    assert second.status_code == 400
    assert "Already registered" in second.json()["detail"]


@pytest.mark.anyio
async def test_register_at_capacity(rsvp_client, hackathon_with_workshop, db_session):

    hackathon, workshop = hackathon_with_workshop
    workshop.max_capacity = 1
    await db_session.commit()

    # First user registers successfully
    first = await rsvp_client.post(f"/api/workshops/{workshop.id}/rsvp?hackathon_id={hackathon.id}")
    assert first.status_code == 201

    # Override user to a different ID to simulate another user
    async def _other_user():
        return {"sub": "other-user-id", "email": "other@example.com"}

    from app.clerk_auth import require_clerk_user

    app.dependency_overrides[require_clerk_user] = _other_user
    second = await rsvp_client.post(f"/api/workshops/{workshop.id}/rsvp?hackathon_id={hackathon.id}")
    app.dependency_overrides[require_clerk_user] = _override_require_clerk_user
    assert second.status_code == 400
    assert "at capacity" in second.json()["detail"]


@pytest.mark.anyio
async def test_cancel_rsvp(rsvp_client, hackathon_with_workshop):
    hackathon, workshop = hackathon_with_workshop
    await rsvp_client.post(f"/api/workshops/{workshop.id}/rsvp?hackathon_id={hackathon.id}")

    resp = await rsvp_client.delete(f"/api/workshops/{workshop.id}/rsvp")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"


@pytest.mark.anyio
async def test_cancel_rsvp_not_found(rsvp_client, hackathon_with_workshop):
    _, workshop = hackathon_with_workshop
    resp = await rsvp_client.delete(f"/api/workshops/{workshop.id}/rsvp")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_mark_attended(rsvp_client, hackathon_with_workshop):
    hackathon, workshop = hackathon_with_workshop
    await rsvp_client.post(f"/api/workshops/{workshop.id}/rsvp?hackathon_id={hackathon.id}")

    resp = await rsvp_client.post(f"/api/workshops/{workshop.id}/rsvp/test-user-id/attended")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "attended"
    assert data["attended_at"] is not None


@pytest.mark.anyio
async def test_mark_attended_not_found(rsvp_client, hackathon_with_workshop):
    _, workshop = hackathon_with_workshop
    resp = await rsvp_client.post(f"/api/workshops/{workshop.id}/rsvp/test-user-id/attended")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_workshop_rsvps(rsvp_client, hackathon_with_workshop):
    hackathon, workshop = hackathon_with_workshop
    await rsvp_client.post(f"/api/workshops/{workshop.id}/rsvp?hackathon_id={hackathon.id}")

    resp = await rsvp_client.get(f"/api/workshops/{workshop.id}/rsvps")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == "test-user-id"
    assert data[0]["status"] == "registered"


@pytest.mark.anyio
async def test_list_my_rsvps_for_hackathon(rsvp_client, hackathon_with_workshop):
    hackathon, workshop = hackathon_with_workshop
    await rsvp_client.post(f"/api/workshops/{workshop.id}/rsvp?hackathon_id={hackathon.id}")

    resp = await rsvp_client.get(f"/api/workshops/hackathons/{hackathon.id}/my-rsvps")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["workshop_id"] == str(workshop.id)
    assert data[0]["status"] == "registered"
