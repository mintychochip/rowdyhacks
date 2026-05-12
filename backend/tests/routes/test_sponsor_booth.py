"""Tests for sponsor booth routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, Sponsor, User, UserRole
from app.routes.sponsor_booth import router as sponsor_booth_router

app = FastAPI()
app.include_router(sponsor_booth_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest_asyncio.fixture
async def booth_client(engine):
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
async def hackathon_with_sponsor(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(Sponsor))
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

    sponsor = Sponsor(hackathon_id=hackathon.id, name="SponsorCo", tier="gold")
    db_session.add(sponsor)
    await db_session.commit()
    await db_session.refresh(sponsor)
    return hackathon, sponsor


@pytest.mark.anyio
async def test_assign_booth(booth_client, hackathon_with_sponsor):
    hackathon, sponsor = hackathon_with_sponsor
    resp = await booth_client.post(
        f"/api/hackathons/{hackathon.id}/sponsor-booths",
        json={"sponsor_id": str(sponsor.id), "booth_number": "A1"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["booth_number"] == "A1"
    assert data["sponsor_id"] == str(sponsor.id)


@pytest.mark.anyio
async def test_list_booths(booth_client, hackathon_with_sponsor):
    hackathon, sponsor = hackathon_with_sponsor
    await booth_client.post(
        f"/api/hackathons/{hackathon.id}/sponsor-booths",
        json={"sponsor_id": str(sponsor.id), "booth_number": "A1"},
    )
    resp = await booth_client.get(f"/api/hackathons/{hackathon.id}/sponsor-booths")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["booth_number"] == "A1"


@pytest.mark.anyio
async def test_scan_lead(booth_client, hackathon_with_sponsor):
    hackathon, sponsor = hackathon_with_sponsor
    create_resp = await booth_client.post(
        f"/api/hackathons/{hackathon.id}/sponsor-booths",
        json={"sponsor_id": str(sponsor.id), "booth_number": "A1"},
    )
    booth_id = create_resp.json()["id"]

    resp = await booth_client.post(f"/api/hackathons/sponsor-booths/{booth_id}/scan-lead")
    assert resp.status_code == 200
    data = resp.json()
    assert data["lead_scan_count"] == 1
