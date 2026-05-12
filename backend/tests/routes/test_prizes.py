import uuid

"""Tests for prize routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, Track, User, UserRole
from app.routes.hackathons import router as hackathons_router
from app.routes.prizes import router as prizes_router

app = FastAPI()
app.include_router(prizes_router)
app.include_router(hackathons_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest_asyncio.fixture
async def prize_client(engine):
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
async def hackathon_and_track(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(Track))
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

    track = Track(hackathon_id=hackathon.id, name="AI Track")
    db_session.add(track)
    await db_session.commit()
    await db_session.refresh(track)
    return hackathon, track


@pytest.mark.anyio
async def test_create_prize(prize_client, hackathon_and_track):
    hackathon, track = hackathon_and_track
    resp = await prize_client.post(
        "/api/prizes",
        json={
            "hackathon_id": str(hackathon.id),
            "name": "Best AI",
            "amount": "$1,000",
            "track_id": str(track.id),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Best AI"
    assert data["amount"] == "$1,000"
    assert data["track_id"] == str(track.id)


@pytest.mark.anyio
async def test_list_prizes(prize_client, hackathon_and_track):
    hackathon, _ = hackathon_and_track
    await prize_client.post(
        "/api/prizes",
        json={
            "hackathon_id": str(hackathon.id),
            "name": "P1",
        },
    )
    resp = await prize_client.get(f"/api/prizes?hackathon_id={hackathon.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "P1"


@pytest.mark.anyio
async def test_get_prize(prize_client, hackathon_and_track):
    hackathon, _ = hackathon_and_track
    create_resp = await prize_client.post(
        "/api/prizes",
        json={
            "hackathon_id": str(hackathon.id),
            "name": "Get Me",
        },
    )
    pid = create_resp.json()["id"]
    resp = await prize_client.get(f"/api/prizes/{pid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Get Me"


@pytest.mark.anyio
async def test_update_prize(prize_client, hackathon_and_track):
    hackathon, _ = hackathon_and_track
    create_resp = await prize_client.post(
        "/api/prizes",
        json={
            "hackathon_id": str(hackathon.id),
            "name": "Old",
        },
    )
    pid = create_resp.json()["id"]
    resp = await prize_client.put(f"/api/prizes/{pid}", json={"name": "New", "amount": "$500"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


@pytest.mark.anyio
async def test_delete_prize(prize_client, hackathon_and_track):
    hackathon, _ = hackathon_and_track
    create_resp = await prize_client.post(
        "/api/prizes",
        json={
            "hackathon_id": str(hackathon.id),
            "name": "Delete Me",
        },
    )
    pid = create_resp.json()["id"]
    resp = await prize_client.delete(f"/api/prizes/{pid}")
    assert resp.status_code == 204

    get_resp = await prize_client.get(f"/api/prizes/{pid}")
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_award_prize(prize_client, hackathon_and_track, db_session):
    from app.models import Team

    hackathon, _ = hackathon_and_track
    create_resp = await prize_client.post(
        "/api/prizes",
        json={"hackathon_id": str(hackathon.id), "name": "Award Me"},
    )
    prize_id = create_resp.json()["id"]

    team = Team(hackathon_id=hackathon.id, name="Team Alpha", join_code=uuid.uuid4().hex[:8], captain_id="test-user-id")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    resp = await prize_client.post(f"/api/prizes/{prize_id}/award/{team.id}")
    assert resp.status_code == 201
    data = resp.json()
    assert data["prize_id"] == prize_id
    assert data["team_id"] == str(team.id)


@pytest.mark.anyio
async def test_revoke_award(prize_client, hackathon_and_track, db_session):
    from app.models import Team

    hackathon, _ = hackathon_and_track
    create_resp = await prize_client.post(
        "/api/prizes",
        json={"hackathon_id": str(hackathon.id), "name": "Revoke Me"},
    )
    prize_id = create_resp.json()["id"]

    team = Team(hackathon_id=hackathon.id, name="Team Beta", join_code=uuid.uuid4().hex[:8], captain_id="test-user-id")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    await prize_client.post(f"/api/prizes/{prize_id}/award/{team.id}")

    resp = await prize_client.delete(f"/api/prizes/{prize_id}/award")
    assert resp.status_code == 204


@pytest.mark.anyio
async def test_list_awarded_prizes(prize_client, hackathon_and_track, db_session):
    from app.models import Team

    hackathon, _ = hackathon_and_track
    create_resp = await prize_client.post(
        "/api/prizes",
        json={"hackathon_id": str(hackathon.id), "name": "Listed"},
    )
    prize_id = create_resp.json()["id"]

    team = Team(hackathon_id=hackathon.id, name="Team Gamma", join_code=uuid.uuid4().hex[:8], captain_id="test-user-id")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    await prize_client.post(f"/api/prizes/{prize_id}/award/{team.id}")

    resp = await prize_client.get(f"/api/hackathons/{hackathon.id}/prizes/awarded")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["prize_id"] == prize_id
    assert data[0]["team_id"] == str(team.id)
