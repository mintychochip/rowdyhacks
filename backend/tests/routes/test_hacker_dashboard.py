"""Tests for hacker dashboard routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, Registration, RegistrationStatus, Scan, User, UserRole
from app.routes.hacker_dashboard import router as dashboard_router

app = FastAPI()
app.include_router(dashboard_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest_asyncio.fixture
async def dashboard_client(engine):
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
async def hackathon_with_reg(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(Scan))
    await db_session.execute(delete(Registration))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="test-user-id", email="test@example.com", name="Test User", role=UserRole.participant)
    db_session.add(user)

    hackathon = Hackathon(
        name="Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        description="A test hackathon",
        schedule={"events": []},
        wifi_ssid="TestWifi",
        wifi_password="secret",
        discord_invite_url="https://discord.gg/test",
        organizer_id="test-user-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=user.id,
        status=RegistrationStatus.accepted,
        qr_token="qr-123",
    )
    db_session.add(reg)
    await db_session.commit()
    await db_session.refresh(reg)

    scan = Scan(registration_id=reg.id, scan_type="checkin")
    db_session.add(scan)
    await db_session.commit()

    return hackathon, user, reg


@pytest.mark.anyio
async def test_get_hacker_dashboard(dashboard_client, hackathon_with_reg):
    hackathon, user, reg = hackathon_with_reg
    resp = await dashboard_client.get(f"/api/hackathons/{hackathon.id}/hacker-dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hackathon"]["id"] == str(hackathon.id)
    assert data["hackathon"]["name"] == "Hack"
    assert data["hackathon"]["wifi_ssid"] == "TestWifi"
    assert data["hackathon"]["wifi_password"] == "secret"
    assert data["registration"]["id"] == str(reg.id)
    assert data["registration"]["status"] == "accepted"
    assert data["registration"]["qr_token"] == "qr-123"
    assert data["registration"]["scan_count"] == 1
    assert len(data["registration"]["scans"]) == 1
    assert data["registration"]["scans"][0]["scan_type"] == "checkin"


@pytest.mark.anyio
async def test_get_hacker_dashboard_hackathon_not_found(dashboard_client):
    import uuid

    resp = await dashboard_client.get(f"/api/hackathons/{uuid.uuid4()}/hacker-dashboard")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Hackathon not found"


@pytest.mark.anyio
async def test_get_hacker_dashboard_not_registered(dashboard_client, db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(Scan))
    await db_session.execute(delete(Registration))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="test-user-id", email="test@example.com", name="Test User", role=UserRole.participant)
    db_session.add(user)

    hackathon = Hackathon(
        name="Lonely Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-user-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    resp = await dashboard_client.get(f"/api/hackathons/{hackathon.id}/hacker-dashboard")
    assert resp.status_code == 404
    assert "Registration not found" in resp.json()["detail"]
