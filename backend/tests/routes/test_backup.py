"""Tests for backup and restore routes."""

import uuid

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, User, UserRole, Workshop
from app.routes.backup import router as backup_router

app = FastAPI()
app.include_router(backup_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest_asyncio.fixture
async def backup_client(engine):
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
async def hackathon_with_data(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(Workshop))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="test-user-id", email="test@example.com", name="Test User", role=UserRole.organizer)
    db_session.add(user)

    hackathon = Hackathon(
        name="Backup Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-user-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    ws = Workshop(
        hackathon_id=hackathon.id,
        title="Workshop A",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    db_session.add(ws)
    await db_session.commit()

    return hackathon


@pytest.mark.anyio
async def test_backup_hackathon(backup_client, hackathon_with_data):
    hackathon = hackathon_with_data
    resp = await backup_client.get(f"/api/backup/{hackathon.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hackathon"]["name"] == "Backup Hack"
    assert len(data["workshops"]) == 1
    assert data["workshops"][0]["title"] == "Workshop A"


@pytest.mark.anyio
async def test_backup_not_found(backup_client):
    resp = await backup_client.get(f"/api/backup/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_restore_hackathon(backup_client, hackathon_with_data):
    hackathon = hackathon_with_data
    backup_resp = await backup_client.get(f"/api/backup/{hackathon.id}")
    data = backup_resp.json()

    resp = await backup_client.post("/api/backup/restore", json={"data": data})
    assert resp.status_code == 200
    result = resp.json()
    assert result["name"] == "Backup Hack"
    assert result["restored"] is True
