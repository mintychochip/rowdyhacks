"""Tests for help request routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, User, UserRole
from app.routes.help_requests import router as help_requests_router

app = FastAPI()
app.include_router(help_requests_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest_asyncio.fixture
async def help_client(engine):
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

    user = User(id="test-user-id", email="test@example.com", name="Test User", role=UserRole.participant)
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
async def test_create_help_request(help_client, hackathon):
    resp = await help_client.post(
        "/api/help-requests",
        json={
            "hackathon_id": str(hackathon.id),
            "title": "Need help",
            "description": "Stuck",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Need help"
    assert data["status"] == "open"
    assert data["requester_id"] == "test-user-id"


@pytest.mark.anyio
async def test_list_open_help_requests(help_client, hackathon):
    await help_client.post(
        "/api/help-requests",
        json={
            "hackathon_id": str(hackathon.id),
            "title": "R1",
        },
    )
    resp = await help_client.get(f"/api/help-requests?hackathon_id={hackathon.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "R1"


@pytest.mark.anyio
async def test_claim_help_request(help_client, hackathon):
    create_resp = await help_client.post(
        "/api/help-requests",
        json={
            "hackathon_id": str(hackathon.id),
            "title": "Claim Me",
        },
    )
    rid = create_resp.json()["id"]
    resp = await help_client.post(f"/api/help-requests/{rid}/claim")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "claimed"
    assert data["mentor_id"] == "test-user-id"


@pytest.mark.anyio
async def test_resolve_help_request(help_client, hackathon):
    create_resp = await help_client.post(
        "/api/help-requests",
        json={
            "hackathon_id": str(hackathon.id),
            "title": "Resolve Me",
        },
    )
    rid = create_resp.json()["id"]
    resp = await help_client.post(f"/api/help-requests/{rid}/resolve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


@pytest.mark.anyio
async def test_delete_help_request(help_client, hackathon):
    create_resp = await help_client.post(
        "/api/help-requests",
        json={
            "hackathon_id": str(hackathon.id),
            "title": "Delete Me",
        },
    )
    rid = create_resp.json()["id"]
    resp = await help_client.delete(f"/api/help-requests/{rid}")
    assert resp.status_code == 204

    get_resp = await help_client.get(f"/api/help-requests/{rid}")
    assert get_resp.status_code == 404
