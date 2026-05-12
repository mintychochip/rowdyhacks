"""Tests for track management routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, Track, User, UserRole
from app.routes.tracks import router as tracks_router

app = FastAPI()
app.include_router(tracks_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest_asyncio.fixture(autouse=True)
async def clear_tracks_cache():
    from app.cache import _memory_cache

    _memory_cache.clear()
    yield


@pytest_asyncio.fixture
async def tracks_client(engine):
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
async def organizer_hackathon(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(Track))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="test-user-id", email="test@example.com", name="Test User", role=UserRole.organizer)
    db_session.add(user)

    hackathon = Hackathon(
        name="Track Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-user-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)
    await db_session.refresh(user)

    return hackathon, user


@pytest_asyncio.fixture
async def sample_track(organizer_hackathon, db_session: AsyncSession):
    hackathon, _ = organizer_hackathon
    track = Track(
        hackathon_id=hackathon.id,
        name="AI Track",
        description="Build AI projects",
        challenge="Use ML to solve a problem",
        icon="🤖",
        color="#10b981",
        prize="Track Prize",
        track_type="themed",
        criteria=["Innovation", "Technical"],
        resources=[{"name": "OpenAI", "url": "https://openai.com"}],
    )
    db_session.add(track)
    await db_session.commit()
    await db_session.refresh(track)
    return track, hackathon


@pytest.mark.anyio
async def test_list_tracks(tracks_client, organizer_hackathon):
    hackathon, _ = organizer_hackathon
    resp = await tracks_client.get(f"/api/hackathons/{hackathon.id}/tracks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hackathon_id"] == str(hackathon.id)
    assert data["tracks"] == []


@pytest.mark.anyio
async def test_list_tracks_with_data(tracks_client, sample_track):
    track, hackathon = sample_track
    resp = await tracks_client.get(f"/api/hackathons/{hackathon.id}/tracks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tracks"]) == 1
    assert data["tracks"][0]["name"] == "AI Track"
    assert data["tracks"][0]["challenge"] == "Use ML to solve a problem"


@pytest.mark.anyio
async def test_create_track(tracks_client, organizer_hackathon):
    hackathon, _ = organizer_hackathon
    resp = await tracks_client.post(
        f"/api/hackathons/{hackathon.id}/tracks",
        json={
            "name": "Web3 Track",
            "description": "Blockchain projects",
            "challenge": "Build a dApp",
            "icon": "⛓",
            "color": "#3b82f6",
            "prize": "ETH",
            "track_type": "themed",
            "criteria": ["Decentralization", "Security"],
            "resources": [],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Web3 Track"
    assert data["hackathon_id"] == str(hackathon.id)
    assert data["criteria"] == ["Decentralization", "Security"]


@pytest.mark.anyio
async def test_create_track_non_organizer(tracks_client, db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(Track))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="test-user-id", email="test@example.com", name="Test User", role=UserRole.participant)
    db_session.add(user)

    hackathon = Hackathon(
        name="No Track Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-user-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    resp = await tracks_client.post(
        f"/api/hackathons/{hackathon.id}/tracks",
        json={"name": "Bad Track"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_update_track(tracks_client, sample_track):
    track, hackathon = sample_track
    resp = await tracks_client.put(
        f"/api/hackathons/{hackathon.id}/tracks/{track.id}",
        json={"name": "Updated AI Track", "description": "Updated description"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated AI Track"
    assert data["description"] == "Updated description"
    assert data["challenge"] == "Use ML to solve a problem"  # unchanged


@pytest.mark.anyio
async def test_update_track_not_found(tracks_client, organizer_hackathon):
    hackathon, _ = organizer_hackathon
    import uuid

    resp = await tracks_client.put(
        f"/api/hackathons/{hackathon.id}/tracks/{uuid.uuid4()}",
        json={"name": "Ghost"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_track(tracks_client, sample_track):
    track, hackathon = sample_track
    resp = await tracks_client.delete(f"/api/hackathons/{hackathon.id}/tracks/{track.id}")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "ok"

    get_resp = await tracks_client.get(f"/api/hackathons/{hackathon.id}/tracks")
    assert get_resp.status_code == 200
    assert get_resp.json()["tracks"] == []
