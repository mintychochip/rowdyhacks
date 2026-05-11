"""Tests for sponsor routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, User, UserRole
from app.routes.sponsors import router as sponsors_router

app = FastAPI()
app.include_router(sponsors_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest_asyncio.fixture
async def sponsor_client(engine):
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
async def test_create_sponsor(sponsor_client, hackathon):
    resp = await sponsor_client.post(
        "/api/sponsors",
        json={
            "hackathon_id": str(hackathon.id),
            "name": "Acme Corp",
            "tier": "gold",
            "website_url": "https://acme.com",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme Corp"
    assert data["tier"] == "gold"


@pytest.mark.anyio
async def test_list_sponsors(sponsor_client, hackathon):
    await sponsor_client.post(
        "/api/sponsors",
        json={
            "hackathon_id": str(hackathon.id),
            "name": "S1",
            "tier": "silver",
        },
    )
    resp = await sponsor_client.get(f"/api/sponsors?hackathon_id={hackathon.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "S1"


@pytest.mark.anyio
async def test_get_sponsor(sponsor_client, hackathon):
    create_resp = await sponsor_client.post(
        "/api/sponsors",
        json={
            "hackathon_id": str(hackathon.id),
            "name": "Get Me",
        },
    )
    sid = create_resp.json()["id"]
    resp = await sponsor_client.get(f"/api/sponsors/{sid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Get Me"


@pytest.mark.anyio
async def test_update_sponsor(sponsor_client, hackathon):
    create_resp = await sponsor_client.post(
        "/api/sponsors",
        json={
            "hackathon_id": str(hackathon.id),
            "name": "Old",
        },
    )
    sid = create_resp.json()["id"]
    resp = await sponsor_client.put(f"/api/sponsors/{sid}", json={"name": "New"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


@pytest.mark.anyio
async def test_delete_sponsor(sponsor_client, hackathon):
    create_resp = await sponsor_client.post(
        "/api/sponsors",
        json={
            "hackathon_id": str(hackathon.id),
            "name": "Delete Me",
        },
    )
    sid = create_resp.json()["id"]
    resp = await sponsor_client.delete(f"/api/sponsors/{sid}")
    assert resp.status_code == 204

    get_resp = await sponsor_client.get(f"/api/sponsors/{sid}")
    assert get_resp.status_code == 404
